#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES-0,1,2,3,4,5,6,7}"
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1

exec "${PYTHON:-python}" -m accelerate.commands.launch \
    --config_file configs/fsdp2_8gpu.yaml \
    src/train.py configs/mix_lora.yaml
