#!/bin/bash
set -e

echo "🚂 Railway Startup Script"
echo "=========================="

# Decode token.pickle from base64 environment variable
if [ -n "$GMAIL_TOKEN_PICKLE_BASE64" ]; then
    echo "📦 Decoding token.pickle from environment variable..."
    echo "$GMAIL_TOKEN_PICKLE_BASE64" | base64 --decode > token.pickle
    echo "✅ token.pickle decoded successfully"
else
    echo "⚠️  GMAIL_TOKEN_PICKLE_BASE64 not set - will use GMAIL_OAUTH_TOKEN fallback"

    # Check if token.pickle exists in repo (shouldn't, but check anyway)
    if [ ! -f "token.pickle" ]; then
        echo "⚠️  No token.pickle found - token refresh may fail"
        echo "   Agent will attempt to use GMAIL_OAUTH_TOKEN from environment"
    fi
fi

# Show configuration (without secrets)
echo ""
echo "📋 Configuration:"
echo "   Python: $(python --version 2>&1)"
echo "   Working directory: $(pwd)"
echo "   Token pickle exists: $([ -f token.pickle ] && echo 'Yes' || echo 'No')"
echo ""

# Start the agent
echo "🤖 Starting Guarantee Email Agent..."
echo "=========================="
exec uv run python -m guarantee_email_agent run
