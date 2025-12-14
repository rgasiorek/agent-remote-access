import json
import subprocess
from typing import Optional
from pydantic import BaseModel
from pathlib import Path

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
    Wrapper for executing Claude Code CLI commands directly on host
    Uses headless mode (claude -p) with JSON output
    """

    def __init__(self, project_path: str = None, timeout: int = 600):
        """
        Initialize Claude wrapper

        Args:
            project_path: Working directory for Claude context
            timeout: Maximum execution time in seconds (default: 10 minutes)
        """
        self.project_path = project_path or str(Path.cwd())
        self.timeout = timeout
        self.cli_command = "claude"  # Can be configured via env var
        self._check_authentication()

    def _check_authentication(self):
        """
        Check if Claude CLI is properly authenticated
        Raises an error if not authenticated
        """
        import os

        # Check if ~/.claude.json exists (created by 'claude login')
        claude_config = Path.home() / '.claude.json'

        if not claude_config.exists():
            raise RuntimeError(
                "Claude CLI is not authenticated. Please run 'claude login' in your terminal first."
            )

        # Ensure ANTHROPIC_API_KEY is not set (we rely on claude login)
        if os.getenv('ANTHROPIC_API_KEY'):
            print("Warning: ANTHROPIC_API_KEY is set in environment but will be ignored. Using 'claude login' authentication instead.")

    def execute(self, message: str, session_id: Optional[str] = None) -> ClaudeResponse:
        """
        Execute Claude Code command directly

        Args:
            message: User's message/prompt
            session_id: Existing session UUID (None for new session)

        Returns:
            ClaudeResponse with parsed output
        """
        # Build command arguments
        args = [self.cli_command, "-p", message, "--output-format", "json"]

        if session_id:
            args.extend(["--resume", session_id])

        try:
            # Prepare clean environment - remove ANTHROPIC_API_KEY to ensure we use claude login
            import os
            env = os.environ.copy()
            env.pop('ANTHROPIC_API_KEY', None)  # Remove if present

            # Execute claude CLI command directly
            result = subprocess.run(
                args,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env
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
                # Command failed - try to parse error from stdout JSON
                error_msg = result.stderr
                try:
                    error_output = json.loads(result.stdout)
                    if error_output.get('is_error'):
                        error_msg = error_output.get('result', error_msg)
                except:
                    pass

                # Detect specific error conditions
                if "Invalid API key" in error_msg:
                    if "claude -p" in str(result.args) or "headless" in error_msg.lower():
                        # This is likely because we're running inside an active Claude session
                        error_msg = "Cannot run Claude CLI in headless mode from within an active Claude Code session. Please exit the current session and test from a regular terminal."
                    else:
                        error_msg = "Invalid API key. Please run 'claude login' in your terminal to authenticate."

                return ClaudeResponse(
                    response="",
                    session_id=session_id or "",
                    cost=0.0,
                    turns=0,
                    success=False,
                    error=f"Agent CLI error: {error_msg}"
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

    def list_sessions(self):
        """List available Claude Code sessions from history - filtered by current project"""
        history_file = Path.home() / '.claude' / 'history.jsonl'

        if not history_file.exists():
            return {
                'sessions': [],
                'hint': f'No Claude Code sessions found. Start a session by running "claude" in {self.project_path} first.'
            }

        sessions = {}
        try:
            with open(history_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        session_id = entry.get('sessionId')
                        project = entry.get('project', '')

                        # ONLY include sessions from the current project path
                        if session_id and project == self.project_path:
                            # Keep only the most recent entry for each session
                            sessions[session_id] = {
                                'session_id': session_id,
                                'display': entry.get('display', '')[:100],
                                'project': project,
                                'timestamp': entry.get('timestamp', 0)
                            }
                    except json.JSONDecodeError:
                        continue

            # Sort by timestamp, most recent first
            sorted_sessions = sorted(sessions.values(), key=lambda x: x['timestamp'], reverse=True)

            result = {'sessions': sorted_sessions[:20]}

            # Add hint if no sessions found for this project
            if not sorted_sessions:
                result['hint'] = f'No Claude Code sessions found for project: {self.project_path}. Start a session by running "claude" in this directory first, or create a new session via the async chat API.'

            return result

        except Exception as e:
            return {'error': str(e), 'sessions': []}

# Global wrapper instance will be initialized by main.py with proper config
claude_wrapper = None
