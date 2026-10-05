# MVR Inference and Evaluation

This directory implements a fixed pipeline: hybrid retrieval → Advisor comment generation → repaired function generation by the Repair Agent → EM evaluation. See [train/README.md](../train/README.md) for Repair Agent training and model-serving instructions.

## Installation

Use Python 3.11 or later and an environment separate from training and vLLM. Run the following commands from the repository root:

```bash
cd approach
uv sync --locked
```

Alternatively, install the exported dependencies in an existing, activated virtual environment:

```bash
python -m pip install -r requirements.txt
```

If you use the latter option, replace `uv run --locked python` in the commands below with that environment's `python`.

## Configuration

`pipeline/method/configs/mvr.yaml` specifies the retrieval corpus, test set, CWE file, and output directory. The current encoder is `sentence-transformers/all-MiniLM-L6-v2`, with an encoding batch size of `512` and the device set to `cuda`.

`pipeline/method/configs/llm.yaml` configures two agents:

| Setting | Advisor | Repair |
| --- | --- | --- |
| `base_url` | `https://api.openai.com/v1` | `http://127.0.0.1:8999` |
| `model` | `gpt-5.4-mini` | `mix_lora` |
| Base URL override environment variable | `OPENAI_BASE_URL` | `LOCAL_VLLM_BASE_URL` |
| API key environment variable | `OPENAI_API_KEY` | Not configured by default |
| Output token limit | `max_completion_tokens: 200` | `max_tokens: 2048` |
| `temperature` | `0.0` | `0.0` |
| `max_concurrency` | `20` | `30` |
| `max_retries` | `3` | `3` |
| `timeout` (seconds) | `120` | `300` |

Set the `OPENAI_API_KEY` environment variable before running the pipeline. The default request URL is `https://api.openai.com/v1/chat/completions`; `OPENAI_BASE_URL` does not need to be set when connecting directly to the official service. API keys are read from the environment variable named by `api_key_env`, rather than stored in the YAML file.

## Running the Pipeline

Run all commands below from `approach/`. First, validate the configuration, data, and templates:

```bash
uv run --locked python -m pipeline.method.run --dry-run
```

After starting the Repair model service and configuring the Advisor credentials, run the full pipeline:

```bash
uv run --locked python -m pipeline.method.run
```

| Command-line argument | Description |
| --- | --- |
| `--config` | Method configuration file; defaults to the bundled `mvr.yaml` |
| `--llm-config` | Agent configuration file; defaults to the bundled `llm.yaml` |
| `--output-dir` | Override the parent directory for results |
| `--limit` | Process only the first N test samples |
| `--dry-run` | Validate inputs and report dataset statistics only |

Relative data paths and `output_dir` in the method YAML are resolved from `approach/`. Relative paths supplied on the command line are resolved from the current working directory. With the appropriate Python environment activated, you can also run `python approach/pipeline/method/run.py --dry-run` from the repository root.

## EM Evaluation

The main pipeline calls `compute_metrics` from `pipeline/evaluate/metric.py` directly.

To evaluate an existing run again, replace `RUN_DIR` with the actual run directory:

```bash
RUN_DIR="runs/your_run_directory"
uv run --locked python -m pipeline.evaluate.metric \
  --input-file "$RUN_DIR/results.jsonl"
```

The standalone evaluation command prints EM, BLEU-4, ROUGE-1, ROUGE-2, and ROUGE-L to the terminal.