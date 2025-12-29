import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration sourced from env vars with sensible defaults."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = Field("Chatterbox Czech API", validation_alias="APP_NAME")
    model_name: str = Field("t3_cs.safetensors", validation_alias="MODEL_NAME")
    model_url: str = Field(
        "https://huggingface.co/Thomcles/Chatterbox-TTS-Czech/resolve/main/t3_cs.safetensors",
        validation_alias="MODEL_URL",
    )
    model_dir: str = Field("model", validation_alias="MODEL_DIR")
    device_preference: str = Field("auto", validation_alias="DEVICE")
    log_level: str = Field("info", validation_alias="LOG_LEVEL")
    port: int = Field(8000, validation_alias="PORT")


def resolve_device(device_preference: str = "auto") -> str:
    """Pick the best available device respecting a user hint."""
    device_preference = device_preference.lower()
    if device_preference != "auto":
        return device_preference

    # Lazy import torch so environments without it can still import config.
    try:
        import torch
    except ImportError:
        return "cpu"

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():  # type: ignore[attr-defined]
        return "mps"
    return "cpu"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
