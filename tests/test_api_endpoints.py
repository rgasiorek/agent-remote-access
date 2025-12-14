import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path
from unittest.mock import patch, Mock

# Add agent-api to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agent-api"))

# Mock config before importing main
with patch('config.config') as mock_config:
    mock_config.AUTH_USERNAME = 'testuser'
    mock_config.AUTH_PASSWORD = 'testpass'
    mock_config.PROJECT_PATH = '/test/path'
    mock_config.AGENT_API_HOST = '127.0.0.1'
    mock_config.AGENT_API_PORT = 8001

    # Mock ClaudeWrapper initialization
    with patch('claude_wrapper.Path'):
        with patch.object(Path, 'exists', return_value=True):
            from main import app

client = TestClient(app)


class TestAPIEndpoints:
    """Test API endpoints"""

    def test_health_endpoint(self):
        """Test health check endpoint (no auth required)"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "agent-api"}

    def test_config_endpoint(self):
        """Test config endpoint (no auth required)"""
        with patch('main.config') as mock_config:
            mock_config.PROJECT_PATH = '/test/project'
            response = client.get("/api/config")
            assert response.status_code == 200
            data = response.json()
            assert "project_path" in data

    def test_chat_endpoint_no_auth(self):
        """Test chat endpoint without authentication"""
        response = client.post("/api/chat", json={"message": "test"})
        assert response.status_code == 401

    def test_chat_endpoint_invalid_auth(self):
        """Test chat endpoint with invalid credentials"""
        response = client.post(
            "/api/chat",
            json={"message": "test"},
            auth=("wrong", "credentials")
        )
        assert response.status_code == 401

    def test_chat_endpoint_success(self):
        """Test chat endpoint with valid authentication"""
        with patch('main.claude_wrapper') as mock_wrapper:
            mock_response = Mock()
            mock_response.response = "Test response"
            mock_response.session_id = "session-123"
            mock_response.cost = 0.05
            mock_response.turns = 1
            mock_response.success = True
            mock_response.error = None
            mock_wrapper.execute.return_value = mock_response

            response = client.post(
                "/api/chat",
                json={"message": "Hello"},
                auth=("testuser", "testpass")
            )

            assert response.status_code == 200
            data = response.json()
            assert data["response"] == "Test response"
            assert data["session_id"] == "session-123"
            assert data["success"] is True

    def test_chat_endpoint_with_session_id(self):
        """Test chat endpoint resuming existing session"""
        with patch('main.claude_wrapper') as mock_wrapper:
            mock_response = Mock()
            mock_response.response = "Resumed response"
            mock_response.session_id = "existing-session"
            mock_response.cost = 0.03
            mock_response.turns = 2
            mock_response.success = True
            mock_response.error = None
            mock_wrapper.execute.return_value = mock_response

            response = client.post(
                "/api/chat",
                json={"message": "Follow-up", "session_id": "existing-session"},
                auth=("testuser", "testpass")
            )

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "existing-session"
            # Verify wrapper was called with session_id
            mock_wrapper.execute.assert_called_once_with(
                message="Follow-up",
                session_id="existing-session"
            )

    def test_sessions_endpoint_no_auth(self):
        """Test sessions endpoint without authentication"""
        response = client.get("/api/sessions")
        assert response.status_code == 401

    def test_sessions_endpoint_success(self):
        """Test sessions endpoint with authentication"""
        with patch('main.claude_wrapper') as mock_wrapper:
            mock_wrapper.list_sessions.return_value = {
                'sessions': [
                    {'session_id': 'session-1', 'display': 'Test 1'}
                ]
            }

            response = client.get("/api/sessions", auth=("testuser", "testpass"))

            assert response.status_code == 200
            data = response.json()
            assert 'sessions' in data
            assert len(data['sessions']) == 1

    def test_chat_endpoint_error_handling(self):
        """Test chat endpoint handles wrapper errors"""
        with patch('main.claude_wrapper') as mock_wrapper:
            mock_response = Mock()
            mock_response.response = ""
            mock_response.session_id = ""
            mock_response.cost = 0
            mock_response.turns = 0
            mock_response.success = False
            mock_response.error = "Test error"
            mock_wrapper.execute.return_value = mock_response

            response = client.post(
                "/api/chat",
                json={"message": "Test"},
                auth=("testuser", "testpass")
            )

            assert response.status_code == 200  # Still 200, but success=False
            data = response.json()
            assert data["success"] is False
            assert data["error"] == "Test error"
