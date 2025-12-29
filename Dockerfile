# CUDA-enabled PyTorch runtime (already includes torch/torchaudio deps)
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

ARG MODEL_DIR=/model

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src \
    DEVICE=auto \
    MODEL_DIR=${MODEL_DIR}

WORKDIR /app

# Minimal system deps (libsndfile for torchaudio wav IO; git for chatterbox install)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libsndfile1 \
       git \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source and tests
COPY src ./src
COPY tests ./tests
COPY README.md ./

# Symlink to externally mounted model directory (bind mount at runtime)
RUN ln -s ${MODEL_DIR} /app/model

EXPOSE 8000

# Default start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
