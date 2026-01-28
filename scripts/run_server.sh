#!/bin/bash
#
# run_server.sh - Start Streamlit server for network access
#
# Usage:
#   ./scripts/run_server.sh                    # Run on 0.0.0.0:8501
#   FIN_HOST=127.0.0.1 ./scripts/run_server.sh # Run on localhost only
#   FIN_PORT=8080 ./scripts/run_server.sh      # Run on different port
#
# Environment variables:
#   FIN_HOST - Host to bind to (default: 0.0.0.0 for network access)
#   FIN_PORT - Port to listen on (default: 8501)
#
# Copyright (C) 2024-2026 Or Hasson
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e

# Default to network-accessible binding
HOST=${FIN_HOST:-0.0.0.0}
PORT=${FIN_PORT:-8501}

# Find the script's directory and navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Check for virtual environment
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

echo "Starting Streamlit server..."
echo "  Host: $HOST"
echo "  Port: $PORT"
echo ""

if [ "$HOST" = "0.0.0.0" ]; then
    echo "Server will be accessible at:"
    echo "  - http://localhost:$PORT (this machine)"
    # Get local IP addresses
    if command -v hostname &> /dev/null; then
        LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ipconfig getifaddr en0 2>/dev/null || echo "")
        if [ -n "$LOCAL_IP" ]; then
            echo "  - http://$LOCAL_IP:$PORT (local network)"
        fi
    fi
    echo ""
    echo "Note: Enable authentication for network access with:"
    echo "  fin-cli auth add-user <username>"
    echo "  fin-cli auth enable"
fi

echo ""

# Run Streamlit
exec streamlit run streamlit_app/app.py \
    --server.address="$HOST" \
    --server.port="$PORT" \
    --server.headless=true
