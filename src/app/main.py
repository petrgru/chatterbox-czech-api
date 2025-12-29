import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.schemas import (
    ChatRequest, 
    ChatResponse, 
    VoiceSampleUpload, 
    VoiceSample,
    VoiceSampleListResponse
)
from app.services.tts import TTSService
from app.services.voice_samples import VoiceSampleManager

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
_tts_service = TTSService(settings=settings)
_voice_sample_manager = VoiceSampleManager()

# Allow browser clients served from other origins (e.g., Vite preview)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    # Get voice sample path if specified
    voice_sample_path = None
    if request.voice_sample_id:
        voice_sample_path = _voice_sample_manager.get_sample_path(request.voice_sample_id)
        if not voice_sample_path:
            raise HTTPException(status_code=404, detail=f"Voice sample {request.voice_sample_id} not found")
    
    try:
        wav_b64, duration_ms = _tts_service.synthesize(
            text=request.text, 
            language=request.language, 
            speed=request.speed,
            voice_sample_path=voice_sample_path
        )
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
        speed=request.speed,
        note="wav_base64 contains WAV bytes encoded as base64",
    )


@app.post("/v1/voice-samples", response_model=VoiceSample)
def upload_voice_sample(upload: VoiceSampleUpload) -> VoiceSample:
    """Upload a new voice sample for voice cloning."""
    try:
        sample_id = _voice_sample_manager.upload_sample(upload.name, upload.audio_base64)
        samples = _voice_sample_manager.list_samples()
        sample = next((s for s in samples if s["id"] == sample_id), None)
        if not sample:
            raise HTTPException(status_code=500, detail="Failed to retrieve uploaded sample")
        return VoiceSample(**sample)
    except Exception as exc:
        logger.exception("Voice sample upload failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/v1/voice-samples", response_model=VoiceSampleListResponse)
def list_voice_samples() -> VoiceSampleListResponse:
    """List all available voice samples."""
    try:
        samples = _voice_sample_manager.list_samples()
        return VoiceSampleListResponse(samples=[VoiceSample(**s) for s in samples])
    except Exception as exc:
        logger.exception("Failed to list voice samples")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/v1/voice-samples/{sample_id}")
def delete_voice_sample(sample_id: str) -> dict:
    """Delete a voice sample."""
    try:
        _voice_sample_manager.delete_sample(sample_id)
        return {"status": "deleted", "id": sample_id}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to delete voice sample")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Entrypoint helper for `python -m app.main`
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)
