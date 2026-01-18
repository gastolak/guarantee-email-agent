#!/bin/bash
set -e

# Handle signals and forward to agent
_term() {
    echo "SIGTERM received, forwarding to agent..." >&2
    kill -TERM "$agent_pid" 2>/dev/null || true
}

_hup() {
    echo "SIGHUP received, forwarding to agent..." >&2
    kill -HUP "$agent_pid" 2>/dev/null || true
}

trap _term SIGTERM SIGINT
trap _hup SIGHUP

# Start agent in background with exec to make it PID 1's child
uv run python -m guarantee_email_agent run "$@" &
agent_pid=$!

# Wait for agent to exit
wait "$agent_pid"
exit_code=$?

echo "Agent exited with code $exit_code" >&2
exit $exit_code
