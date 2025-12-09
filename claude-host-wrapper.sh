#!/bin/bash
# Wrapper script that runs on the host to execute Claude CLI
# This is called from inside the Docker container

# Execute claude with all arguments passed through
/Users/montrosesoftware/.local/bin/claude "$@"
