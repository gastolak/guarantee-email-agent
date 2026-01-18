# Deployment Guide

This guide covers production deployment options for the Guarantee Email Agent.

## Table of Contents

1. [Overview](#overview)
2. [Systemd (Linux)](#systemd-linux)
3. [Launchd (macOS)](#launchd-macos)
4. [Docker](#docker)
5. [Railway](#railway)
6. [Process Management](#process-management)
7. [Log Management](#log-management)
8. [Troubleshooting](#troubleshooting)

## Overview

The Guarantee Email Agent is designed for production deployment with:

- **Single-process architecture**: Manageable by systemd, launchd, Docker
- **Unix signal handling**: Graceful shutdown on SIGTERM/SIGINT, log rotation on SIGHUP
- **Idempotent startup**: Safe to restart repeatedly, no manual cleanup required
- **Stdout/stderr separation**: INFO/DEBUG → stdout, WARNING/ERROR → stderr
- **Optional file logging**: For daemon mode with log rotation support

### Exit Codes

The agent uses standard exit codes per NFR29:

- `0` - Success (clean shutdown)
- `1` - Unexpected error
- `2` - Configuration error
- `3` - MCP connection failure during startup
- `4` - Eval failure (pass rate <99%)

## Systemd (Linux)

Systemd is the recommended deployment method for Linux production servers.

### Installation

1. **Copy service file:**
   ```bash
   sudo cp deployment/systemd/agent.service /etc/systemd/system/guarantee-email-agent.service
   ```

2. **Edit service file with your configuration:**
   ```bash
   sudo nano /etc/systemd/system/guarantee-email-agent.service
   ```
   
   Update:
   - `User` and `Group` (create dedicated user)
   - `WorkingDirectory` (installation path)
   - `Environment` variables (API keys, credentials)
   - `ExecStart` (uv path, config path)

3. **Create application directory:**
   ```bash
   sudo mkdir -p /opt/guarantee-email-agent
   sudo chown agent:agent /opt/guarantee-email-agent
   ```

4. **Install application:**
   ```bash
   cd /opt/guarantee-email-agent
   git clone <repo-url> .
   uv sync
   cp config.example.yaml config.yaml
   # Edit config.yaml with your settings
   ```

5. **Reload systemd and start service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable guarantee-email-agent
   sudo systemctl start guarantee-email-agent
   ```

### Management Commands

```bash
# Check status
sudo systemctl status guarantee-email-agent

# View logs
sudo journalctl -u guarantee-email-agent -f

# Restart
sudo systemctl restart guarantee-email-agent

# Stop
sudo systemctl stop guarantee-email-agent

# View recent logs
sudo journalctl -u guarantee-email-agent --since "1 hour ago"
```

### Service File Reference

Key settings in `deployment/systemd/agent.service`:

- `Type=simple`: Single-process service
- `Restart=on-failure`: Auto-restart on crashes
- `KillMode=mixed`: Send SIGTERM to main process
- `KillSignal=SIGTERM`: Graceful shutdown signal
- `TimeoutStopSec=30`: Wait 30s for graceful shutdown
- `StandardOutput=journal`: Logs to systemd journal
- `StandardError=journal`: Errors to systemd journal

## Launchd (macOS)

Launchd is the macOS process manager for daemon services.

### Installation

1. **Copy plist file:**
   ```bash
   cp deployment/launchd/com.example.agent.plist ~/Library/LaunchAgents/
   ```

2. **Edit plist with your configuration:**
   ```bash
   nano ~/Library/LaunchAgents/com.example.agent.plist
   ```
   
   Update:
   - `ProgramArguments` (uv path, python path, config path)
   - `WorkingDirectory` (installation path)
   - `EnvironmentVariables` (API keys, credentials)
   - `StandardOutPath` and `StandardErrorPath` (log paths)

3. **Load service:**
   ```bash
   launchctl load ~/Library/LaunchAgents/com.example.agent.plist
   ```

### Management Commands

```bash
# Check if running
launchctl list | grep guarantee-email-agent

# Start (if not auto-started)
launchctl start com.example.guarantee-email-agent

# Stop
launchctl stop com.example.guarantee-email-agent

# Unload (disable)
launchctl unload ~/Library/LaunchAgents/com.example.agent.plist

# View logs
tail -f /opt/guarantee-email-agent/logs/stdout.log
tail -f /opt/guarantee-email-agent/logs/stderr.log
```

### Plist File Reference

Key settings in `deployment/launchd/com.example.agent.plist`:

- `RunAtLoad=true`: Start on boot
- `KeepAlive=true`: Auto-restart on crashes
- `StandardOutPath`: Stdout log file
- `StandardErrorPath`: Stderr log file

## Docker

Docker provides containerized deployment with consistent environments.

### Building Image

```bash
# From project root
docker build -t guarantee-email-agent -f deployment/docker/Dockerfile .
```

### Running Container

```bash
docker run -d \
  --name guarantee-email-agent \
  -e ANTHROPIC_API_KEY="your-key" \
  -e GMAIL_CREDENTIALS="/app/credentials.json" \
  -e WARRANTY_API_KEY="your-key" \
  -e TICKETING_API_KEY="your-key" \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/credentials.json:/app/credentials.json \
  -v $(pwd)/logs:/app/logs \
  guarantee-email-agent
```

### Management Commands

```bash
# View logs
docker logs -f guarantee-email-agent

# Check status
docker ps -f name=guarantee-email-agent

# Stop (graceful shutdown)
docker stop guarantee-email-agent

# Restart
docker restart guarantee-email-agent

# Remove
docker rm -f guarantee-email-agent
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  agent:
    build:
      context: .
      dockerfile: deployment/docker/Dockerfile
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GMAIL_CREDENTIALS=/app/credentials.json
      - WARRANTY_API_KEY=${WARRANTY_API_KEY}
      - TICKETING_API_KEY=${TICKETING_API_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./config.yaml:/app/config.yaml
      - ./credentials.json:/app/credentials.json
      - ./logs:/app/logs
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
docker-compose logs -f
docker-compose stop
```

## Railway

Railway provides managed deployment with automatic builds and logs.

### Setup

1. **Create Railway project:**
   - Go to https://railway.app
   - Create new project from GitHub repo

2. **Configure environment variables:**
   Add in Railway dashboard:
   - `ANTHROPIC_API_KEY`
   - `GMAIL_CREDENTIALS` (as file or base64)
   - `WARRANTY_API_KEY`
   - `TICKETING_API_KEY`
   - `LOG_LEVEL=INFO`

3. **Verify Procfile:**
   Ensure `Procfile` exists in project root:
   ```
   web: uv run python -m guarantee_email_agent run
   ```

4. **Deploy:**
   - Push to GitHub main branch
   - Railway auto-deploys

### Management

- **View logs**: Railway dashboard → Logs tab
- **Restart**: Railway dashboard → Restart button
- **Environment variables**: Railway dashboard → Variables tab

### Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# View logs
railway logs

# Run locally with Railway environment
railway run python -m guarantee_email_agent run
```

## Process Management

### Manual Process Management

Start agent in background:
```bash
# Using nohup
nohup uv run python -m guarantee_email_agent run &

# Using built-in backgrounding
uv run python -m guarantee_email_agent run > agent.log 2>&1 &
```

Check status:
```bash
# Find process
pgrep -f "agent run"

# Detailed status
./scripts/agent-status.sh
```

Stop agent:
```bash
# Graceful shutdown
pkill -TERM -f "agent run"

# Using helper script
./scripts/agent-stop.sh

# Force kill (if unresponsive)
pkill -KILL -f "agent run"
```

### Log Rotation

Send SIGHUP to rotate logs:
```bash
PID=$(pgrep -f "agent run")
kill -HUP $PID
```

Compatible with logrotate:
```conf
# /etc/logrotate.d/guarantee-email-agent
/opt/guarantee-email-agent/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 agent agent
    sharedscripts
    postrotate
        killall -HUP -u agent python || true
    endscript
}
```

## Log Management

### Output Separation

The agent separates logs by severity:

- **Stdout**: INFO and DEBUG messages
- **Stderr**: WARNING, ERROR, CRITICAL messages

Capture separately:
```bash
uv run python -m guarantee_email_agent run > stdout.log 2> stderr.log
```

Or combine:
```bash
uv run python -m guarantee_email_agent run > combined.log 2>&1
```

### File Logging

Configure file logging in `config.yaml`:

```yaml
logging:
  level: INFO
  file_path: /var/log/guarantee-email-agent/agent.log
```

File logging captures all levels and supports rotation via SIGHUP.

### Viewing Logs

```bash
# Tail logs
tail -f /var/log/guarantee-email-agent/agent.log

# Search for errors
grep ERROR /var/log/guarantee-email-agent/agent.log

# Filter by date
grep "2026-01-18" /var/log/guarantee-email-agent/agent.log

# Show last 100 lines
tail -100 /var/log/guarantee-email-agent/agent.log
```

## Troubleshooting

### Agent Won't Start

1. **Check configuration:**
   ```bash
   uv run python -m guarantee_email_agent run --config config.yaml
   ```
   Look for configuration errors (exit code 2).

2. **Check MCP connections:**
   Configuration validation tests MCP connections on startup.
   Check stderr for connection errors (exit code 3).

3. **Check logs:**
   ```bash
   # Systemd
   sudo journalctl -u guarantee-email-agent -n 50

   # File logs
   tail -50 /var/log/guarantee-email-agent/agent.log

   # Docker
   docker logs guarantee-email-agent
   ```

### Agent Crashes

1. **Check exit code:**
   - 0: Normal shutdown
   - 1: Unexpected error (check logs)
   - 2: Configuration error
   - 3: MCP connection failure

2. **Enable debug logging:**
   ```yaml
   logging:
     level: DEBUG
   ```

3. **Check resource limits:**
   ```bash
   ulimit -a
   ```

### High Memory/CPU Usage

1. **Check process stats:**
   ```bash
   ./scripts/agent-status.sh
   ```

2. **Monitor resources:**
   ```bash
   # CPU and memory
   top -p $(pgrep -f "agent run")

   # Open files
   lsof -p $(pgrep -f "agent run") | wc -l
   ```

3. **Review polling interval:**
   Increase if processing is slow:
   ```yaml
   agent:
     polling_interval_seconds: 120  # Default: 60
   ```

### Logs Not Rotating

1. **Verify SIGHUP handler:**
   ```bash
   PID=$(pgrep -f "agent run")
   kill -HUP $PID
   # Check logs for "SIGHUP received, rotating log files"
   ```

2. **Check logrotate configuration:**
   ```bash
   sudo logrotate -d /etc/logrotate.d/guarantee-email-agent
   ```

3. **Verify file permissions:**
   ```bash
   ls -la /var/log/guarantee-email-agent/
   ```

### Docker Container Won't Stop

1. **Check container logs:**
   ```bash
   docker logs guarantee-email-agent
   ```

2. **Force stop:**
   ```bash
   docker rm -f guarantee-email-agent
   ```

3. **Verify entrypoint signal handling:**
   Ensure `deployment/docker/entrypoint.sh` is executable.

## Security Best Practices

1. **Run as non-root user:**
   - Systemd: Set `User=` and `Group=`
   - Docker: Image uses non-root user
   - Manual: Use dedicated `agent` user

2. **Protect secrets:**
   - Use environment variables, not hardcoded values
   - Set file permissions: `chmod 600 credentials.json`
   - Use secret management: AWS Secrets Manager, HashiCorp Vault

3. **Enable security hardening:**
   - Systemd: `NoNewPrivileges=true`, `PrivateTmp=true`
   - Docker: Run as non-root, read-only filesystem

4. **Monitor logs:**
   - Set up log aggregation (ELK, Splunk)
   - Alert on ERROR logs
   - Monitor exit codes

## Support

For issues or questions:
- Check logs with DEBUG level
- Review GitHub issues
- Consult project README
- Contact support team
