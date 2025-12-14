from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn
from pathlib import Path

from config import config

# Initialize FastAPI app
app = FastAPI(
    title="Portal UI",
    description="Static file server for the web interface",
    version="1.0.0"
)

# Get the directory where this file is located
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

# Health check
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "portal-ui"}

# Serve index.html at root
@app.get("/")
async def serve_index():
    """Serve the main HTML page"""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"error": "index.html not found"}, 404

# Serve JavaScript
@app.get("/app.js")
async def serve_js():
    """Serve JavaScript file"""
    js_path = STATIC_DIR / "app.js"
    if js_path.exists():
        return FileResponse(
            js_path,
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return {"error": "app.js not found"}, 404

# Serve CSS
@app.get("/styles.css")
async def serve_css():
    """Serve CSS file"""
    css_path = STATIC_DIR / "styles.css"
    if css_path.exists():
        return FileResponse(css_path, media_type="text/css")
    return {"error": "styles.css not found"}, 404

def main():
    """Start the portal UI server"""
    print(f"Starting Portal UI Server...")
    print(f"Server URL: http://{config.UI_SERVER_HOST}:{config.UI_SERVER_PORT}")
    print(f"Agent API URL: http://{config.AGENT_API_HOST}:{config.AGENT_API_PORT}\n")

    uvicorn.run(
        app,
        host=config.UI_SERVER_HOST,
        port=config.UI_SERVER_PORT,
        log_level="info"
    )

if __name__ == "__main__":
    main()
