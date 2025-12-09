FROM python:3.11-slim

# Set working directory
WORKDIR /app

# No need to install system dependencies or Claude CLI
# Claude CLI will be mounted from the host

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server/ ./server/
COPY frontend/ ./frontend/

# Create necessary directories
RUN mkdir -p /app/sessions /workspace

# Expose port
EXPOSE 8000

# Set environment variables
# HOME is needed for Claude CLI to resolve symlinks correctly
ENV PYTHONUNBUFFERED=1 \
    CLAUDE_PROJECT_PATH=/workspace \
    HOME=/Users/montrosesoftware \
    PATH="/Users/montrosesoftware/.local/bin:$PATH"

# Run the FastAPI server
CMD ["python", "-m", "server.main"]
