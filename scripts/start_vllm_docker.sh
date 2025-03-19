#!/bin/bash

# Check if the first argument is provided
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Usage: bash scripts/start_vllm.sh <model_name> <cuda_devices> <port>"
    exit 1
fi

model_name=$1
model_name="${model_name%/}" # remove the trailing slash

cuda_devices=$2

port=$3

# Count the number of GPUs
comma_count=$(grep -o "," <<<"$cuda_devices" | wc -l)
num_gpu=$(($comma_count + 1))

echo "Serving $model_name with vllm"
echo "CUDA_VISIBLE_DEVICES: $cuda_devices"
echo "Number of GPUs: $num_gpu"
echo "device=$cuda_devices"

docker run -d --runtime nvidia \
    -e "NVIDIA_VISIBLE_DEVICES=$cuda_devices" \
    -v ~/vllm_cache/huggingface:/root/.cache/huggingface \
    --env "HUGGING_FACE_HUB_TOKEN=$HUGGING_FACE_HUB_TOKEN" \
    -p $port:$port \
    --ipc=host \
    vllm/vllm-openai:v0.7.3 \
    --model $model_name \
    --gpu-memory-utilization 0.9 \
    --port $port \
    --tensor-parallel-size $num_gpu \
    --enable-auto-tool-choice \
    --tool-call-parser llama3_json

# Commands
#    bash scripts/start_vllm_docker.sh meta-llama/Llama-3.1-8B-Instruct 1 11620
