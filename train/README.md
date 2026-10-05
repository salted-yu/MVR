# MVR Repair Agent Training

This directory uses the bundled LLaMA-Factory framework to perform SFT/LoRA fine-tuning on `Qwen/Qwen2.5-Coder-14B-Instruct`. The trained adapter serves as the Repair Agent in the [MVR inference pipeline](../approach/README.md).

## Installation

Install the framework in this directory in a separate training environment. Python 3.11 or later is required. The current training configuration uses eight CUDA GPUs with BF16 support. The PyTorch CUDA build must be compatible with the host machine and support the current FSDP2 configuration.

Run the following commands from the repository root:

```bash
cd train
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Data and Training Parameters

The dataset registration in `data/dataset_info.json` maps `instruction` to the input, `output` to the target repaired function, and `system` to the system instruction.


## Training

Run the following from this directory:

```bash
bash train_mix_lora.sh
```

`CUDA_VISIBLE_DEVICES` specifies the visible GPUs and defaults to `0,1,2,3,4,5,6,7`. If you change the GPU count, also update `num_processes` in the distributed configuration.

After training, `outputs/mix_lora/` contains the LoRA adapter configuration and weights, training metrics, training state, and loss plots. Checkpoints are saved during training according to the configuration. The current setting is `overwrite_output_dir: false`; the framework handles existing output directories and checkpoint resumption. Set a new output directory for an independent training run.

## Model Serving

In a separate environment with vLLM installed, run the following from `train/`. The adapter directory must contain the configuration and weights produced by training, and the base model must match the one used for training.

```bash
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}" \
TOKENIZERS_PARALLELISM=false \
"${VLLM_BIN:-vllm}" serve "${BASE_MODEL:-Qwen/Qwen2.5-Coder-14B-Instruct}" \
  --served-model-name Qwen2.5-Coder-14B-Instruct \
  --host 0.0.0.0 \
  --port "${PORT:-8999}" \
  --max-model-len "${MAX_MODEL_LEN:-32768}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION:-0.82}" \
  --tensor-parallel-size "${TENSOR_PARALLEL_SIZE:-1}" \
  --enable-lora \
  --max-lora-rank 16 \
  --lora-modules "mix_lora=${MVR_ADAPTER_PATH:-$PWD/outputs/mix_lora}"
```

The command loads `outputs/mix_lora/` by default. Set `MVR_ADAPTER_PATH` to use a different path. The service uses one visible GPU by default; GPU memory requirements depend on the model, context length, and parallelism settings.

The [agent configuration in approach](../approach/pipeline/method/configs/llm.yaml) connects to `http://127.0.0.1:8999` and requests the adapter model `mix_lora` by default. If you change the address or port, update `repair.base_url` or set `LOCAL_VLLM_BASE_URL` accordingly.
