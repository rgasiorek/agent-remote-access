import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration loaded from environment variables"""

    # Authentication
    AUTH_USERNAME: str = os.getenv("AUTH_USERNAME", "")
    AUTH_PASSWORD: str = os.getenv("AUTH_PASSWORD", "")

    # Agent project path (expand to absolute path)
    PROJECT_PATH: str = os.path.abspath(os.path.expanduser(os.getenv("CLAUDE_PROJECT_PATH", os.getcwd())))

    # Agent CLI command (defaults to 'claude' for Claude Code)
    AGENT_CLI_COMMAND: str = os.getenv("AGENT_CLI_COMMAND", "claude")

    # Session storage
    SESSION_FILE: str = os.path.join(os.getcwd(), "sessions", "sessions.json")

    # Agent API Server
    AGENT_API_HOST: str = os.getenv("AGENT_API_HOST", "127.0.0.1")
    AGENT_API_PORT: int = int(os.getenv("AGENT_API_PORT", "8001"))

    # UI Server
    UI_SERVER_HOST: str = os.getenv("UI_SERVER_HOST", "127.0.0.1")
    UI_SERVER_PORT: int = int(os.getenv("UI_SERVER_PORT", "8000"))

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.AUTH_USERNAME or not cls.AUTH_PASSWORD:
            raise ValueError(
                "AUTH_USERNAME and AUTH_PASSWORD must be set in .env file. "
                "Copy .env.example to .env and configure credentials."
            )

        # Ensure sessions directory exists
        sessions_dir = Path(cls.SESSION_FILE).parent
        sessions_dir.mkdir(parents=True, exist_ok=True)

        return True

config = Config()
