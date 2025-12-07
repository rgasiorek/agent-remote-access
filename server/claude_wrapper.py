import json
import subprocess
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
        Execute Claude Code command and parse response

        Args:
            message: User's message/prompt
            session_id: Existing session UUID (None for new session)

        Returns:
            ClaudeResponse with parsed output

        Raises:
            subprocess.TimeoutExpired: If command exceeds timeout
            subprocess.CalledProcessError: If command fails
        """
        # Build command
        cmd = ["claude", "-p", message, "--output-format", "json"]

        if session_id:
            cmd.extend(["--resume", session_id])

        try:
            # Execute command
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            # Parse JSON output
            if result.returncode == 0:
                output = json.loads(result.stdout)

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
                    error=f"Claude CLI error: {result.stderr}"
                )

        except subprocess.TimeoutExpired:
            return ClaudeResponse(
                response="",
                session_id=session_id or "",
                cost=0.0,
                turns=0,
                success=False,
                error=f"Request timed out after {self.timeout} seconds"
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
