#!/bin/bash
# Check guarantee-email-agent status

PROCESS_NAME="agent run"

echo "=== Guarantee Email Agent Status ==="
echo

# Find agent process
PID=$(pgrep -f "$PROCESS_NAME")

if [ -z "$PID" ]; then
    echo "Status: NOT RUNNING"
    echo
    exit 1
else
    echo "Status: RUNNING"
    echo "PID: $PID"
    echo
    
    # Show process details
    echo "Process details:"
    ps -p "$PID" -o pid,ppid,user,%cpu,%mem,etime,command
    echo
    
    # Show open files (if lsof available)
    if command -v lsof &> /dev/null; then
        echo "Open files count: $(lsof -p "$PID" 2>/dev/null | wc -l)"
    fi
    
    exit 0
fi
