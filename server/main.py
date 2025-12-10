from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import uvicorn
from pathlib import Path

from server.config import config
from server.auth import verify_auth
from server.session_manager import session_manager
from server.claude_wrapper import claude_wrapper

# Validate configuration on startup
config.validate()

# Initialize FastAPI app
app = FastAPI(
    title="Claude Code Remote Access",
    description="Remote access to Claude Code CLI sessions",
    version="1.0.0"
)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    conv_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    cost: float
    turns: int
    success: bool
    error: Optional[str] = None

class ResetResponse(BaseModel):
    message: str
    conv_id: str

# Health check (no auth required)
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "claude-remote-access"}

# Serve frontend
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the chat UI"""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return HTMLResponse("<h1>Frontend not found</h1><p>Run from project root directory</p>", status_code=404)

@app.get("/app.js")
async def serve_js():
    """Serve JavaScript file"""
    js_path = Path(__file__).parent.parent / "frontend" / "app.js"
    if js_path.exists():
        return FileResponse(js_path, media_type="application/javascript")
    return HTMLResponse("Not found", status_code=404)

@app.get("/styles.css")
async def serve_css():
    """Serve CSS file"""
    css_path = Path(__file__).parent.parent / "frontend" / "styles.css"
    if css_path.exists():
        return FileResponse(css_path, media_type="text/css")
    return HTMLResponse("Not found", status_code=404)

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
        # Get existing session or None for new conversation
        conv_id = request.conv_id or "default"
        existing_session = request.session_id or session_manager.get_session(conv_id)

        # Execute Claude command
        result = claude_wrapper.execute(
            message=request.message,
            session_id=existing_session
        )

        # Update session if successful
        if result.success:
            session_manager.update_session(
                conv_id=conv_id,
                session_id=result.session_id,
                turn_count=result.turns,
                last_message=request.message
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

# Reset conversation endpoint (requires auth)
@app.post("/api/reset", response_model=ResetResponse)
async def reset(conv_id: str = "default", username: str = Depends(verify_auth)):
    """
    Reset conversation session

    Args:
        conv_id: Conversation ID to reset (default: "default")
        username: Authenticated username

    Returns:
        ResetResponse confirming reset
    """
    try:
        session_manager.reset_session(conv_id)
        return ResetResponse(
            message="Conversation reset successfully",
            conv_id=conv_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset session: {str(e)}")

# Get available Claude Code sessions from host bridge
@app.get("/api/sessions")
async def get_sessions(username: str = Depends(verify_auth)):
    """List available Claude Code sessions that can be resumed"""
    import requests

    try:
        response = requests.get('http://host.docker.internal:8001/sessions', timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch sessions from host bridge")
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Cannot connect to host bridge: {str(e)}")

def main():
    """Start the server"""
    print(f"Starting Claude Code Remote Access Server...")
    print(f"Project path: {config.PROJECT_PATH}")
    print(f"Server URL: http://{config.HOST}:{config.PORT}")
    print(f"\nTo expose via ngrok, run: ngrok http {config.PORT}")
    print(f"Authentication: {config.AUTH_USERNAME} / {'*' * len(config.AUTH_PASSWORD)}\n")

    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level="info"
    )

if __name__ == "__main__":
    main()
