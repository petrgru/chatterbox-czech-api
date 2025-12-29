# Chatterbox Czech API

A lightweight FastAPI service that exposes Czech text-to-speech (TTS) via HTTP. It downloads and serves the Chatterbox TTS Czech model and can run on CPU, GPU (CUDA), or Apple MPS where available.

## Status
- Initial scaffold committed (FastAPI app with `/health` and `/v1/chat`).
- TTS service lazily downloads `t3_cs.safetensors` from Hugging Face on first use.

## Goals
- Provide a simple HTTP API for Czech TTS using the model stored under `model/` (downloaded from https://huggingface.co/Thomcles/Chatterbox-TTS-Czech/resolve/main/t3_cs.safetensors).
- Offer deterministic responses for scripted flows; can be extended with LLM-backed replies later.
- Be easy to deploy in containers and runnable locally for quick iteration.
- Prefer GPU (CUDA) when present; falls back to CPU.

## Suggested Architecture (adjust as needed)
- `src/` – application entrypoint, routers/handlers, business logic.
- `src/services/` – LLM client wrappers (e.g., OpenAI API), rule-based responders, prompt templates.
- `src/config.py` (or `.ts`) – configuration loading from environment.
- `tests/` – unit and integration tests; include contract tests for API routes.
- `infra/` – deployment manifests (Dockerfile, docker-compose, CI/CD pipeline files).

## Quickstart
1) Clone and enter the repo
```bash
git clone git@github.com:petrgru/chatterbox-czech-api.git
cd chatterbox-czech-api
```

2) Create a virtual environment and install deps
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

3) Configure environment (optional)
Create `.env` to override defaults:
```env
MODEL_NAME=t3_cs.safetensors
MODEL_URL=https://huggingface.co/Thomcles/Chatterbox-TTS-Czech/resolve/main/t3_cs.safetensors
MODEL_DIR=model
DEVICE=auto  # auto|cpu|cuda|mps
LOG_LEVEL=info
PORT=8000
```

CUDA check and selection:
```bash
# If you want GPU, ensure the container/host sees the card
nvidia-smi

# Run container with GPU (example):
# docker run --gpus all ...

# Force GPU or CPU via env
export DEVICE=cuda   # or DEVICE=cpu to avoid CUDA
```

4) Run the API
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The first `/v1/chat` call will download the model into `model/` if not already present.

## Model Files
- Default location: `model/` (configurable via `MODEL_DIR`).
- Expected filename: `t3_cs.safetensors` (configurable via `MODEL_NAME`).
- To pre-download manually: place the file at `${MODEL_DIR}/${MODEL_NAME}`; set `MODEL_URL` if you want the service to fetch from a different source.

## API
- `GET /health` – liveness check.
- `POST /v1/chat` – JSON body `{ "text": "Třetí přání je výkon pohřební služby", "language": "cs" }`; returns base64-encoded WAV in `wav_base64` plus metadata.

Example request:
```bash
curl -X POST http://localhost:8000/v1/chat \
	-H "Content-Type: application/json" \
	-d '{"text":"Dobrý den, vítáme vás v našem testu syntézy řeči","language":"cs"}'
```

Example response (truncated):
```json
{
	"reply": "Dobrý den, vítáme vás v našem testu syntézy řeči",
	"wav_base64": "UklGRu4...",
	"model": "t3_cs.safetensors",
	"device": "cuda",
	"duration_ms": 1234.5,
	"sample_rate": 22050,
	"language": "cs",
	"note": "wav_base64 contains WAV bytes encoded as base64"
}
```

To persist audio to disk from the response:
```bash
python - <<'PY'
import base64, json, sys
payload = json.load(sys.stdin)
audio = base64.b64decode(payload["wav_base64"])
with open("output.wav", "wb") as f:
		f.write(audio)
PY
```
## Testing
- Install dev deps (`pip install -r requirements.txt`).
- Run unit tests: `pytest`.
- The test suite includes a basic `/health` check; add integration coverage for `/v1/chat` once GPU/CPU runtime is available in CI.

## Deployment
- Container-first: add a `Dockerfile` and optionally `docker-compose.yml` (not yet included).
- Configure CI to run lint/tests and build/push images.
- For production, set worker count appropriate to hardware and keep request size limits conservative.

## Contributing
- Open an issue or draft PR outlining planned changes.
- Keep secrets out of git; rely on environment variables and secret managers.
- Add or update tests with every change.

## Next Steps
- Add automated formatting/linting (e.g., Ruff + Black) and CI workflow.
- Add Dockerfile and compose for GPU/CPU targets.
- Add `/metrics` and richer usage metadata.
