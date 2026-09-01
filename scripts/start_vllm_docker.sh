#!/usr/bin/env bash
set -euo pipefail

if (( $# != 3 )); then
    echo "Usage: bash scripts/start_vllm_docker.sh <model_name> <cuda_devices> <port>" >&2
    exit 1
fi

model_name=${1%/}
cuda_devices=$2
port=$3

IFS=',' read -r -a gpu_ids <<< "$cuda_devices"
num_gpus=${#gpu_ids[@]}

hf_home=${HF_HOME:-$HOME/.cache/huggingface}
mkdir -p "$hf_home"

echo "Serving $model_name with vLLM"
echo "CUDA devices: $cuda_devices"
echo "Tensor parallel size: $num_gpus"

docker_args=(
    run
    -d
    --runtime nvidia
    -e "NVIDIA_VISIBLE_DEVICES=$cuda_devices"
    -v "$hf_home:/root/.cache/huggingface"
    -p "$port:$port"
    --ipc=host
)

if [[ -n ${HF_TOKEN:-} ]]; then
    docker_args+=(--env HF_TOKEN)
fi

docker_args+=(
    vllm/vllm-openai:v0.7.3
    --model "$model_name"
    --gpu-memory-utilization 0.9
    --port "$port"
    --tensor-parallel-size "$num_gpus"
    --enable-auto-tool-choice
    --tool-call-parser llama3_json
)

docker "${docker_args[@]}"
