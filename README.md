# MVR Replication Package

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
