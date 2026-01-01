"""Integration tests for the /v1/chat endpoint."""
import base64
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.fixture
def mock_tts_service():
    """Mock the TTS service to avoid heavy dependencies."""
    with patch("app.main._tts_service") as mock_service:
        # Create a mock that returns valid base64 WAV and duration
        mock_service.synthesize.return_value = (
            base64.b64encode(b"RIFF" + b"\x00" * 40).decode("ascii"),
            1234.5
        )
        mock_service.device = "cpu"
        mock_service.sample_rate = 22050
        yield mock_service


def test_chat_basic_synthesis(mock_tts_service):
    """Test basic text-to-speech synthesis."""
    response = client.post(
        "/v1/chat",
        json={"text": "Dobrý den, vítáme vás"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "reply" in data
    assert "wav_base64" in data
    assert "model" in data
    assert "device" in data
    assert "duration_ms" in data
    assert "sample_rate" in data
    assert "language" in data
    assert "speed" in data
    
    # Verify values
    assert data["reply"] == "Dobrý den, vítáme vás"
    assert data["language"] == "cs"  # default
    assert data["speed"] == 1.1  # default
    assert data["device"] == "cpu"
    assert data["sample_rate"] == 22050
    
    # Verify TTS service was called correctly
    mock_tts_service.synthesize.assert_called_once_with(
        text="Dobrý den, vítáme vás",
        language="cs",
        speed=1.1,
        voice_sample_path=None
    )


def test_chat_with_custom_speed(mock_tts_service):
    """Test synthesis with custom speed parameter."""
    response = client.post(
        "/v1/chat",
        json={"text": "Test rychlosti", "speed": 0.8}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["speed"] == 0.8
    
    mock_tts_service.synthesize.assert_called_once_with(
        text="Test rychlosti",
        language="cs",
        speed=0.8,
        voice_sample_path=None
    )


def test_chat_with_language(mock_tts_service):
    """Test synthesis with explicit language parameter."""
    response = client.post(
        "/v1/chat",
        json={"text": "Hello world", "language": "en"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "en"
    
    mock_tts_service.synthesize.assert_called_once_with(
        text="Hello world",
        language="en",
        speed=1.1,
        voice_sample_path=None
    )


def test_chat_empty_text(mock_tts_service):
    """Test that empty text returns an error."""
    mock_tts_service.synthesize.side_effect = ValueError("Text must not be empty")
    
    response = client.post(
        "/v1/chat",
        json={"text": ""}
    )
    
    assert response.status_code == 400
    assert "Text must not be empty" in response.json()["detail"]


def test_chat_whitespace_only_text(mock_tts_service):
    """Test that whitespace-only text returns an error."""
    mock_tts_service.synthesize.side_effect = ValueError("Text must not be empty")
    
    response = client.post(
        "/v1/chat",
        json={"text": "   "}
    )
    
    assert response.status_code == 400
    assert "Text must not be empty" in response.json()["detail"]


def test_chat_speed_too_low(mock_tts_service):
    """Test that speed below 0.7 is rejected by validation."""
    response = client.post(
        "/v1/chat",
        json={"text": "Test", "speed": 0.5}
    )
    
    # Pydantic validation should catch this
    assert response.status_code == 422
    assert "greater_than_equal" in response.json()["detail"][0]["type"]


def test_chat_speed_too_high(mock_tts_service):
    """Test that speed above 1.3 is rejected by validation."""
    response = client.post(
        "/v1/chat",
        json={"text": "Test", "speed": 1.5}
    )
    
    # Pydantic validation should catch this
    assert response.status_code == 422
    assert "less_than_equal" in response.json()["detail"][0]["type"]


def test_chat_speed_at_lower_bound(mock_tts_service):
    """Test that speed at 0.7 is accepted."""
    response = client.post(
        "/v1/chat",
        json={"text": "Test", "speed": 0.7}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["speed"] == 0.7


def test_chat_speed_at_upper_bound(mock_tts_service):
    """Test that speed at 1.3 is accepted."""
    response = client.post(
        "/v1/chat",
        json={"text": "Test", "speed": 1.3}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["speed"] == 1.3


def test_chat_missing_required_field():
    """Test that missing required 'text' field returns validation error."""
    response = client.post(
        "/v1/chat",
        json={"language": "cs"}
    )
    
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(err["loc"] == ["body", "text"] for err in errors)


def test_chat_with_voice_sample(mock_tts_service):
    """Test synthesis with a voice sample ID."""
    with patch("app.main._voice_sample_manager") as mock_manager:
        mock_manager.get_sample_path.return_value = "/tmp/voice_samples/test.wav"
        
        response = client.post(
            "/v1/chat",
            json={"text": "Test", "voice_sample_id": "sample-123"}
        )
        
        assert response.status_code == 200
        mock_manager.get_sample_path.assert_called_once_with("sample-123")
        mock_tts_service.synthesize.assert_called_once_with(
            text="Test",
            language="cs",
            speed=1.1,
            voice_sample_path="/tmp/voice_samples/test.wav"
        )


def test_chat_with_nonexistent_voice_sample(mock_tts_service):
    """Test that using a non-existent voice sample ID returns 404."""
    with patch("app.main._voice_sample_manager") as mock_manager:
        mock_manager.get_sample_path.return_value = None
        
        response = client.post(
            "/v1/chat",
            json={"text": "Test", "voice_sample_id": "nonexistent"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


def test_chat_synthesis_import_error(mock_tts_service):
    """Test that ImportError during synthesis returns 500."""
    mock_tts_service.synthesize.side_effect = ImportError("chatterbox not installed")
    
    response = client.post(
        "/v1/chat",
        json={"text": "Test"}
    )
    
    assert response.status_code == 500
    assert "chatterbox not installed" in response.json()["detail"]


def test_chat_synthesis_unexpected_error(mock_tts_service):
    """Test that unexpected errors during synthesis return 500."""
    mock_tts_service.synthesize.side_effect = RuntimeError("Unexpected error")
    
    response = client.post(
        "/v1/chat",
        json={"text": "Test"}
    )
    
    assert response.status_code == 500
    assert "Synthesis failed" in response.json()["detail"]


def test_chat_long_text(mock_tts_service):
    """Test synthesis with a long text."""
    long_text = "Toto je velmi dlouhý text. " * 100  # ~2800 characters
    
    response = client.post(
        "/v1/chat",
        json={"text": long_text}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == long_text


def test_chat_special_characters(mock_tts_service):
    """Test synthesis with special characters."""
    special_text = "Čeština: ěščřžýáíé! @#$% 123 []{}()"
    
    response = client.post(
        "/v1/chat",
        json={"text": special_text}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == special_text
