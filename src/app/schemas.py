from typing import Optional, List
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    text: str = Field(..., description="Czech text to synthesize into speech")
    language: str = Field("cs", description="Language code; defaults to Czech")
    speed: float = Field(1.1, ge=0.7, le=1.3, description="Speech speed multiplier (0.7-1.3, default 1.1)")
    voice_sample_id: Optional[str] = Field(None, description="ID of voice sample to use for voice cloning")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Echo of the input text or generated reply")
    wav_base64: str = Field(..., description="Base64-encoded WAV audio")
    model: str = Field(..., description="Model weights used")
    device: str = Field(..., description="Compute device (cpu/cuda/mps)")
    duration_ms: float = Field(..., description="Approximate audio duration in milliseconds")
    sample_rate: int = Field(..., description="Sample rate of the generated audio")
    language: str = Field(..., description="Language used for synthesis")
    speed: float = Field(..., description="Speech speed multiplier used")
    note: Optional[str] = Field(None, description="Extra info about fallbacks or processing")


class VoiceSampleUpload(BaseModel):
    name: str = Field(..., description="Name/label for the voice sample")
    audio_base64: str = Field(..., description="Base64-encoded audio file (WAV format)")


class VoiceSample(BaseModel):
    id: str = Field(..., description="Unique identifier for the voice sample")
    name: str = Field(..., description="Name/label for the voice sample")
    created_at: str = Field(..., description="Timestamp when the sample was created")
    file_size: int = Field(..., description="Size of the audio file in bytes")


class VoiceSampleListResponse(BaseModel):
    samples: List[VoiceSample] = Field(..., description="List of available voice samples")
