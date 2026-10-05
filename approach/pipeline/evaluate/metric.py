from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path


CLI_DESCRIPTION = """
Combined evaluation module for EM, BLEU-4, ROUGE-1, ROUGE-2, and ROUGE-L metrics.
"""

# Token pattern for text metrics
TOKEN_PATTERN = r"<(?:S2SV_\w+|vul-[\w-]+|INDENT|DEDENT|unk)>|\w+|[^\w\s]"
_TOKEN_RE = re.compile(TOKEN_PATTERN)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def ngrams(tokens: list[str], n: int) -> Counter:
    return Counter(tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


def overlap_f1(matches: int, predicted: int, reference: int) -> float:
    return 2.0 * matches / (predicted + reference) if predicted and reference else 0.0


def lcs_length(a: list[str], b: list[str]) -> int:
    if len(a) < len(b):
        a, b = b, a
    masks: dict[str, int] = {}
    for i, token in enumerate(b):
        masks[token] = masks.get(token, 0) | (1 << i)
    state = 0
    for token in a:
        x = state | masks.get(token, 0)
        state = x & ~(x - ((state << 1) | 1))
    return state.bit_count()


def extract_code(text: str) -> str:
    text = str(text or "")
    think_token = "</think>"
    if think_token in text:
        text = text.split(think_token, 1)[1].strip()

    stripped = text.strip()
    pattern = r"```(?:[a-zA-Z0-9_+-]+)?\n(.*?)\n```"
    matches = re.findall(pattern, stripped, re.DOTALL)
    if matches:
        return matches[0].strip()

    if stripped.startswith("```"):
        stripped = stripped[3:]
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    stripped = stripped.strip()
    return stripped if stripped else text


def em_format(value: str) -> str:
    code = extract_code(value)
    return re.sub(r"\s+", "", code)


def compute_exact_match(pred: str, label: str) -> int:
    return 1 if em_format(pred) == em_format(label) else 0


def compute_predict_same_as_input(pred: str, model_input: str | None) -> int | None:
    if model_input is None:
        return None
    return 1 if em_format(pred) == em_format(model_input) else 0


def summarize_metric_records(records: list[dict]) -> list[dict]:
    grouped: dict[str, list] = {"ALL": list(records)}
    for r in records:
        grouped.setdefault(r.get("language", "Unknown"), []).append(r)

    rows = []
    for language, items in grouped.items():
        total = len(items)
        em_count = sum(item["exact_match"] for item in items)
        same_input_items = [i for i in items if i.get("predict_same_as_input") is not None]
        same_input_count = sum(i["predict_same_as_input"] for i in same_input_items)
        same_input_total = len(same_input_items)

        rows.append({
            "Scope": "overall" if language == "ALL" else "language",
            "Language": language,
            "Total": total,
            "Exact_Match_Count": em_count,
            "Exact_Match_Percent": 100 * em_count / total if total else 0.0,
            "Predict_Same_As_Input_Count": same_input_count,
            "Predict_Same_As_Input_Rate": same_input_count / same_input_total if same_input_total else "",
        })

    return rows


def compute_metrics(
    input_file: str | Path,
) -> dict:
    input_path = Path(input_file)

    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    # Compute EM for each record
    metric_records = []
    pairs = []
    for idx, r in enumerate(records):
        func_before = str(r.get("instruction", ""))
        func_after = str(r.get("output", ""))
        language = r.get("language", "Unknown")
        raw_predict = str(r.get("predict", ""))

        predict = extract_code(raw_predict)
        em = compute_exact_match(predict, func_after)
        same_as_input = compute_predict_same_as_input(predict, func_before)

        metric_records.append({
            "index": idx,
            "language": language,
            "exact_match": em,
            "predict_same_as_input": same_as_input,
        })

        # Prepare pairs for text metrics
        pairs.append({
            "sample_id": str(idx),
            "prediction": predict,
            "reference": func_after,
            "representation": language,
            "reported_em_correct": em == 1,
        })

    # Compute text metrics (BLEU-4, ROUGE-1, ROUGE-2, ROUGE-L)
    text_metrics = compute_text_metrics(pairs)

    summary_rows = summarize_metric_records(metric_records)
    overall = next((r for r in summary_rows if r["Scope"] == "overall"), {})

    return {
        "em_percent": overall.get("Exact_Match_Percent", 0),
        "em_count": overall.get("Exact_Match_Count", 0),
        "total": overall.get("Total", 0),
        "bleu4": text_metrics["bleu4"],
        "rouge1": text_metrics["rouge1"],
        "rouge2": text_metrics["rouge2"],
        "rougeL": text_metrics["rougeL"],
    }


def compute_text_metrics(pairs: list[dict]) -> dict:
    """Compute BLEU-4, ROUGE-1, ROUGE-2, and ROUGE-L metrics."""
    if not pairs:
        return {"bleu4": 0.0, "rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}

    bleu_total = 0.0
    rouge_totals = [0.0] * 3

    for pair in pairs:
        pred = tokenize(pair["prediction"])
        ref = tokenize(pair["reference"])

        rouge = []
        matched, precisions = [], []

        for n in range(1, 5):
            p, r = ngrams(pred, n), ngrams(ref, n)
            hits = sum((p & r).values())
            matched.append(hits)
            precisions.append((hits if hits else 0.1) / max(1, sum(p.values())))
            if n <= 2:
                rouge.append(overlap_f1(hits, sum(p.values()), sum(r.values())))

        rouge.append(overlap_f1(lcs_length(pred, ref), len(pred), len(ref)))
        bp = min(1.0, math.exp(1 - len(ref) / len(pred))) if pred else 0.0
        bleu = bp * math.exp(sum(math.log(p) for p in precisions) / 4) if matched[0] else 0.0

        bleu_total += bleu
        for i, value in enumerate(rouge):
            rouge_totals[i] += value

    return {
        "bleu4": 100 * bleu_total / len(pairs),
        "rouge1": 100 * rouge_totals[0] / len(pairs),
        "rouge2": 100 * rouge_totals[1] / len(pairs),
        "rougeL": 100 * rouge_totals[2] / len(pairs),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=CLI_DESCRIPTION)
    parser.add_argument("--input-file", type=Path, required=True)
    args = parser.parse_args()
    if not args.input_file.is_file():
        parser.error(f"Input file not found: {args.input_file}")

    stats = compute_metrics(args.input_file)

    print(f"EM:      {stats['em_count']}/{stats['total']} ({stats['em_percent']:.4f}%)")
    print(f"BLEU-4:  {stats['bleu4']:.4f}")
    print(f"ROUGE-1: {stats['rouge1']:.4f}")
    print(f"ROUGE-2: {stats['rouge2']:.4f}")
    print(f"ROUGE-L: {stats['rougeL']:.4f}")


if __name__ == "__main__":
    main()
