#!/bin/bash
MODEL_PATH=${LLAMA_MODEL_PATH:-/models/${LLAMA_MODEL:-hermes3}.gguf}

if [ ! -f "$MODEL_PATH" ]; then
    echo "ERROR: Modelo no encontrado en $MODEL_PATH"
    echo "Descarga el modelo con: curl -L {url} -o $MODEL_PATH"
    exit 1
fi

exec /usr/local/bin/llama-server \
    -m "$MODEL_PATH" \
    --host 0.0.0.0 \
    --port ${LLAMA_PORT:-8080} \
    --n-gpu-layers ${LLAMA_N_GPU_LAYERS:-35} \
    --ctx-size ${LLAMA_CTX_SIZE:-8192}
