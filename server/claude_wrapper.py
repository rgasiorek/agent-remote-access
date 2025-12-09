import json
import subprocess
import requests
from typing import Optional
from pydantic import BaseModel
from server.config import config

class ClaudeResponse(BaseModel):
    """Response from Claude Code CLI"""
    response: str
    session_id: str
    cost: float
    turns: int
    success: bool = True
    error: Optional[str] = None

class ClaudeWrapper:
    """
    Wrapper for executing Claude Code CLI commands
    Uses headless mode (claude -p) with JSON output
    """

    def __init__(self, project_path: str = None, timeout: int = 300):
        """
        Initialize Claude wrapper

        Args:
            project_path: Working directory for Claude context (default: from config)
            timeout: Maximum execution time in seconds (default: 5 minutes)
        """
        self.project_path = project_path or config.PROJECT_PATH
        self.timeout = timeout

    def execute(self, message: str, session_id: Optional[str] = None) -> ClaudeResponse:
        """
        Execute Claude Code command via host bridge

        Args:
            message: User's message/prompt
            session_id: Existing session UUID (None for new session)

        Returns:
            ClaudeResponse with parsed output
        """
        # Build command arguments
        args = ["-p", message, "--output-format", "json"]

        if session_id:
            args.extend(["--resume", session_id])

        try:
            # Call host bridge service
            response = requests.post(
                'http://host.docker.internal:8001/execute',
                json={
                    'args': args,
                    'cwd': self.project_path,
                    'timeout': self.timeout
                },
                timeout=self.timeout + 5  # Add buffer to HTTP timeout
            )

            if response.status_code != 200:
                return ClaudeResponse(
                    response="",
                    session_id=session_id or "",
                    cost=0.0,
                    turns=0,
                    success=False,
                    error=f"Host bridge error: {response.text}"
                )

            result = response.json()

            # Parse JSON output
            if result['returncode'] == 0:
                output = json.loads(result['stdout'])

                # Extract fields from Claude's JSON response
                return ClaudeResponse(
                    response=output.get("result", ""),
                    session_id=output.get("session_id", ""),
                    cost=output.get("total_cost_usd", 0.0),
                    turns=output.get("num_turns", 0),
                    success=True
                )
            else:
                # Command failed
                return ClaudeResponse(
                    response="",
                    session_id=session_id or "",
                    cost=0.0,
                    turns=0,
                    success=False,
                    error=f"Claude CLI error: {result['stderr']}"
                )

        except requests.Timeout:
            return ClaudeResponse(
                response="",
                session_id=session_id or "",
                cost=0.0,
                turns=0,
                success=False,
                error=f"Request timed out after {self.timeout} seconds"
            )

        except requests.RequestException as e:
            return ClaudeResponse(
                response="",
                session_id=session_id or "",
                cost=0.0,
                turns=0,
                success=False,
                error=f"Failed to connect to host bridge: {str(e)}"
            )

        except json.JSONDecodeError as e:
            return ClaudeResponse(
                response="",
                session_id=session_id or "",
                cost=0.0,
                turns=0,
                success=False,
                error=f"Failed to parse Claude response: {str(e)}"
            )

        except Exception as e:
            return ClaudeResponse(
                response="",
                session_id=session_id or "",
                cost=0.0,
                turns=0,
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

# Global wrapper instance
claude_wrapper = ClaudeWrapper()
