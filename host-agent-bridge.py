#!/usr/bin/env python3
"""
Simple HTTP bridge that runs on the host to execute AI agent CLI commands.
The Docker container calls this service via host.docker.internal:8001

Supports any AI agent CLI that follows similar patterns (Claude Code, etc.)
"""
import subprocess
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import sys

# Load environment variables from .env file
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

class AgentBridgeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/execute':
            self.send_response(404)
            self.end_headers()
            return

        # Read request body
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        request_data = json.loads(body)

        # Extract command arguments
        args = request_data.get('args', [])
        cwd = request_data.get('cwd', None)
        timeout = request_data.get('timeout', 300)

        try:
            # Get agent CLI command from env (defaults to 'claude')
            cli_command = os.getenv('AGENT_CLI_COMMAND', 'claude')

            # Execute agent CLI command
            result = subprocess.run(
                [cli_command] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            response = {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except subprocess.TimeoutExpired:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Command timeout'}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def log_message(self, format, *args):
        # Custom logging
        sys.stderr.write(f"[AgentBridge] {format % args}\n")

if __name__ == '__main__':
    port = 8001
    server = HTTPServer(('0.0.0.0', port), AgentBridgeHandler)
    print(f"Agent Host Bridge running on port {port}")
    print("Waiting for requests from Docker container...")
    server.serve_forever()
