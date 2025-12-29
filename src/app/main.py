import logging
from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.schemas import ChatRequest, ChatResponse
from app.services.tts import TTSService

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
_tts_service = TTSService(settings=settings)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        wav_b64, duration_ms = _tts_service.synthesize(text=request.text, language=request.language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - unexpected runtime errors
        logger.exception("TTS synthesis failed")
        raise HTTPException(status_code=500, detail="Synthesis failed") from exc

    return ChatResponse(
        reply=request.text,
        wav_base64=wav_b64,
        model=settings.model_name,
        device=_tts_service.device,
        duration_ms=duration_ms,
        sample_rate=_tts_service.sample_rate,
        language=request.language,
        note="wav_base64 contains WAV bytes encoded as base64",
    )


# Entrypoint helper for `python -m app.main`
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)
