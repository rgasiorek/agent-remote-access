from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import subprocess
import uuid
import os
import json
from pathlib import Path

from config import config
from auth import verify_auth
from claude_wrapper import ClaudeWrapper

# Validate configuration on startup
config.validate()

# Initialize Claude wrapper with configured project path
claude_wrapper = ClaudeWrapper(project_path=config.PROJECT_PATH)

# Initialize FastAPI app
app = FastAPI(
    title="Agent API",
    description="API for communicating with AI agent CLI",
    version="1.0.0"
)

# Enable CORS - allow all origins since Nginx acts as gateway
# All external requests come through Nginx, internal requests come from portal-ui
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    cost: float
    turns: int
    success: bool
    error: Optional[str] = None

class AsyncTaskResponse(BaseModel):
    task_id: str
    status: str  # "processing"

class TaskStatusResponse(BaseModel):
    status: str  # "processing", "completed", "not_found"
    result: Optional[dict] = None

# Health check (no auth required)
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "agent-api"}

# Chat endpoint (requires auth)
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, username: str = Depends(verify_auth)):
    """
    Send message to Claude Code and get response

    Args:
        request: ChatRequest with message and optional session_id
        username: Authenticated username (injected by verify_auth)

    Returns:
        ChatResponse with Claude's response and session info
    """
    try:
        # Execute Claude command
        result = claude_wrapper.execute(
            message=request.message,
            session_id=request.session_id  # None = new session, provided = resume that session
        )

        return ChatResponse(
            response=result.response,
            session_id=result.session_id,
            cost=result.cost,
            turns=result.turns,
            success=result.success,
            error=result.error
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

# RESTful async chat endpoints to bypass Cloudflare timeout
@app.post("/api/sessions/{session_id}/chat", response_model=AsyncTaskResponse)
async def submit_chat_task(session_id: str, request: ChatRequest, username: str = Depends(verify_auth)):
    """
    Submit async chat task to Claude Code - returns immediately with task_id

    Args:
        session_id: Session ID to resume, or "new" for new session
        request: ChatRequest with message

    Returns:
        AsyncTaskResponse with task_id for polling
    """
    task_id = str(uuid.uuid4())
    output_file = f"/tmp/claude_task_{task_id}.json"

    # Build command
    args = ["claude", "-p", request.message, "--output-format", "json"]

    # Use session_id from path if not "new"
    if session_id != "new":
        args.extend(["--resume", session_id])

    # Start Claude CLI with output redirected to temp file
    try:
        with open(output_file, 'w') as f:
            subprocess.Popen(
                args,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=claude_wrapper.project_path
            )

        return AsyncTaskResponse(task_id=task_id, status="processing")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

@app.get("/api/sessions/{session_id}/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(session_id: str, task_id: str, username: str = Depends(verify_auth)):
    """
    Poll for task completion status

    Args:
        session_id: Session ID (for REST hierarchy)
        task_id: Task ID to check

    Returns:
        TaskStatusResponse with status and result (if completed)
    """
    output_file = f"/tmp/claude_task_{task_id}.json"

    if not os.path.exists(output_file):
        return TaskStatusResponse(status="not_found")

    # Check if file has content
    try:
        with open(output_file, 'r') as f:
            content = f.read()

        if content.strip():
            # Process finished - parse result
            result = json.loads(content)
            return TaskStatusResponse(status="completed", result=result)
        else:
            # File exists but empty - still processing
            return TaskStatusResponse(status="processing")

    except json.JSONDecodeError:
        # File has partial content - still writing
        return TaskStatusResponse(status="processing")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading task status: {str(e)}")

@app.delete("/api/sessions/{session_id}/tasks/{task_id}")
async def cleanup_task(session_id: str, task_id: str, username: str = Depends(verify_auth)):
    """
    Cleanup task file after browser has rendered the result

    Args:
        session_id: Session ID (for REST hierarchy)
        task_id: Task ID to cleanup

    Returns:
        Status message
    """
    output_file = f"/tmp/claude_task_{task_id}.json"

    try:
        if os.path.exists(output_file):
            os.remove(output_file)
            return {"status": "cleaned"}
        else:
            return {"status": "not_found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up task: {str(e)}")

# Get available Claude Code sessions
@app.get("/api/sessions")
async def get_sessions(username: str = Depends(verify_auth)):
    """List available Claude Code sessions that can be resumed"""
    try:
        return claude_wrapper.list_sessions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")

# Config endpoint - provides project path to frontend
@app.get("/api/config")
async def get_config():
    """Get configuration including project path (no auth required for basic config)"""
    return {"project_path": config.PROJECT_PATH}

def main():
    """Start the agent API server"""
    print(f"Starting Agent API Server...")
    print(f"Project path: {config.PROJECT_PATH}")
    print(f"Server URL: http://{config.AGENT_API_HOST}:{config.AGENT_API_PORT}")
    print(f"Authentication: {config.AUTH_USERNAME} / {'*' * len(config.AUTH_PASSWORD)}\n")

    uvicorn.run(
        app,
        host=config.AGENT_API_HOST,
        port=config.AGENT_API_PORT,
        log_level="info"
    )

if __name__ == "__main__":
    main()
