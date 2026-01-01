"""Pytest configuration and fixtures."""
import sys
from unittest.mock import MagicMock

# Mock heavy dependencies before any imports
sys.modules['torch'] = MagicMock()
sys.modules['torch.cuda'] = MagicMock()
sys.modules['torch.backends'] = MagicMock()
sys.modules['torch.backends.mps'] = MagicMock()
sys.modules['torch.autocast'] = MagicMock()
sys.modules['torchaudio'] = MagicMock()
sys.modules['torchaudio.transforms'] = MagicMock()
sys.modules['chatterbox'] = MagicMock()
sys.modules['chatterbox.mtl_tts'] = MagicMock()
sys.modules['safetensors.torch'] = MagicMock()
