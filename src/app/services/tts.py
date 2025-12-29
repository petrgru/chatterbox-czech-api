import base64
import io
import logging
from contextlib import nullcontext
from pathlib import Path
from threading import Lock, Timer
from time import perf_counter
from typing import Optional, Tuple

import requests
import torchaudio as ta
from safetensors.torch import load_file as load_safetensors

from app.config import Settings, resolve_device

logger = logging.getLogger(__name__)


class TTSService:
    """Lazy-loading wrapper around the multilingual Chatterbox TTS model."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None
        self._device: Optional[str] = None
        self._sample_rate: Optional[int] = None
        self._lock = Lock()
        self._inference_lock = Lock()
        self._evict_timer: Optional[Timer] = None
        self._last_used: Optional[float] = None
        self._evict_after_seconds = 20

    @property
    def device(self) -> str:
        return self._device or resolve_device(self.settings.device_preference)

    @property
    def sample_rate(self) -> int:
        if self._sample_rate is None:
            return 22050  # Sensible default; overwritten after model load
        return self._sample_rate

    def _ensure_weights(self) -> Path:
        model_path = Path(self.settings.model_dir) / self.settings.model_name
        model_path.parent.mkdir(parents=True, exist_ok=True)
        if model_path.exists():
            return model_path

        logger.info("Model weights not found; downloading to %s", model_path)
        response = requests.get(self.settings.model_url, stream=True, timeout=300)
        response.raise_for_status()
        with open(model_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logger.info("Model download complete")
        return model_path

    def _load_model(self) -> None:
        # Double-checked locking to avoid duplicate loads under concurrency.
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return

            weights_path = self._ensure_weights()

            try:
                from chatterbox import mtl_tts
            except ImportError as exc:
                raise ImportError(
                    "chatterbox is not installed. Install via pip: pip install git+https://github.com/resemble-ai/chatterbox.git"
                ) from exc

            preferred_device = resolve_device(self.settings.device_preference)
            logger.info("Loading Chatterbox model on device=%s", preferred_device)

            def _init_on(device: str):
                mm = mtl_tts.ChatterboxMultilingualTTS.from_pretrained(device=device)
                state = load_safetensors(str(weights_path), device="cpu")
                mm.t3.load_state_dict(state)
                mm.t3.to(device).eval()
                return mm

            if preferred_device == "cuda":
                try:
                    import torch

                    if not torch.cuda.is_available() or torch.cuda.device_count() < 1:
                        raise RuntimeError("CUDA requested but no GPU is visible. Set DEVICE=cpu or run with --gpus all.")
                except ImportError:
                    raise RuntimeError("CUDA requested but torch is missing CUDA support. Install a CUDA-enabled torch or set DEVICE=cpu.")

            multilingual_model = _init_on(preferred_device)

            self._model = multilingual_model
            self._device = preferred_device
            self._sample_rate = multilingual_model.sr
            logger.info("Model loaded (sr=%s, device=%s)", self._sample_rate, self._device)

    def _cancel_evict_timer(self) -> None:
        if self._evict_timer is not None:
            self._evict_timer.cancel()
            self._evict_timer = None

    def _schedule_evict(self) -> None:
        self._cancel_evict_timer()
        self._evict_timer = Timer(self._evict_after_seconds, self._unload_if_idle)
        self._evict_timer.daemon = True
        self._evict_timer.start()

    def _unload_if_idle(self) -> None:
        # Avoid unloading while an inference is running.
        with self._inference_lock:
            with self._lock:
                if self._model is None:
                    return

                last_used = self._last_used or perf_counter()
                idle_for = perf_counter() - last_used
                if idle_for < self._evict_after_seconds:
                    # Reschedule if new activity happened after timer was set.
                    self._schedule_evict()
                    return

                logger.info("Unloading TTS model after %.1fs idle", idle_for)
                self._model = None
                self._device = None
                self._sample_rate = None

                try:
                    import torch

                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except ImportError:
                    pass

    def synthesize(self, text: str, language: str = "cs") -> Tuple[str, float]:
        """Generate speech audio and return (base64_wav, duration_ms)."""
        if not text.strip():
            raise ValueError("Text must not be empty")

        self._cancel_evict_timer()
        self._load_model()
        assert self._model is not None  # for type checkers

        start = perf_counter()
        autocast_ctx = nullcontext()
        try:
            import torch

            if self.device.startswith("cuda") and torch.cuda.is_available():
                autocast_ctx = torch.autocast(device_type="cuda")
            elif self.device == "mps" and hasattr(torch, "mps") and torch.backends.mps.is_available():  # type: ignore[attr-defined]
                autocast_ctx = torch.autocast(device_type="mps")
        except ImportError:
            pass

        with self._inference_lock:
            with autocast_ctx:
                # ChatterboxMultilingualTTS expects `language_id`; Czech is not in the
                # provided multilingual map, so we pass None to avoid validation errors.
                wav = self._model.generate(text, language_id=None)
        elapsed_ms = (perf_counter() - start) * 1000

        # wav is expected to be a torch Tensor shaped (channels, samples)
        samples = wav.shape[-1] if hasattr(wav, "shape") else 0
        approx_duration_ms = samples / float(self.sample_rate) * 1000 if samples else elapsed_ms

        buffer = io.BytesIO()
        ta.save(buffer, wav, self.sample_rate, format="wav")
        wav_bytes = buffer.getvalue()
        wav_b64 = base64.b64encode(wav_bytes).decode("ascii")

        self._last_used = perf_counter()
        self._schedule_evict()

        return wav_b64, approx_duration_ms
