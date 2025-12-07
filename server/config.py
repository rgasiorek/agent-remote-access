import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration loaded from environment variables"""

    # Authentication
    AUTH_USERNAME: str = os.getenv("AUTH_USERNAME", "")
    AUTH_PASSWORD: str = os.getenv("AUTH_PASSWORD", "")

    # Claude project path
    PROJECT_PATH: str = os.getenv("CLAUDE_PROJECT_PATH", os.getcwd())

    # Session storage
    SESSION_FILE: str = os.path.join(os.getcwd(), "sessions", "sessions.json")

    # Server
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

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
