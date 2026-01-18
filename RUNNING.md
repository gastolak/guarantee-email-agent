# Running the Guarantee Email Agent

This guide explains how to run the complete warranty email processing pipeline.

## Prerequisites

1. **Python 3.10+** installed
2. **uv** package manager installed
3. **API Keys** for:
   - Anthropic API (for Claude LLM)
   - Gmail API
   - Warranty API
   - Ticketing System API

## Quick Start

### 1. Install Dependencies

```bash
# Install dependencies using uv
uv sync
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual API keys
# IMPORTANT: Never commit .env to git!
vim .env  # or nano .env, or your preferred editor
```

Required environment variables in `.env`:
```bash
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GMAIL_API_KEY=your_gmail_api_key_here
WARRANTY_API_KEY=your_warranty_api_key_here
TICKETING_API_KEY=your_ticketing_api_key_here
```

Optional environment variables:
```bash
LOG_LEVEL=INFO              # Override config: DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json             # Override config: json or text
CONFIG_PATH=./config.yaml   # Override default config path
```

### 3. Verify Configuration

```bash
# Check configuration is valid
uv run python -c "from guarantee_email_agent.config import load_config; print(load_config())"
```

### 4. Run the Agent

```bash
# Start the agent with default config
uv run guarantee-email-agent run

# Or specify a custom config file
uv run guarantee-email-agent run --config ./custom-config.yaml
```

## What Happens When You Run

The agent follows this startup sequence:

1. **Startup Banner** - Displays version and agent info
2. **Configuration Loading** - Loads `config.yaml` and environment variables
3. **Startup Validations**:
   - Config schema validation
   - Secret verification (all API keys present)
   - Instruction file verification
   - MCP connection testing (Gmail, Warranty API, Ticketing)
   - Creates eval directory if missing
4. **Email Processor Initialization** - Sets up the email processing pipeline
5. **Agent Runner Initialization** - Sets up inbox monitoring loop
6. **Signal Handlers Registration** - Handles Ctrl+C and SIGTERM for graceful shutdown
7. **Inbox Monitoring Loop** - Starts polling Gmail inbox

### During Operation

The agent will:
- Poll Gmail inbox every 60 seconds (configurable in `config.yaml`)
- Process each email through the complete pipeline:
  1. **Parse** email from Gmail format
  2. **Extract** serial number (pattern-based fast path, LLM fallback)
  3. **Detect** scenario (heuristics + LLM orchestration)
  4. **Route** to appropriate scenario handler
  5. **Validate** warranty (if applicable) via Warranty API
  6. **Generate** response using Claude LLM
  7. **Send** email response via Gmail
  8. **Create** ticket (if valid warranty) via Ticketing API
  9. **Log** all operations with structured context

### Graceful Shutdown

Press **Ctrl+C** or send **SIGTERM** to gracefully shutdown:
- Current email processing completes
- Connections cleaned up
- Resources released
- Exit code 0 on clean shutdown

## CLI Commands

### Run Command

```bash
# Start the agent
uv run guarantee-email-agent run

# With custom config
uv run guarantee-email-agent run --config ./custom-config.yaml

# Help
uv run guarantee-email-agent run --help
```

### Version

```bash
# Show version
uv run guarantee-email-agent --version
uv run guarantee-email-agent -v
```

### Eval Command (Coming in Epic 4)

```bash
# Run evaluation suite (not yet implemented)
uv run guarantee-email-agent eval
```

## Configuration

The agent uses `config.yaml` for non-secret configuration:

```yaml
# Logging Configuration
logging:
  level: "INFO"           # DEBUG, INFO, WARNING, ERROR
  json_format: false      # true for production, false for dev
  log_to_stdout: true     # Always true (NFR16: stateless)

# Instruction Files
instructions:
  main: "./instructions/main.md"
  scenarios:
    - "./instructions/scenarios/valid-warranty.md"
    - "./instructions/scenarios/invalid-warranty.md"
    - "./instructions/scenarios/missing-info.md"
    - "./instructions/scenarios/graceful-degradation.md"

# MCP Connections
mcp:
  gmail:
    connection_string: "mcp://gmail"
  warranty_api:
    connection_string: "mcp://warranty-api"
    endpoint: "https://api.example.com/warranty/check"
  ticketing_system:
    connection_string: "mcp://ticketing"
    endpoint: "https://tickets.example.com/api/v1"

# Evaluation
eval:
  pass_threshold: 99.0
  test_suite_path: "./evals/scenarios/"
```

## Logging

### Development Mode (Human-Readable)

```yaml
logging:
  level: "DEBUG"          # Show all logs including email bodies
  json_format: false      # Human-readable text format
  log_to_stdout: true
```

Output example:
```
2026-01-18 14:30:45 [INFO] guarantee_email_agent.cli: Loading configuration from config.yaml
2026-01-18 14:30:45 [INFO] guarantee_email_agent.agent.startup: Running startup validations...
2026-01-18 14:30:46 [INFO] guarantee_email_agent.agent.startup: ✓ All startup validations passed
2026-01-18 14:30:46 [INFO] guarantee_email_agent.agent.runner: Starting inbox monitoring loop...
```

### Production Mode (Machine-Readable)

```yaml
logging:
  level: "INFO"           # No email bodies (NFR14)
  json_format: true       # JSON format for log aggregation
  log_to_stdout: true
```

Or via environment:
```bash
LOG_FORMAT=json LOG_LEVEL=INFO uv run guarantee-email-agent run
```

Output example:
```json
{"timestamp":"2026-01-18T14:30:45.123Z","level":"INFO","logger":"guarantee_email_agent.cli","message":"Loading configuration from config.yaml"}
{"timestamp":"2026-01-18T14:30:45.456Z","level":"INFO","logger":"guarantee_email_agent.agent.startup","message":"Running startup validations..."}
{"timestamp":"2026-01-18T14:30:46.789Z","level":"INFO","logger":"guarantee_email_agent.agent.runner","message":"Starting inbox monitoring loop...","context":{"polling_interval_seconds":60}}
```

### Customer Data Protection (NFR14)

**IMPORTANT**: Email body content is **ONLY** logged at DEBUG level:
- **INFO level**: Email metadata only (subject, from, message_id)
- **DEBUG level**: Full email body included

For production, always use `INFO` level to protect customer data.

## Exit Codes

- **0**: Success (clean shutdown)
- **1**: Unexpected error
- **2**: Configuration error
- **3**: MCP connection error

## Troubleshooting

### "Configuration validation failed"
- Check `config.yaml` syntax (valid YAML)
- Verify all required fields are present
- Ensure instruction files exist at specified paths

### "MCP connection failed"
- Verify API keys in `.env` file
- Check MCP connection strings in `config.yaml`
- Test network connectivity to API endpoints

### "Missing API key"
- Ensure all 4 API keys are set in `.env`:
  - `ANTHROPIC_API_KEY`
  - `GMAIL_API_KEY`
  - `WARRANTY_API_KEY`
  - `TICKETING_API_KEY`

### "Instruction file not found"
- Verify file paths in `config.yaml`
- Check files exist: `instructions/main.md` and scenario files

### High Memory Usage
- Reduce polling frequency in config
- Enable JSON logging (more efficient than text)
- Check for memory leaks in MCP clients

### Slow Processing
- Check LLM response times (should be <10s)
- Verify warranty API response times
- Enable DEBUG logging to see step timing

## Testing

Run the complete test suite:

```bash
# All tests
uv run pytest tests/ -v

# Specific test module
uv run pytest tests/agent/test_runner.py -v

# With coverage
uv run pytest tests/ --cov=src/guarantee_email_agent --cov-report=term-missing
```

Current test status: **260 tests passing, 2 skipped**

## Development

### Debug Mode

```bash
# Enable DEBUG logging to see all operations
LOG_LEVEL=DEBUG uv run guarantee-email-agent run
```

### Manual Testing

```python
# Test email processor directly
from guarantee_email_agent.config import load_config
from guarantee_email_agent.email import create_email_processor

config = load_config()
processor = create_email_processor(config)

# Mock email data
email_data = {
    "subject": "Warranty claim for SN-12345",
    "body": "My product stopped working. Serial: SN-12345",
    "from": "customer@example.com",
    "received": "2026-01-18T10:30:00Z",
    "message_id": "test-123"
}

# Process
result = await processor.process_email(email_data)
print(result)
```

## Architecture

The complete pipeline consists of:

1. **Agent Runner** (`src/guarantee_email_agent/agent/runner.py`)
   - Inbox monitoring loop
   - Graceful shutdown handling
   - Consecutive error tracking

2. **Email Processor** (`src/guarantee_email_agent/email/processor.py`)
   - Email parsing
   - Serial number extraction (pattern + LLM)
   - Scenario detection (heuristics + LLM)
   - Warranty validation
   - Response generation
   - Email sending
   - Ticket creation

3. **LLM Orchestration** (`src/guarantee_email_agent/llm/`)
   - Orchestrator: Scenario detection
   - Response Generator: Email responses

4. **MCP Clients** (`src/guarantee_email_agent/integrations/mcp/`)
   - Gmail client
   - Warranty API client
   - Ticketing system client

5. **Graceful Degradation** (`src/guarantee_email_agent/email/graceful_handler.py`)
   - Out-of-scope handling
   - Missing information
   - API failures
   - Edge cases

6. **Structured Logging** (`src/guarantee_email_agent/utils/logging.py`)
   - JSON formatter
   - Error context enrichment
   - Performance tracking

## Next Steps

After Epic 3 completion, Epic 4 will add:
- **Story 4.1**: Evaluation framework (YAML test format, execution, pass rate calculation)
- **Story 4.2**: Eval reporting and continuous improvement
- **Story 4.3**: Enhanced error handling and comprehensive logging
- **Story 4.4**: Production hardening (daemon mode, idempotent startup)

## Support

For issues or questions:
- Review logs in DEBUG mode
- Check test suite: `uv run pytest tests/ -v`
- Verify configuration: `config.yaml` and `.env`
- Consult implementation artifacts in `_bmad-output/implementation-artifacts/`
