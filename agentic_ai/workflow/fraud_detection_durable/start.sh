#!/bin/bash
# Start both worker and backend processes

echo "Starting Fraud Detection Durable Workflow..."
echo "DTS Endpoint: $DTS_ENDPOINT"

# Start worker in background
echo "Starting worker..."
python worker.py &
WORKER_PID=$!

# Wait a bit for worker to connect to DTS
sleep 5

# Start backend in foreground
echo "Starting backend on port ${BACKEND_PORT:-8002}..."
python backend.py

# If backend exits, kill worker
kill $WORKER_PID 2>/dev/null
