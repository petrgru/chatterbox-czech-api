"""Integration tests for voice sample management endpoints."""
import base64
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# Create a minimal valid WAV file for testing
def create_test_wav() -> bytes:
    """Create a minimal valid WAV file."""
    # WAV header for a 1-second 22050Hz mono file
    data = b"RIFF"
    data += (36).to_bytes(4, 'little')  # file size - 8
    data += b"WAVE"
    data += b"fmt "
    data += (16).to_bytes(4, 'little')  # fmt chunk size
    data += (1).to_bytes(2, 'little')   # audio format (PCM)
    data += (1).to_bytes(2, 'little')   # num channels
    data += (22050).to_bytes(4, 'little')  # sample rate
    data += (44100).to_bytes(4, 'little')  # byte rate
    data += (2).to_bytes(2, 'little')   # block align
    data += (16).to_bytes(2, 'little')  # bits per sample
    data += b"data"
    data += (0).to_bytes(4, 'little')   # data size
    return data


@pytest.fixture
def mock_voice_sample_manager():
    """Mock the voice sample manager."""
    with patch("app.main._voice_sample_manager") as mock_manager:
        yield mock_manager


def test_upload_voice_sample(mock_voice_sample_manager):
    """Test uploading a voice sample."""
    test_wav = create_test_wav()
    test_b64 = base64.b64encode(test_wav).decode("ascii")
    
    # Configure mock
    mock_voice_sample_manager.upload_sample.return_value = "sample-123"
    mock_voice_sample_manager.list_samples.return_value = [{
        "id": "sample-123",
        "name": "Test Voice",
        "created_at": "2024-01-01T00:00:00",
        "file_size": len(test_wav)
    }]
    
    response = client.post(
        "/v1/voice-samples",
        json={"name": "Test Voice", "audio_base64": test_b64}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == "sample-123"
    assert data["name"] == "Test Voice"
    assert "created_at" in data
    assert "file_size" in data
    
    mock_voice_sample_manager.upload_sample.assert_called_once_with(
        "Test Voice", test_b64
    )


def test_upload_voice_sample_invalid_base64(mock_voice_sample_manager):
    """Test uploading with invalid base64 data."""
    mock_voice_sample_manager.upload_sample.side_effect = Exception("Invalid base64")
    
    response = client.post(
        "/v1/voice-samples",
        json={"name": "Test", "audio_base64": "not-valid-base64!!!"}
    )
    
    assert response.status_code == 500
    assert "Invalid base64" in response.json()["detail"]


def test_upload_voice_sample_empty_name(mock_voice_sample_manager):
    """Test uploading with empty name."""
    test_wav = create_test_wav()
    test_b64 = base64.b64encode(test_wav).decode("ascii")
    
    mock_voice_sample_manager.upload_sample.return_value = "sample-456"
    mock_voice_sample_manager.list_samples.return_value = [{
        "id": "sample-456",
        "name": "",
        "created_at": "2024-01-01T00:00:00",
        "file_size": len(test_wav)
    }]
    
    response = client.post(
        "/v1/voice-samples",
        json={"name": "", "audio_base64": test_b64}
    )
    
    # Empty name should be accepted (up to business logic)
    assert response.status_code == 200


def test_upload_voice_sample_missing_name():
    """Test that missing 'name' field returns validation error."""
    response = client.post(
        "/v1/voice-samples",
        json={"audio_base64": "dGVzdA=="}
    )
    
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(err["loc"] == ["body", "name"] for err in errors)


def test_upload_voice_sample_missing_audio():
    """Test that missing 'audio_base64' field returns validation error."""
    response = client.post(
        "/v1/voice-samples",
        json={"name": "Test"}
    )
    
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(err["loc"] == ["body", "audio_base64"] for err in errors)


def test_list_voice_samples_empty(mock_voice_sample_manager):
    """Test listing voice samples when none exist."""
    mock_voice_sample_manager.list_samples.return_value = []
    
    response = client.get("/v1/voice-samples")
    
    assert response.status_code == 200
    data = response.json()
    assert "samples" in data
    assert data["samples"] == []


def test_list_voice_samples_multiple(mock_voice_sample_manager):
    """Test listing multiple voice samples."""
    mock_voice_sample_manager.list_samples.return_value = [
        {
            "id": "sample-1",
            "name": "Voice 1",
            "created_at": "2024-01-01T00:00:00",
            "file_size": 1000
        },
        {
            "id": "sample-2",
            "name": "Voice 2",
            "created_at": "2024-01-02T00:00:00",
            "file_size": 2000
        },
        {
            "id": "sample-3",
            "name": "Voice 3",
            "created_at": "2024-01-03T00:00:00",
            "file_size": 3000
        }
    ]
    
    response = client.get("/v1/voice-samples")
    
    assert response.status_code == 200
    data = response.json()
    assert "samples" in data
    assert len(data["samples"]) == 3
    
    # Verify structure
    for sample in data["samples"]:
        assert "id" in sample
        assert "name" in sample
        assert "created_at" in sample
        assert "file_size" in sample


def test_list_voice_samples_error(mock_voice_sample_manager):
    """Test that errors during listing return 500."""
    mock_voice_sample_manager.list_samples.side_effect = Exception("Database error")
    
    response = client.get("/v1/voice-samples")
    
    assert response.status_code == 500
    assert "Database error" in response.json()["detail"]


def test_delete_voice_sample(mock_voice_sample_manager):
    """Test deleting a voice sample."""
    response = client.delete("/v1/voice-samples/sample-123")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deleted"
    assert data["id"] == "sample-123"
    
    mock_voice_sample_manager.delete_sample.assert_called_once_with("sample-123")


def test_delete_nonexistent_voice_sample(mock_voice_sample_manager):
    """Test deleting a non-existent voice sample."""
    mock_voice_sample_manager.delete_sample.side_effect = ValueError("Sample not-found not found")
    
    response = client.delete("/v1/voice-samples/not-found")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_delete_voice_sample_error(mock_voice_sample_manager):
    """Test that unexpected errors during deletion return 500."""
    mock_voice_sample_manager.delete_sample.side_effect = Exception("Disk error")
    
    response = client.delete("/v1/voice-samples/sample-123")
    
    assert response.status_code == 500
    assert "Disk error" in response.json()["detail"]


def test_upload_and_delete_workflow(mock_voice_sample_manager):
    """Test complete workflow: upload, list, then delete."""
    test_wav = create_test_wav()
    test_b64 = base64.b64encode(test_wav).decode("ascii")
    
    # Configure mock for upload
    mock_voice_sample_manager.upload_sample.return_value = "sample-999"
    mock_voice_sample_manager.list_samples.return_value = [{
        "id": "sample-999",
        "name": "Workflow Test",
        "created_at": "2024-01-01T00:00:00",
        "file_size": len(test_wav)
    }]
    
    # Upload
    upload_response = client.post(
        "/v1/voice-samples",
        json={"name": "Workflow Test", "audio_base64": test_b64}
    )
    assert upload_response.status_code == 200
    sample_id = upload_response.json()["id"]
    
    # List
    list_response = client.get("/v1/voice-samples")
    assert list_response.status_code == 200
    assert len(list_response.json()["samples"]) == 1
    
    # Delete
    delete_response = client.delete(f"/v1/voice-samples/{sample_id}")
    assert delete_response.status_code == 200


def test_upload_large_audio_file(mock_voice_sample_manager):
    """Test uploading a large audio file."""
    # Create a 1MB file
    large_audio = b"RIFF" + b"\x00" * (1024 * 1024)
    large_b64 = base64.b64encode(large_audio).decode("ascii")
    
    mock_voice_sample_manager.upload_sample.return_value = "sample-large"
    mock_voice_sample_manager.list_samples.return_value = [{
        "id": "sample-large",
        "name": "Large File",
        "created_at": "2024-01-01T00:00:00",
        "file_size": len(large_audio)
    }]
    
    response = client.post(
        "/v1/voice-samples",
        json={"name": "Large File", "audio_base64": large_b64}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["file_size"] == len(large_audio)


def test_upload_special_characters_in_name(mock_voice_sample_manager):
    """Test uploading with special characters in name."""
    test_wav = create_test_wav()
    test_b64 = base64.b64encode(test_wav).decode("ascii")
    special_name = "Český hlas 🎤 #1 (test)"
    
    mock_voice_sample_manager.upload_sample.return_value = "sample-special"
    mock_voice_sample_manager.list_samples.return_value = [{
        "id": "sample-special",
        "name": special_name,
        "created_at": "2024-01-01T00:00:00",
        "file_size": len(test_wav)
    }]
    
    response = client.post(
        "/v1/voice-samples",
        json={"name": special_name, "audio_base64": test_b64}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == special_name


def test_delete_with_special_characters_in_id(mock_voice_sample_manager):
    """Test deleting a sample with special characters in ID."""
    # UUIDs shouldn't have special chars, but test URL encoding handling
    sample_id = "sample-with-dash"
    
    response = client.delete(f"/v1/voice-samples/{sample_id}")
    
    assert response.status_code == 200
    mock_voice_sample_manager.delete_sample.assert_called_once_with(sample_id)


def test_get_sample_path_integration(mock_voice_sample_manager):
    """Test that get_sample_path is properly integrated with chat endpoint."""
    with patch("app.main._tts_service") as mock_tts:
        mock_tts.synthesize.return_value = (base64.b64encode(b"test").decode(), 1000)
        mock_tts.device = "cpu"
        mock_tts.sample_rate = 22050
        
        mock_voice_sample_manager.get_sample_path.return_value = "/tmp/test.wav"
        
        response = client.post(
            "/v1/chat",
            json={"text": "Test", "voice_sample_id": "sample-123"}
        )
        
        assert response.status_code == 200
        mock_voice_sample_manager.get_sample_path.assert_called_once_with("sample-123")
        mock_tts.synthesize.assert_called_once()
        call_args = mock_tts.synthesize.call_args
        assert call_args.kwargs["voice_sample_path"] == "/tmp/test.wav"


def test_upload_sample_not_found_after_upload(mock_voice_sample_manager):
    """Test edge case where sample is not found after upload."""
    test_wav = create_test_wav()
    test_b64 = base64.b64encode(test_wav).decode("ascii")
    
    # Configure mock to return a sample ID but then not find it
    mock_voice_sample_manager.upload_sample.return_value = "sample-missing"
    mock_voice_sample_manager.list_samples.return_value = []  # Sample not in list
    
    response = client.post(
        "/v1/voice-samples",
        json={"name": "Test", "audio_base64": test_b64}
    )
    
    assert response.status_code == 500
    assert "Failed to retrieve uploaded sample" in response.json()["detail"]


def test_upload_with_extremely_long_name(mock_voice_sample_manager):
    """Test uploading with an extremely long name."""
    test_wav = create_test_wav()
    test_b64 = base64.b64encode(test_wav).decode("ascii")
    long_name = "A" * 10000  # 10K character name
    
    mock_voice_sample_manager.upload_sample.return_value = "sample-long-name"
    mock_voice_sample_manager.list_samples.return_value = [{
        "id": "sample-long-name",
        "name": long_name,
        "created_at": "2024-01-01T00:00:00",
        "file_size": len(test_wav)
    }]
    
    response = client.post(
        "/v1/voice-samples",
        json={"name": long_name, "audio_base64": test_b64}
    )
    
    assert response.status_code == 200
    assert response.json()["name"] == long_name
