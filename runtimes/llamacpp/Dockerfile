FROM nvidia/cuda:12.4-devel-ubuntu22.04

RUN apt-get update && apt-get install -y \
    build-essential cmake git curl \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/ggerganov/llama.cpp /llama.cpp
WORKDIR /llama.cpp
RUN mkdir build && cd build && \
    cmake .. -DLLAMA_CUDA=ON -DLLAMA_NATIVE=OFF && \
    make -j$(nproc)

RUN ln -s /llama.cpp/build/bin/server /usr/local/bin/llama-server

VOLUME ["/models"]
EXPOSE 8080

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
