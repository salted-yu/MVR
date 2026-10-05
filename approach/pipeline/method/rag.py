from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
TEMPLATES = Environment(
    loader=FileSystemLoader(str(PROMPT_DIR)), undefined=StrictUndefined,
    autoescape=False,
)


def load_jsonl(path: str | Path) -> list[dict]:
    rows = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{path}:{line_number}: expected a JSON object")
                rows.append(row)
    if not rows:
        raise ValueError(f"Empty dataset: {path}")
    return rows


def save_jsonl(path: str | Path, rows: list[dict]) -> None:
    with Path(path).open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def validate_dataset(rows: list[dict], name: str) -> None:
    for index, row in enumerate(rows):
        for field in ("func_before", "func_after", "language"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"{name}[{index}]: missing or empty {field}")
        if row.get("repo") is not None and not isinstance(row["repo"], str):
            raise ValueError(f"{name}[{index}]: repo must be a string or null")


def query_identity(row: dict) -> tuple[str, str]:
    query_hash = hashlib.sha256(row["func_before"].encode()).hexdigest()
    identity = json.dumps([row["language"], row.get("repo"), query_hash])
    return hashlib.sha256(identity.encode()).hexdigest(), query_hash


def build_cwe_lookup(path: str | Path) -> dict[str, dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = data.get("Weaknesses")
    if not isinstance(entries, list) or not entries:
        raise ValueError("CWE knowledge base must contain a nonempty Weaknesses list")
    return {str(entry["ID"]): entry for entry in entries}


def cwe_knowledge(row: dict, lookup: dict[str, dict]) -> list[dict]:
    raw = row.get("cwe") or ""
    ids = re.findall(r"(?:CWE-)?(\d+)", str(raw), flags=re.IGNORECASE)
    return [{"id": f"CWE-{cwe_id}", "name": entry.get("Name", ""),
             "description": entry.get("Description", ""),
             "extended_description": entry.get("ExtendedDescription", "")}
            for cwe_id in dict.fromkeys(ids)
            if (entry := lookup.get(cwe_id)) is not None]


def build_context(row: dict, retrieved: list[dict], lookup: dict[str, dict]) -> dict:
    sample_id, query_hash = query_identity(row)
    examples = [{
        "example_id": ex["example_id"], "selection_pool": ex["selection_pool"],
        "rrf_score": ex["rrf_score"], "language": ex["language"],
        "repo": ex.get("repo") or "", "before": ex["func_before"],
        "after": ex["func_after"], "cve_description": ex.get("cve_description") or "",
        "commit_message": ex.get("commit_message") or "",
    } for ex in retrieved]
    return {"sample_id": sample_id, "query_sha256": query_hash,
            "source_idx": row.get("idx"), "language": row["language"],
            "repo": row.get("repo") or "", "query": row["func_before"],
            "cwe": str(row.get("cwe") or ""), "cwe_knowledge": cwe_knowledge(row, lookup),
            "examples": examples}


def build_prompt(context: dict, role: str, repair_comment: str = "") -> dict:
    if role not in {"advisor", "repair"}:
        raise ValueError(f"Unknown agent role: {role}")
    if role == "repair" and not repair_comment.strip():
        raise ValueError(f"Missing Repair Comment for {context['sample_id']}")
    examples = context["examples"]
    if role == "advisor":
        template_name = "advisor_comment.jinja"
        knowledge = "\n".join(
            entry[field] for entry in context["cwe_knowledge"]
            for field in ("id", "name", "description", "extended_description") if entry[field]
        )
    else:
        template_name = "rag.jinja"
        examples = [dict(example, cve_description="", commit_message="") for example in examples]
        knowledge = repair_comment
    system = TEMPLATES.get_template(template_name).render(
        k=len(examples), examples=examples, cwe_knowledge=knowledge,
    )
    return {"sample_id": context["sample_id"], "query_sha256": context["query_sha256"],
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": context["query"]}]}
