import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class VoiceSampleManager:
    """Manages voice samples for voice cloning."""

    def __init__(self, storage_dir: str = "/tmp/voice_samples"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.storage_dir / "metadata.json"
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    self.metadata = json.load(f)
            except Exception as e:
                logger.warning("Failed to load metadata: %s", e)
                self.metadata = {}
        else:
            self.metadata = {}

    def _save_metadata(self) -> None:
        """Save metadata to disk."""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error("Failed to save metadata: %s", e)
            raise

    def upload_sample(self, name: str, audio_base64: str) -> str:
        """
        Upload a voice sample.
        
        Args:
            name: Name/label for the sample
            audio_base64: Base64-encoded audio data
            
        Returns:
            Sample ID
        """
        sample_id = str(uuid4())
        audio_data = base64.b64decode(audio_base64)
        
        # Save audio file
        audio_path = self.storage_dir / f"{sample_id}.wav"
        with open(audio_path, "wb") as f:
            f.write(audio_data)
        
        # Save metadata
        self.metadata[sample_id] = {
            "name": name,
            "created_at": datetime.utcnow().isoformat(),
            "file_size": len(audio_data),
            "file_path": str(audio_path)
        }
        self._save_metadata()
        
        logger.info("Uploaded voice sample: %s (%s)", name, sample_id)
        return sample_id

    def list_samples(self) -> List[dict]:
        """List all available voice samples."""
        samples = []
        for sample_id, meta in self.metadata.items():
            samples.append({
                "id": sample_id,
                "name": meta["name"],
                "created_at": meta["created_at"],
                "file_size": meta["file_size"]
            })
        return samples

    def delete_sample(self, sample_id: str) -> None:
        """Delete a voice sample."""
        if sample_id not in self.metadata:
            raise ValueError(f"Sample {sample_id} not found")
        
        # Delete file
        audio_path = Path(self.metadata[sample_id]["file_path"])
        if audio_path.exists():
            audio_path.unlink()
        
        # Remove from metadata
        del self.metadata[sample_id]
        self._save_metadata()
        
        logger.info("Deleted voice sample: %s", sample_id)

    def get_sample_path(self, sample_id: str) -> Optional[str]:
        """Get the file path for a voice sample."""
        if sample_id not in self.metadata:
            return None
        return self.metadata[sample_id]["file_path"]
