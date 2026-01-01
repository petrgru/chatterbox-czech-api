"""Integration tests for CORS and other middleware."""
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_cors_headers_on_health_endpoint():
    """Test that CORS headers are present on health endpoint."""
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000"}
    )
    
    # CORS middleware should add these headers
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "*"


def test_cors_headers_on_chat_endpoint():
    """Test that CORS headers are present on chat endpoint."""
    response = client.options(
        "/v1/chat",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST"
        }
    )
    
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-methods" in response.headers


def test_cors_headers_on_voice_samples_endpoint():
    """Test that CORS headers are present on voice samples endpoint."""
    response = client.options(
        "/v1/voice-samples",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "*"


def test_cors_allows_custom_headers():
    """Test that CORS allows custom headers."""
    response = client.options(
        "/v1/chat",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Custom-Header,Content-Type"
        }
    )
    
    assert "access-control-allow-headers" in response.headers
    # The middleware allows all headers
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "x-custom-header" in allowed_headers or "*" in allowed_headers
