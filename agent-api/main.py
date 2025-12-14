from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

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
