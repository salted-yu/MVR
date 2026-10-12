# MVR Replication Package

## Performance Comparison

Performance comparison between the proposed framework and state-of-the-art vulnerability repair techniques. The best result in each column is shown in **bold**, and the best baseline result is <ins>underlined</ins>.

| Technique | EM (%) | BLEU-4 | ROUGE-1 | ROUGE-2 | ROUGE-L |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **_Learning-based AVR techniques_** | | | | | |
| TFix | 1.32 | 15.22 | 42.72 | 24.63 | 37.28 |
| VRepair | 0.96 | 4.42 | 25.85 | 9.93 | 22.45 |
| VulRepair | 2.05 | 15.37 | 43.01 | 24.93 | 37.45 |
| VQM | 2.05 | 17.64 | 47.07 | 27.81 | 40.76 |
| VulMaster | <ins>8.78</ins> | 39.49 | 64.30 | 50.09 | 58.45 |
| **_LLM-based AVR techniques_** | | | | | |
| APPATCH | 6.26 | 18.94 | 40.65 | 30.54 | 35.76 |
| VulKey | 6.50 | 28.51 | 55.73 | 40.20 | 51.12 |
| PaiLGen | 7.34 | 36.79 | 57.12 | 47.79 | 53.21 |
| **_Static LLMs_** | | | | | |
| Qwen2.5-Coder | 0.72 | <ins>79.68</ins> | <ins>89.08</ins> | <ins>85.99</ins> | <ins>87.38</ins> |
| Claude Sonnet 5 | 6.62 | 75.69 | 85.91 | 81.80 | 82.58 |
| GPT-5.6-Terra | 1.81 | 62.42 | 79.16 | 71.36 | 72.16 |
| **Ours** | **17.93** | **83.65** | **91.54** | **88.56** | **89.18** |
| _Gain over best baseline_ | +9.15 | +3.97 | +2.46 | +2.57 | +1.80 |

## Ablation Study

Ablation study of our framework. Subscripts denote the absolute change relative to the full framework (↓ decrease, ↑ increase). The best result in each column is shown in **bold**.

| Variant | EM (%) | BLEU-4 | ROUGE-1 | ROUGE-2 | ROUGE-L |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **Ours (full)** | **17.93** | **83.65** | **91.54** | **88.56** | **89.18** |
| _Data and training_ | | | | | |
| w/o Reference Corpus | 13.72<sub>↓4.21</sub> | 82.41<sub>↓1.24</sub> | 90.55<sub>↓0.99</sub> | 87.50<sub>↓1.06</sub> | 88.07<sub>↓1.11</sub> |
| w/o SFT | 15.64<sub>↓2.29</sub> | 81.88<sub>↓1.77</sub> | 90.41<sub>↓1.13</sub> | 87.11<sub>↓1.45</sub> | 87.88<sub>↓1.30</sub> |
| _Retrieval_ | | | | | |
| w/o Multi-Pool Retrieval | 14.68<sub>↓3.25</sub> | 82.94<sub>↓0.71</sub> | 90.99<sub>↓0.55</sub> | 88.00<sub>↓0.56</sub> | 88.66<sub>↓0.52</sub> |

## Exact Match Across the 2025 Top 25 CWEs

The Exact Match score of four approaches across the Top 25 Most Dangerous CWE-IDs in 2025.

| Rank | CWE | Ours | VulMaster | PailGen | Claude Sonnet 5 | Total |
| ---: | :--- | ---: | ---: | ---: | ---: | ---: |
| 1 | 79: Cross-site Scripting | **6 (12.24%)** | 3 (6.12%) | 3 (6.12%) | 0 (0.00%) | 49 |
| 2 | 89: SQL Injection | **3 (18.75%)** | 1 (6.25%) | 1 (6.25%) | 2 (12.50%) | 16 |
| 3 | 352: Cross-Site Request Forgery | **1 (25.00%)** | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 4 |
| 4 | 862: Missing Authorization | 0 (0.00%) | 0 (0.00%) | **1 (10.00%)** | **1 (10.00%)** | 10 |
| 5 | 787: Out-of-bounds Write | 2 (7.69%) | 1 (3.85%) | **3 (11.54%)** | **3 (11.54%)** | 26 |
| 6 | 22: Path Traversal | **4 (11.43%)** | 3 (8.57%) | 0 (0.00%) | 1 (2.86%) | 35 |
| 7 | 416: Use After Free | 3 (8.82%) | 1 (2.94%) | **4 (11.76%)** | 3 (8.82%) | 34 |
| 8 | 125: Out-of-bounds Read | **4 (9.09%)** | 1 (2.27%) | 0 (0.00%) | 3 (6.82%) | 44 |
| 9 | 78: OS Command Injection | **2 (18.18%)** | 0 (0.00%) | 0 (0.00%) | 1 (9.09%) | 11 |
| 10 | 94: Code Injection | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 10 |
| 11 | 120: Classic Buffer Overflow | **3 (30.00%)** | 1 (10.00%) | 1 (10.00%) | 0 (0.00%) | 10 |
| 12 | 434: Unrestricted Upload of File with Dangerous Type | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 2 |
| 13 | 476: NULL Pointer Dereference | **7 (25.00%)** | 2 (7.14%) | 6 (21.43%) | 6 (21.43%) | 28 |
| 14 | 121: Stack-based Buffer Overflow | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 2 |
| 15 | 502: Deserialization of Untrusted Data | 1 (9.09%) | 1 (9.09%) | **2 (18.18%)** | 1 (9.09%) | 11 |
| 16 | 122: Heap-based Buffer Overflow | **2 (50.00%)** | 1 (25.00%) | 1 (25.00%) | 0 (0.00%) | 4 |
| 17 | 863: Incorrect Authorization | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 6 |
| 18 | 20: Improper Input Validation | **9 (21.43%)** | 6 (14.29%) | 4 (9.52%) | 2 (4.76%) | 42 |
| 19 | 284: Improper Access Control | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 10 |
| 20 | 200: Exposure of Sensitive Information to an Unauthorized Actor | **8 (26.67%)** | 4 (13.33%) | 2 (6.67%) | 2 (6.67%) | 30 |
| 21 | 306: Missing Authentication for Critical Function | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 6 |
| 22 | 918: Server-Side Request Forgery | **1 (16.67%)** | **1 (16.67%)** | 0 (0.00%) | 0 (0.00%) | 6 |
| 23 | 77: Command Injection | **4 (40.00%)** | **4 (40.00%)** | 3 (30.00%) | 2 (20.00%) | 10 |
| 24 | 639: Authorization Bypass Through User-Controlled Key | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 3 |
| 25 | 770: Allocation of Resources Without Limits or Throttling | **5 (50.00%)** | 3 (30.00%) | 1 (10.00%) | 1 (10.00%) | 10 |
| | **Overall (Top 25 samples)** | **65 (15.51%)** | 33 (7.88%) | 32 (7.64%) | 28 (6.68%) | **419** |

Each method cell reports the number of exact repairs, followed by the corresponding EM rate for that CWE in parentheses. Boldface denotes the highest positive EM result in each row, including ties.

## Overview

This repository provides the prepared MVR data, LoRA fine-tuning code for the Repair Agent, and the pipeline for retrieval, Advisor comment generation, code repair, and EM evaluation.

## Directory Structure

| Directory | Contents | Documentation |
| --- | --- | --- |
| `train/` | LLaMA-Factory source code, training data, SFT/LoRA configurations, and the Bash training entry point | [Training and model serving](train/README.md) |
| `approach/` | Hybrid retrieval, calls to both agents, original prompts, and EM evaluation | [Inference and evaluation](approach/README.md) |

## Method

1. Perform SFT on `Qwen/Qwen2.5-Coder-14B-Instruct` using the mixed training corpus.
2. Apply BM25 and dense retrieval independently within the same-repository and same-language candidate pools, then fuse their rankings with RRF. Select one repository example first, then fill the remaining slot from the language pool, retaining at most two distinct examples.
3. The Advisor generates a Repair Comment using the retrieved examples, example metadata, and CWE knowledge.
4. The Repair Agent generates the repaired function using the complete vulnerable function, retrieved examples, and Repair Comment.
5. Evaluate predictions using the original EM script.

## Data

Download `data.tar.gz` from [Google Drive](https://drive.google.com/file/d/1ZdlUWsMsOFg9fCb48kMbKa47pWDcToIp/view?usp=sharing) and extract it from the repository root:

```bash
tar -xzf data.tar.gz
```

This restores the following paths directly under the repository root:

```
approach/data/          ← retrieval corpus and test samples
train/data/MVR/all_mix_train_repair.json  ← SFT training data
```

No additional moves are needed; the paths match the repository layout exactly.

## Running the Pipeline

Use separate environments for training, model serving, and `approach`. Both Python projects require Python 3.11 or later.

1. Install the local LLaMA-Factory framework as described in [train/README.md](train/README.md), review the training configuration, and run the following from the repository root:

   ```bash
   bash train/train_mix_lora.sh
   ```

2. Follow the model-serving instructions in the same document to load the base model and trained LoRA adapter with vLLM. The default Repair service address is `http://127.0.0.1:8999`, and the requested model name is `mix_lora`.

3. Install the dependencies in `approach/` and run the local validation:

   ```bash
   cd approach
   uv sync --locked
   uv run --locked python -m pipeline.method.run --dry-run
   ```

   This validates the data, configuration, and templates without loading the encoder or calling model APIs. Actual retrieval uses CUDA by default; see [approach/README.md](approach/README.md) for details.

4. Configure the services in `approach/pipeline/method/configs/llm.yaml`. The Advisor uses the official OpenAI endpoint at `https://api.openai.com/v1` with `gpt-5.4-mini` by default. Set the API key in the `OPENAI_API_KEY` environment variable, then run the following from `approach/`:

   ```bash
   uv run --locked python -m pipeline.method.run
   ```

   Each actual run creates a separate directory under `approach/runs/`, containing configuration records, contexts, prompts and responses for both agents, predictions, and EM metrics.

## Acknowledgments

We thank the developers and contributors of [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) and [vLLM](https://github.com/vllm-project/vllm) for their open-source work. This project uses LLaMA-Factory for SFT/LoRA training and vLLM for serving the Repair Agent.
