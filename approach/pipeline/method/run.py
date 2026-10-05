from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import yaml
from tqdm import tqdm

from pipeline.evaluate.metric import compute_metrics
from pipeline.method.llm import load_llm_config, run_agent
from pipeline.method.rag import (
    PROMPT_DIR, build_context, build_cwe_lookup, build_prompt, cwe_knowledge,
    load_jsonl, query_identity, save_jsonl, validate_dataset,
)
from pipeline.method.retriever import HybridRetriever, K, RRF_CONSTANT

APPROACH_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = Path(__file__).resolve().parent / "configs"


def load_method_config(path: str | Path) -> dict:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    keys = {"train_file", "test_file", "cwe_file", "output_dir", "retrieval"}
    if not isinstance(config, dict) or set(config) != keys:
        raise ValueError(f"Method config must contain exactly {sorted(keys)}")
    for key in keys - {"retrieval"}:
        if not isinstance(config[key], str) or not config[key].strip():
            raise ValueError(f"{key} must be a nonempty path")
        config[key] = (APPROACH_DIR / config[key]).resolve()
    retrieval = config["retrieval"]
    if not isinstance(retrieval, dict) or set(retrieval) != {"embedding_model", "embedding_batch_size", "device"}:
        raise ValueError("Only embedding_model, embedding_batch_size and device are configurable for retrieval")
    for key in ("embedding_model", "device"):
        if not isinstance(retrieval[key], str) or not retrieval[key].strip():
            raise ValueError(f"retrieval.{key} must be a nonempty string")
    if type(retrieval["embedding_batch_size"]) is not int or retrieval["embedding_batch_size"] <= 0:
        raise ValueError("embedding_batch_size must be a positive integer")
    for key in ("train_file", "test_file", "cwe_file"):
        if not config[key].is_file():
            raise FileNotFoundError(config[key])
    return config


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_pipeline(config_path: Path, llm_config_path: Path, *, output_dir: Path | None = None,
                 limit: int | None = None, dry_run: bool = False) -> dict:
    if limit is not None and (type(limit) is not int or limit <= 0):
        raise ValueError("limit must be a positive integer")
    config = load_method_config(config_path)
    settings = load_llm_config(llm_config_path, require_credentials=not dry_run)
    examples = load_jsonl(config["train_file"])
    queries = load_jsonl(config["test_file"])
    validate_dataset(examples, "train")
    validate_dataset(queries, "test")
    identities = [query_identity(row)[0] for row in queries]
    if len(set(identities)) != len(identities):
        raise ValueError("Test data contains duplicate queries")
    if limit is not None:
        queries = queries[:limit]
    lookup = build_cwe_lookup(config["cwe_file"])
    preview_examples = [dict(examples[0], example_id="example-0", selection_pool="repo", rrf_score=0.0)]
    for retrieved in ([], preview_examples):
        preview = build_context(queries[0], retrieved, lookup)
        build_prompt(preview, "advisor")
        build_prompt(preview, "repair", "Dry-run template validation")
    info = {"method": "MVR", "train_examples": len(examples), "test_queries": len(queries),
            "queries_with_cwe_knowledge": sum(bool(cwe_knowledge(row, lookup)) for row in queries),
            "retrieval": {"k": K, "rrf_constant": RRF_CONSTANT,
                          "selection": "one_repository_then_unique_language", **config["retrieval"]}}
    if dry_run:
        return {"status": "dry_run", **info}
    parent = Path(output_dir).resolve() if output_dir else config["output_dir"]
    run_dir = parent / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    run_dir.mkdir(parents=True, exist_ok=False)
    source_files = sorted((APPROACH_DIR / "pipeline").rglob("*.py")) + sorted(PROMPT_DIR.glob("*.jinja"))
    save_json(run_dir / "run.json", {
        **info,
        "inputs": {key: {"path": str(config[key]), "sha256": file_hash(config[key])}
                   for key in ("train_file", "test_file", "cwe_file")},
        "agents": {role: {key: value for key, value in values.items() if key != "api_key"}
                   for role, values in settings.items()},
        "source_sha256": {str(path.relative_to(APPROACH_DIR)): file_hash(path) for path in source_files},
    })
    stage = "retrieval"
    try:
        retriever = HybridRetriever(examples, **config["retrieval"])
        contexts = [build_context(row, retriever.retrieve(row), lookup)
                    for row in tqdm(queries, desc="retrieval")]
        save_jsonl(run_dir / "contexts.jsonl", contexts)
        stage = "advisor"
        advisor_prompts = [build_prompt(context, "advisor") for context in contexts]
        save_jsonl(run_dir / "advisor_prompts.jsonl", advisor_prompts)
        comments = run_agent(advisor_prompts, settings["advisor"], run_dir / "advisor_results.jsonl")
        stage = "repair"
        repair_prompts = [build_prompt(context, "repair", comments[context["sample_id"]]) for context in contexts]
        save_jsonl(run_dir / "repair_prompts.jsonl", repair_prompts)
        predictions = run_agent(repair_prompts, settings["repair"], run_dir / "repair_results.jsonl")
        results = [{"sample_id": context["sample_id"], "query_sha256": context["query_sha256"],
                    "source_idx": context["source_idx"], "language": context["language"],
                    "status": "ok", "instruction": row["func_before"], "output": row["func_after"],
                    "predict": predictions[context["sample_id"]]}
                   for row, context in zip(queries, contexts, strict=True)]
        save_jsonl(run_dir / "results.jsonl", results)
        stage = "evaluation"
        metrics = compute_metrics(run_dir / "results.jsonl")
        save_json(run_dir / "metrics.json", metrics)
        return {"status": "complete", "output_dir": str(run_dir), **metrics}
    except Exception as error:
        save_json(run_dir / "failure.json", {"stage": stage, "error": str(error)})
        raise RuntimeError(f"{stage} failed; details saved to {run_dir}") from error


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MVR retrieval, Advisor, Repair and evaluation in sequence.")
    parser.add_argument("--config", type=Path, default=CONFIG_DIR / "mvr.yaml")
    parser.add_argument("--llm-config", type=Path, default=CONFIG_DIR / "llm.yaml")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        result = run_pipeline(args.config, args.llm_config, output_dir=args.output_dir,
                              limit=args.limit, dry_run=args.dry_run)
    except (ValueError, FileNotFoundError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
