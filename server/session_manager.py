import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from server.config import config

class SessionManager:
    """
    Manages Claude Code session IDs for conversation persistence
    Thread-safe file-based storage
    """

    def __init__(self, session_file: str = None):
        self.session_file = session_file or config.SESSION_FILE
        self.lock = threading.Lock()
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create session file if it doesn't exist"""
        path = Path(self.session_file)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.session_file, 'w') as f:
                json.dump({"conversations": {}}, f, indent=2)

    def _read_sessions(self) -> Dict:
        """Read sessions from file (thread-safe)"""
        with self.lock:
            with open(self.session_file, 'r') as f:
                return json.load(f)

    def _write_sessions(self, data: Dict):
        """Write sessions to file (thread-safe)"""
        with self.lock:
            with open(self.session_file, 'w') as f:
                json.dump(data, f, indent=2)

    def get_session(self, conv_id: str = "default") -> Optional[str]:
        """
        Retrieve session ID for a conversation

        Args:
            conv_id: Conversation identifier (default: "default")

        Returns:
            Session UUID or None if no session exists
        """
        data = self._read_sessions()
        conv = data.get("conversations", {}).get(conv_id)
        return conv.get("session_id") if conv else None

    def update_session(self, conv_id: str = "default", session_id: str = None, turn_count: int = 0):
        """
        Update or create session information

        Args:
            conv_id: Conversation identifier
            session_id: Claude session UUID
            turn_count: Number of turns in conversation
        """
        data = self._read_sessions()

        if conv_id not in data["conversations"]:
            data["conversations"][conv_id] = {
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "last_message_at": datetime.utcnow().isoformat() + "Z",
                "turn_count": turn_count
            }
        else:
            data["conversations"][conv_id]["session_id"] = session_id
            data["conversations"][conv_id]["last_message_at"] = datetime.utcnow().isoformat() + "Z"
            data["conversations"][conv_id]["turn_count"] = turn_count

        self._write_sessions(data)

    def reset_session(self, conv_id: str = "default"):
        """
        Reset/delete a conversation session

        Args:
            conv_id: Conversation identifier to reset
        """
        data = self._read_sessions()

        if conv_id in data["conversations"]:
            del data["conversations"][conv_id]
            self._write_sessions(data)

    def get_all_sessions(self) -> Dict:
        """Get all conversation sessions"""
        data = self._read_sessions()
        return data.get("conversations", {})

# Global session manager instance
session_manager = SessionManager()
