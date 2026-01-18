#!/bin/bash
# Stop guarantee-email-agent gracefully

PROCESS_NAME="agent run"
TIMEOUT=30

echo "=== Stopping Guarantee Email Agent ==="
echo

# Find agent process
PID=$(pgrep -f "$PROCESS_NAME")

if [ -z "$PID" ]; then
    echo "Agent is not running"
    exit 0
fi

echo "Found agent process: PID $PID"
echo "Sending SIGTERM (graceful shutdown)..."

# Send SIGTERM
kill -TERM "$PID"

# Wait for process to exit
echo "Waiting up to ${TIMEOUT}s for graceful shutdown..."
for i in $(seq 1 "$TIMEOUT"); do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "✓ Agent stopped gracefully after ${i}s"
        exit 0
    fi
    sleep 1
    if [ $((i % 5)) -eq 0 ]; then
        echo "  Still waiting... (${i}/${TIMEOUT}s)"
    fi
done

# Force kill if still running
echo "⚠ Timeout exceeded, sending SIGKILL..."
kill -KILL "$PID" 2>/dev/null
sleep 1

if ps -p "$PID" > /dev/null 2>&1; then
    echo "✗ Failed to stop agent"
    exit 1
else
    echo "✓ Agent stopped (forced)"
    exit 0
fi
