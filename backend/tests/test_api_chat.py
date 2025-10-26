"""Tests for chat API endpoints."""
import pytest
from fastapi.testclient import TestClient


# Note: These tests require mocking the external API calls
# This is a template for future test implementation

@pytest.mark.skip("Requires API mocking")
def test_chat_intake_endpoint():
    """Test chat intake endpoint with valid request."""
    # from app.main import app
    # client = TestClient(app)
    # 
    # response = client.post(
    #     "/api/chat/intake",
    #     json={"message": "black accent chair"}
    # )
    # 
    # assert response.status_code == 200
    # data = response.json()
    # assert "intent" in data
    # assert data["intent"]["query_text"] is not None
    pass


@pytest.mark.skip("Requires API mocking")
def test_chat_intake_empty_message():
    """Test chat intake with empty message."""
    # from app.main import app
    # client = TestClient(app)
    # 
    # response = client.post(
    #     "/api/chat/intake",
    #     json={"message": ""}
    # )
    # 
    # Should handle gracefully
    pass



