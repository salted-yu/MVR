from __future__ import annotations

import asyncio
import json
import math
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import yaml
from tqdm import tqdm

SETTING_KEYS = {
    "base_url", "base_url_env", "model", "api_key_env", "max_tokens", "temperature",
    "max_completion_tokens", "max_concurrency", "max_retries", "timeout", "trust_env", "extra_payload",
}


def load_llm_config(path: str | Path, require_credentials: bool = True) -> dict:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) != {"advisor", "repair"}:
        raise ValueError("LLM config must contain exactly advisor and repair")
    settings = {}
    for role, raw in config.items():
        if not isinstance(raw, dict) or set(raw) - SETTING_KEYS:
            raise ValueError(f"Unsupported settings for {role}")
        values = dict(raw)
        for field in ("base_url", "model", "base_url_env", "api_key_env"):
            if field in values and not isinstance(values[field], str):
                raise ValueError(f"{role}.{field} must be a string")
        values["base_url"] = os.environ.get(values.get("base_url_env", "")) or values.get("base_url", "")
        url = urlsplit(values["base_url"])
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError(f"{role}.base_url must be an HTTP(S) URL without credentials or query parameters")
        if not values.get("model", "").strip():
            raise ValueError(f"{role}.model is required")
        token_fields = {"max_tokens", "max_completion_tokens"} & values.keys()
        if len(token_fields) != 1:
            raise ValueError(f"{role} must specify exactly one of max_tokens or max_completion_tokens")
        for field in (*token_fields, "max_concurrency", "max_retries"):
            value = values.get(field)
            minimum = 0 if field == "max_retries" else 1
            if type(value) is not int or value < minimum:
                raise ValueError(f"{role}.{field} must be an integer >= {minimum}")
        for field in ("temperature", "timeout"):
            value = values.get(field)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (field == "timeout" and value == 0):
                raise ValueError(f"Invalid {role}.{field}")
        values.setdefault("trust_env", False)
        if type(values["trust_env"]) is not bool:
            raise ValueError(f"{role}.trust_env must be a boolean")
        extra = values.setdefault("extra_payload", {})
        if not isinstance(extra, dict) or set(extra) & {
            "model", "messages", "max_tokens", "max_completion_tokens", "temperature", "stream", "n",
        }:
            raise ValueError(f"Invalid {role}.extra_payload")
        env_name = values.get("api_key_env", "")
        values["api_key"] = os.environ.get(env_name, "")
        if require_credentials and env_name and not values["api_key"]:
            raise ValueError(f"Set {env_name} for the {role} agent")
        settings[role] = values
    return settings


def validate_results(prompts: list[dict], results: list[dict]) -> dict[str, str]:
    expected = {row["sample_id"]: row["query_sha256"] for row in prompts}
    if len(expected) != len(prompts) or len(results) != len(prompts):
        raise ValueError("Agent results must match every query exactly once")
    predictions = {}
    for row in results:
        sample_id = row.get("sample_id")
        if sample_id not in expected or sample_id in predictions or row.get("query_sha256") != expected[sample_id]:
            raise ValueError("Agent result identity does not match its query")
        prediction = row.get("prediction")
        if row.get("status") != "ok" or not isinstance(prediction, str) or not prediction.strip():
            raise RuntimeError(f"Agent failed for {sample_id}: {row.get('error', 'empty output')}")
        predictions[sample_id] = prediction.strip()
    return predictions


async def request_one(client: httpx.AsyncClient, prompt: dict, settings: dict) -> dict:
    result = {"sample_id": prompt["sample_id"], "query_sha256": prompt["query_sha256"],
              "status": "error", "prediction": "", "model": settings["model"]}
    token_field = "max_completion_tokens" if "max_completion_tokens" in settings else "max_tokens"
    payload = {"model": settings["model"], "messages": prompt["messages"],
               token_field: settings[token_field], "temperature": settings["temperature"],
               "stream": False, **settings["extra_payload"]}
    base_url = settings["base_url"].rstrip("/")
    url = base_url + ("/chat/completions" if base_url.endswith("/v1") else "/v1/chat/completions")
    headers = {"Authorization": f"Bearer {settings['api_key']}"} if settings["api_key"] else {}
    for attempt in range(settings["max_retries"] + 1):
        retryable = False
        try:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                result["error"] = f"HTTP {response.status_code}"
                retryable = response.status_code in {408, 429} or response.status_code >= 500
            else:
                body = response.json()
                choice = body["choices"][0]
                message = choice["message"]
                content = message.get("content")
                result["finish_reason"] = choice.get("finish_reason")
                if message.get("refusal") or choice.get("finish_reason") != "stop":
                    result["error"] = "Refused, incomplete, or non-text completion"
                elif not isinstance(content, str) or not content.strip():
                    result["error"] = "Empty completion"
                else:
                    result.update(status="ok", prediction=content.strip())
                    result.pop("error", None)
                    return result
        except httpx.RequestError as error:
            result["error"] = type(error).__name__
            retryable = True
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            result["error"] = "Malformed completion response"
        if not retryable or attempt == settings["max_retries"]:
            break
        await asyncio.sleep(min(2 ** attempt, 30))
    return result


async def request_batch(prompts: list[dict], settings: dict, output_path: Path) -> list[dict]:
    semaphore = asyncio.Semaphore(settings["max_concurrency"])
    async with httpx.AsyncClient(timeout=settings["timeout"], trust_env=settings["trust_env"]) as client:
        async def run_one(prompt):
            async with semaphore:
                return await request_one(client, prompt, settings)

        tasks = [asyncio.create_task(run_one(prompt)) for prompt in prompts]
        results = []
        with output_path.open("w", encoding="utf-8") as stream:
            for task in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc=output_path.stem):
                result = await task
                results.append(result)
                stream.write(json.dumps(result, ensure_ascii=False) + "\n")
                stream.flush()
        return results


def run_agent(prompts: list[dict], settings: dict, output_path: Path) -> dict[str, str]:
    if not prompts:
        raise ValueError("Cannot run an agent without queries")
    results = asyncio.run(request_batch(prompts, settings, output_path))
    return validate_results(prompts, results)
