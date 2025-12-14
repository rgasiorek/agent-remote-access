import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
import sys
from pathlib import Path

# Add agent-api to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agent-api"))

from auth import verify_auth
from config import config


class TestAuth:
    """Test authentication functionality"""

    def test_verify_auth_success(self, monkeypatch):
        """Test successful authentication with correct credentials"""
        # Set test credentials
        monkeypatch.setattr(config, 'AUTH_USERNAME', 'testuser')
        monkeypatch.setattr(config, 'AUTH_PASSWORD', 'testpass')

        credentials = HTTPBasicCredentials(username='testuser', password='testpass')
        result = verify_auth(credentials)

        assert result == 'testuser'

    def test_verify_auth_invalid_username(self, monkeypatch):
        """Test authentication failure with invalid username"""
        monkeypatch.setattr(config, 'AUTH_USERNAME', 'testuser')
        monkeypatch.setattr(config, 'AUTH_PASSWORD', 'testpass')

        credentials = HTTPBasicCredentials(username='wronguser', password='testpass')

        with pytest.raises(HTTPException) as exc_info:
            verify_auth(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid credentials"
        assert exc_info.value.headers == {"WWW-Authenticate": "Basic"}

    def test_verify_auth_invalid_password(self, monkeypatch):
        """Test authentication failure with invalid password"""
        monkeypatch.setattr(config, 'AUTH_USERNAME', 'testuser')
        monkeypatch.setattr(config, 'AUTH_PASSWORD', 'testpass')

        credentials = HTTPBasicCredentials(username='testuser', password='wrongpass')

        with pytest.raises(HTTPException) as exc_info:
            verify_auth(credentials)

        assert exc_info.value.status_code == 401

    def test_verify_auth_empty_credentials(self, monkeypatch):
        """Test authentication failure with empty credentials"""
        monkeypatch.setattr(config, 'AUTH_USERNAME', 'testuser')
        monkeypatch.setattr(config, 'AUTH_PASSWORD', 'testpass')

        credentials = HTTPBasicCredentials(username='', password='')

        with pytest.raises(HTTPException) as exc_info:
            verify_auth(credentials)

        assert exc_info.value.status_code == 401
