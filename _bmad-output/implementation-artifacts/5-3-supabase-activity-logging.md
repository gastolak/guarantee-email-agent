---
story_id: "5.3"
title: "Supabase Activity Logging - Complete Agent Telemetry"
category: "observability"
priority: "high"
epic: "Production Monitoring & Analytics"
estimated_effort: "3 days"
depends_on: ["5.1", "5.2"]
status: "ready_for_dev"
created: "2026-02-03"
updated: "2026-02-03"
---

# Story 5.3: Supabase Activity Logging - Complete Agent Telemetry

## Context

The warranty email agent currently logs to stdout/stderr and log files, but lacks persistent, queryable telemetry for:
- **Analytics**: Which steps are most common? Where do failures occur?
- **Debugging**: What was the exact input/output for a failed email?
- **Compliance**: Audit trail of all agent decisions and actions
- **Monitoring**: Real-time dashboard of agent activity and performance

**Solution:** Log all agent activity to **Supabase** (PostgreSQL database) with structured tables for emails, steps, function calls, and responses.

## User Story

**As a** CTO monitoring the warranty email agent in production
**I want** all agent activity (emails, steps, function calls, responses) logged to Supabase
**So that** I can query historical data, debug failures, monitor performance, and build analytics dashboards

## Architecture Overview

### Database Schema (Supabase PostgreSQL)

```sql
-- Main email processing sessions
-- PRIVACY NOTE: Full email bodies NOT stored to comply with GDPR
-- Only metadata and extracted fields stored for analytics
CREATE TABLE email_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id VARCHAR(255) UNIQUE NOT NULL,  -- Gmail message ID
    received_at TIMESTAMP NOT NULL,
    from_address VARCHAR(255) NOT NULL,
    email_subject TEXT NOT NULL,

    -- Extracted metadata (NO full email body for PII compliance)
    serial_number VARCHAR(100),  -- Extracted serial number
    issue_category VARCHAR(100),  -- e.g., 'warranty_inquiry', 'device_not_found', 'out_of_scope'
    email_body_hash VARCHAR(64),  -- SHA-256 hash for deduplication (not for recovery)
    email_body_length INTEGER,   -- Character count for analytics

    -- Processing status
    status VARCHAR(50) NOT NULL,  -- 'processing', 'completed', 'failed', 'halted'
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    total_duration_ms INTEGER,
    logs_finalized BOOLEAN DEFAULT FALSE,  -- True when all async logs complete

    -- Step sequence summary
    total_steps INTEGER DEFAULT 0,
    step_sequence TEXT[],  -- ['01-extract-serial', '02-check-warranty', ...]

    -- Final outcome
    outcome VARCHAR(100),  -- 'ticket_created', 'ai_opt_out', 'escalated', 'out_of_scope'
    ticket_id VARCHAR(50),
    error_message TEXT,

    -- Metadata
    agent_version VARCHAR(50),
    model_provider VARCHAR(50),  -- 'gemini', 'anthropic'
    model_name VARCHAR(100),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Data retention: Records auto-deleted after retention period
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '30 days'
);

-- Individual step executions
-- PRIVACY NOTE: LLM prompts/responses stored only for FAILED steps to reduce storage
-- Success cases store only structured output for performance analytics
CREATE TABLE step_executions (
    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES email_sessions(session_id) ON DELETE CASCADE,

    -- Step identification
    step_number INTEGER NOT NULL,  -- 1, 2, 3...
    step_name VARCHAR(100) NOT NULL,  -- '01-extract-serial'

    -- Step timing
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_ms INTEGER,

    -- Step input/output (structured only for success, full for failures)
    input_context_summary JSONB,  -- Key fields only (serial_number, ticket_id, etc.)
    llm_prompt_hash VARCHAR(64),  -- SHA-256 hash for deduplication
    llm_prompt TEXT,  -- Full prompt ONLY for failed steps (NULL for success)
    llm_response TEXT,  -- Full response ONLY for failed steps (NULL for success)
    llm_token_count INTEGER,  -- Token count for cost analysis
    parsed_output JSONB,  -- Structured output (serial_number, next_step, etc.)

    -- Routing
    next_step VARCHAR(100),
    routing_reason TEXT,

    -- Status
    status VARCHAR(50) NOT NULL,  -- 'success', 'failed', 'timeout'
    error_message TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Function calls made during steps
CREATE TABLE function_calls (
    call_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES step_executions(execution_id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES email_sessions(session_id) ON DELETE CASCADE,

    -- Function details
    function_name VARCHAR(100) NOT NULL,  -- 'check_warranty', 'create_ticket', 'send_email'
    function_args JSONB NOT NULL,

    -- Call timing
    called_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_ms INTEGER,

    -- Response
    function_response JSONB,
    status VARCHAR(50) NOT NULL,  -- 'success', 'failed', 'timeout'
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Email responses sent by agent
-- PRIVACY NOTE: Full email bodies NOT stored for GDPR compliance
-- Only template name and key variables stored for audit trail
CREATE TABLE email_responses (
    response_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES email_sessions(session_id) ON DELETE CASCADE,

    -- Email details (NO full body)
    recipient_type VARCHAR(50) NOT NULL,  -- 'customer', 'admin', 'supervisor'
    recipient_email VARCHAR(255) NOT NULL,
    subject TEXT NOT NULL,
    template_name VARCHAR(100),  -- e.g., 'device-not-found', 'valid-warranty'
    template_variables JSONB,  -- Key variables used (ticket_id, serial_number, etc.)
    body_length INTEGER,  -- Character count for analytics

    -- Sending status
    sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL,  -- 'sent', 'failed'
    error_message TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX idx_email_sessions_received_at ON email_sessions(received_at DESC);
CREATE INDEX idx_email_sessions_status ON email_sessions(status);
CREATE INDEX idx_email_sessions_outcome ON email_sessions(outcome);
CREATE INDEX idx_email_sessions_from_address ON email_sessions(from_address);
CREATE INDEX idx_email_sessions_serial_number ON email_sessions(serial_number);
CREATE INDEX idx_email_sessions_expires_at ON email_sessions(expires_at);  -- For retention cleanup
CREATE INDEX idx_step_executions_session_id ON step_executions(session_id);
CREATE INDEX idx_step_executions_step_name ON step_executions(step_name);
CREATE INDEX idx_step_executions_status ON step_executions(status);  -- For failure analysis
CREATE INDEX idx_function_calls_function_name ON function_calls(function_name);
CREATE INDEX idx_function_calls_session_id ON function_calls(session_id);

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_email_sessions_updated_at BEFORE UPDATE ON email_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Data retention cleanup function
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete expired sessions (CASCADE will delete related records)
    DELETE FROM email_sessions
    WHERE expires_at < NOW()
    RETURNING session_id INTO deleted_count;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- Log cleanup for monitoring
    RAISE NOTICE 'Cleaned up % expired sessions', deleted_count;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Schedule daily cleanup at 2 AM (requires pg_cron extension or Supabase Edge Function)
-- Via Supabase Edge Function (recommended):
-- Create edge function that runs: SELECT cleanup_expired_sessions();
-- Schedule via Supabase Dashboard: Cron expression "0 2 * * *"
```

## Cost Analysis & Justification

### Supabase Pricing (Pro Tier Required)

**Base Costs:**
- Pro tier base: **$25/month**
- Storage: **$0.125/GB**
- Bandwidth: **$0.09/GB**
- Free tier (500MB, 2GB bandwidth): **Insufficient for production**

### Projected Monthly Costs by Volume

#### Low Volume (1,000 emails/month)
- Storage estimate: ~5GB (with 30-day retention)
  - Sessions: ~1GB (metadata only, no full email bodies)
  - Steps: ~2GB (structured output only, failures get full logs)
  - Function calls: ~1GB
  - Email responses: ~1GB (template names only)
- Storage cost: 5GB × $0.125 = **$0.63/month**
- Bandwidth (queries): ~2GB × $0.09 = **$0.18/month**
- **Total: ~$26/month**

#### Medium Volume (5,000 emails/month)
- Storage estimate: ~15GB (with 30-day retention)
- Storage cost: 15GB × $0.125 = **$1.88/month**
- Bandwidth: ~5GB × $0.09 = **$0.45/month**
- **Total: ~$27/month**

#### High Volume (10,000 emails/month)
- Storage estimate: ~25GB (with 30-day retention)
- Storage cost: 25GB × $0.125 = **$3.13/month**
- Bandwidth: ~10GB × $0.09 = **$0.90/month**
- **Total: ~$29/month**

**Note:** PII removal and selective prompt storage (failures only) reduces costs by **~70%** compared to original design.

### Alternatives Considered

#### Option 1: AWS CloudWatch Logs + S3
**Pros:**
- Lower cost: ~$10-15/month for same volume
- Native AWS integration
- Long-term archival via S3 Glacier

**Cons:**
- No structured query interface (must use CloudWatch Insights or Athena)
- More complex setup (CloudWatch + S3 + Athena)
- Query performance slower than PostgreSQL
- No real-time dashboard capabilities

**Decision:** Rejected - poor queryability for debugging

#### Option 2: Self-Hosted PostgreSQL
**Pros:**
- Zero external costs
- Full control over data

**Cons:**
- Operational overhead (backups, scaling, monitoring)
- Estimated maintenance: 2-4 hours/month (~$200-400 in labor)
- No automatic scaling
- Requires DevOps expertise

**Decision:** Rejected - operational cost exceeds $29/month Supabase cost

#### Option 3: Datadog APM + Logs
**Pros:**
- Best-in-class monitoring and alerting
- Beautiful dashboards out of the box
- Advanced analytics

**Cons:**
- Very expensive: ~$100-200/month for this volume
- Overkill for current needs
- Vendor lock-in

**Decision:** Rejected - too expensive for MVP stage

### Why Supabase? (Final Decision)

✅ **Best balance of cost, features, and ease of use:**
1. **Queryable** - PostgreSQL with full SQL support
2. **Real-time** - Instant dashboard updates via subscriptions
3. **Managed** - Zero DevOps overhead
4. **Scalable** - Automatic scaling up to 500GB+
5. **Affordable** - ~$26-29/month for projected volume
6. **Developer-friendly** - Python client, REST API, GraphQL

**ROI Justification:**
- Saves ~4 hours/month debugging time (no log file searching) = **$400/month** value
- Enables proactive monitoring (catch issues before customers report) = **Priceless**
- Cost: **$29/month** = **93% ROI**

### Cost Optimization Strategies Implemented

1. ✅ **PII Removal** - No full email bodies (saves ~50GB/month storage)
2. ✅ **Selective Prompt Storage** - Full LLM logs only for failures (saves ~20GB/month)
3. ✅ **30-Day Retention** - Auto-delete old logs (prevents unbounded growth)
4. ✅ **Indexed Queries** - Fast queries reduce bandwidth usage
5. ✅ **JSONB for Structured Data** - Efficient storage vs. TEXT columns

**Estimated savings from optimizations: ~$8-12/month vs. original design**

## Requirements

### Functional Requirements

#### FR1: Log Email Session Start
**When** an email is received and processing begins
**Then** create a record in `email_sessions` table with:
- `email_id` (Gmail message ID)
- `from_address`, `email_subject` (NO full email body for PII compliance)
- `email_body_hash` (SHA-256 for deduplication), `email_body_length` (for analytics)
- `received_at` timestamp
- `status: 'processing'`
- `agent_version`, `model_provider`, `model_name`
- `expires_at` (NOW() + retention_days for auto-cleanup)

#### FR2: Log Each Step Execution
**When** a step is executed
**Then** create a record in `step_executions` table with:
- `session_id` (foreign key)
- `step_number` (1, 2, 3...)
- `step_name` (e.g., '01-extract-serial')
- `input_context_summary` (JSONB of key fields only: serial_number, ticket_id, etc.)
- `llm_prompt_hash` (SHA-256 for deduplication)
- `llm_prompt` (full prompt ONLY if status='failed', NULL for success - storage optimization)
- `llm_response` (full response ONLY if status='failed', NULL for success)
- `llm_token_count` (for cost analysis)
- `parsed_output` (structured data extracted)
- `next_step` and `routing_reason`
- `duration_ms` (step execution time)
- `status: 'success'` or `'failed'`

#### FR3: Log All Function Calls
**When** a function is called (check_warranty, create_ticket, send_email, etc.)
**Then** create a record in `function_calls` table with:
- `execution_id` (foreign key to step)
- `session_id` (foreign key to email session)
- `function_name`
- `function_args` (JSONB)
- `function_response` (JSONB)
- `duration_ms`
- `status: 'success'` or `'failed'`
- `retry_count` (if retried)

#### FR4: Log Email Responses
**When** an email is sent (customer, admin, supervisor)
**Then** create a record in `email_responses` table with:
- `session_id` (foreign key)
- `recipient_type` ('customer', 'admin', 'supervisor')
- `recipient_email`
- `subject`
- `template_name` (e.g., 'device-not-found', 'valid-warranty')
- `template_variables` (JSONB: ticket_id, serial_number, etc. - NO full body for PII compliance)
- `body_length` (character count for analytics)
- `sent_at` timestamp
- `status: 'sent'` or `'failed'`

#### FR5: Update Session on Completion
**When** email processing completes (success or failure)
**Then** update `email_sessions` record with:
- `status: 'completed'`, `'failed'`, or `'halted'`
- `completed_at` timestamp
- `total_duration_ms`
- `total_steps` (count)
- `step_sequence` (array of step names)
- `outcome` ('ticket_created', 'ai_opt_out', 'escalated', etc.)
- `ticket_id` (if created)
- `serial_number` (extracted from step execution)
- `issue_category` (classified from outcome)
- `logs_finalized: true` (after all async log writes complete - prevents race conditions)
- `error_message` (if failed)

#### FR6: Query Interface - Recent Sessions
**Given** I want to see recent email processing activity
**When** I query `email_sessions` table
**Then** return sessions ordered by `received_at DESC` with:
- Email subject, sender, status, outcome
- Total steps, duration
- Ticket ID (if created)
- Error message (if failed)

#### FR7: Query Interface - Step Execution Drill-Down
**Given** I want to debug a specific email session
**When** I query `step_executions` for a `session_id`
**Then** return all steps with:
- Step name, input context, LLM response
- Next step routing decision
- Duration, status
- Ability to view full LLM prompt/response

#### FR8: Query Interface - Function Call Analytics
**Given** I want to analyze function call patterns
**When** I query `function_calls` grouped by `function_name`
**Then** return:
- Function name, total calls, success rate
- Average duration, retry count
- Most common failure reasons

#### FR9: Query Interface - Error Analysis
**Given** I want to identify common failure patterns
**When** I query failed sessions
**Then** return:
- Failed step name, error message
- Frequency of each failure type
- Example email inputs that trigger failures

#### FR10: Data Retention and Cleanup (MANDATORY)
**Given** logs must not grow unbounded and violate GDPR retention limits
**When** email sessions are created
**Then**:
- Set `expires_at` field based on config: `supabase_retention_days` (default: 30 days)
- Scheduled cleanup job runs daily at 2 AM via Supabase Edge Function
- Cleanup function `cleanup_expired_sessions()` deletes sessions where `expires_at < NOW()`
- CASCADE delete removes all related records (steps, function calls, email responses)
- Log cleanup count for monitoring: "Cleaned up N expired sessions"
- Config override: Set `supabase_retention_days: 90` for longer retention if legally required

**GDPR Compliance:**
- Default 30-day retention complies with GDPR "storage limitation" principle
- No PII stored (email bodies removed from schema)
- Right to erasure: Delete session by `email_id` removes all traces

## Acceptance Criteria

### AC1: Supabase Client Integration ✅
**Given** the agent needs to log to Supabase
**When** agent starts up
**Then**:
- [ ] Supabase client initialized from config (`supabase_url`, `supabase_key` from env vars)
- [ ] Connection tested on startup
- [ ] Database schema exists (tables created via migration)
- [ ] Logging disabled if `SUPABASE_URL` env var missing (graceful degradation)
- [ ] All database operations are async (non-blocking)
- [ ] Failed writes log warning but don't crash agent

**Files to Create:**
- [ ] `src/guarantee_email_agent/logging/supabase_logger.py` - Main logger class
- [ ] `migrations/001_create_telemetry_tables.sql` - Database schema
- [ ] `src/guarantee_email_agent/logging/models.py` - Pydantic models for log records

**Dependencies:**
```toml
[project.dependencies]
supabase = ">=2.0.0"
```

### AC2: Email Session Logging ✅
**Given** an email is being processed
**When** processing starts
**Then**:
- [ ] New record created in `email_sessions` with status='processing'
- [ ] `session_id` stored in processing context
- [ ] On completion: `status`, `outcome`, `total_steps`, `step_sequence`, `duration_ms` updated
- [ ] On failure: `error_message` captured
- [ ] All session metadata logged (agent version, model, timestamps)

**Implementation:**
```python
# In EmailProcessor.process_email()
session_id = await supabase_logger.log_email_session_start(
    email_id=email.message_id,
    from_address=email.from_address,
    email_subject=email.subject,
    email_body=email.body,
    received_at=email.received_at
)

# Store in context
context.session_id = session_id

# On completion
await supabase_logger.log_email_session_complete(
    session_id=session_id,
    status='completed',
    outcome='ticket_created',
    ticket_id=context.ticket_id,
    total_steps=len(step_history),
    step_sequence=[s.step_name for s in step_history],
    total_duration_ms=total_time
)
```

### AC3: Step Execution Logging ✅
**Given** a step is being executed
**When** step starts and completes
**Then**:
- [ ] New record created in `step_executions` before LLM call
- [ ] Input context (JSONB) captured
- [ ] Full LLM prompt logged
- [ ] Full LLM response logged
- [ ] Parsed output (serial number, next_step, etc.) captured as JSONB
- [ ] Step duration measured and logged
- [ ] On error: `error_message` captured

**Implementation:**
```python
# In StepOrchestrator.execute_step()
execution_id = await supabase_logger.log_step_start(
    session_id=context.session_id,
    step_number=step_number,
    step_name=step_name,
    input_context=context.to_dict()
)

# After LLM call
await supabase_logger.log_step_complete(
    execution_id=execution_id,
    llm_prompt=prompt,
    llm_response=response,
    parsed_output={
        'serial_number': parsed.serial_number,
        'next_step': parsed.next_step,
        'routing_reason': parsed.routing_reason
    },
    next_step=parsed.next_step,
    duration_ms=duration,
    status='success'
)
```

### AC4: Function Call Logging ✅
**Given** a function is called (check_warranty, create_ticket, send_email)
**When** function executes
**Then**:
- [ ] Record created in `function_calls` before execution
- [ ] Function name and args (JSONB) captured
- [ ] Function response (JSONB) captured
- [ ] Duration measured
- [ ] Retry count tracked (if retried via tenacity)
- [ ] On error: `error_message` captured

**Implementation:**
```python
# In FunctionDispatcher.call_function()
call_id = await supabase_logger.log_function_call_start(
    execution_id=context.current_execution_id,
    session_id=context.session_id,
    function_name=function_name,
    function_args=args
)

# After function execution
await supabase_logger.log_function_call_complete(
    call_id=call_id,
    function_response=response,
    duration_ms=duration,
    status='success',
    retry_count=retry_attempt
)
```

### AC5: Email Response Logging ✅
**Given** an email is being sent
**When** send_email function executes
**Then**:
- [ ] Record created in `email_responses`
- [ ] Recipient type identified ('customer', 'admin', 'supervisor')
- [ ] Full email subject and body logged
- [ ] Send status ('sent' or 'failed') recorded
- [ ] Timestamp captured

**Implementation:**
```python
# In send_email tool
await supabase_logger.log_email_response(
    session_id=context.session_id,
    recipient_type='customer',  # or 'admin', 'supervisor'
    recipient_email=to_address,
    subject=subject,
    body=body,
    status='sent'
)
```

### AC6: Query Helpers for Analytics ✅
**Given** I want to query logged data
**When** using query helper methods
**Then**:
- [ ] `get_recent_sessions(limit=50)` returns recent email sessions
- [ ] `get_session_details(session_id)` returns full session with steps and function calls
- [ ] `get_step_executions(session_id)` returns all steps for a session
- [ ] `get_function_call_stats(days=7)` returns function call analytics
- [ ] `get_failed_sessions(days=7)` returns recent failures with error messages
- [ ] `get_step_performance(step_name)` returns average duration and success rate

**Files to Create:**
- [ ] `src/guarantee_email_agent/logging/queries.py` - Helper query functions

**Example:**
```python
from guarantee_email_agent.logging.queries import get_recent_sessions

# Get last 50 email sessions
sessions = await get_recent_sessions(limit=50)
for session in sessions:
    print(f"{session.received_at} | {session.from_address} | {session.outcome} | {session.total_duration_ms}ms")
```

### AC7: Async Non-Blocking Logging ✅
**Given** logging to Supabase should not slow down email processing
**When** log writes occur
**Then**:
- [ ] All Supabase writes are async
- [ ] Logging errors are caught and logged to stderr (don't crash agent)
- [ ] Optional: Use background task queue for log writes (fire-and-forget)
- [ ] Email processing continues even if log writes fail

**Implementation:**
```python
# Non-blocking logging
try:
    await supabase_logger.log_step_start(...)
except Exception as e:
    logger.error(f"Supabase logging failed: {e}", exc_info=True)
    # Continue processing - don't crash
```

### AC8: Configuration and Environment Variables ✅
**Given** Supabase credentials must be secure
**When** configuring the agent
**Then**:
- [ ] `SUPABASE_URL` environment variable required
- [ ] `SUPABASE_KEY` environment variable required (anon key for writes)
- [ ] Config flag: `supabase_logging_enabled: true|false` (default: true if env vars set)
- [ ] Config flag: `supabase_retention_days: 30` (default: 30 days, auto-delete old logs)
- [ ] Config flag: `supabase_store_full_prompts: false` (default: false, only store for failures)
- [ ] Config flag: `supabase_logging_required: false` (default: false, if true agent crashes on connection failure)
- [ ] If env vars missing: logging disabled, warning logged, agent continues (unless logging_required=true)
- [ ] Validation on startup: test write to `email_sessions` table

**Files to Modify:**
- [ ] `config.yaml` - Add supabase config flags (logging_enabled, retention_days, store_full_prompts)
- [ ] `src/guarantee_email_agent/config/schema.py` - Add Supabase config fields
- [ ] `.env.example` - Document SUPABASE_URL and SUPABASE_KEY

**Example config.yaml:**
```yaml
# Supabase Observability
supabase_logging_enabled: true
supabase_retention_days: 30  # Auto-delete logs older than N days
supabase_store_full_prompts: false  # Only store full prompts for failures (saves storage)
supabase_logging_required: false  # If true, agent crashes if Supabase unavailable
```

## Implementation Plan

### Phase 1: Database Setup + Data Retention (1 day)
- [ ] Create Supabase project (or use existing)
- [ ] Run migration: `migrations/001_create_telemetry_tables.sql` (updated schema with PII removal)
- [ ] Verify tables exist: `email_sessions`, `step_executions`, `function_calls`, `email_responses`
- [ ] Create indexes for performance (including `expires_at` for cleanup)
- [ ] Implement `cleanup_expired_sessions()` function
- [ ] Create Supabase Edge Function for daily cleanup schedule
- [ ] Configure cron: "0 2 * * *" (daily at 2 AM)
- [ ] Test manual insert/query via Supabase dashboard
- [ ] Test cleanup function: Insert expired record, run cleanup, verify deletion

### Phase 2: Logger Implementation (0.5 days)
- [ ] Create `src/guarantee_email_agent/logging/supabase_logger.py`
- [ ] Implement `SupabaseLogger` class with async methods:
  - `log_email_session_start()`
  - `log_email_session_complete()`
  - `log_step_start()`
  - `log_step_complete()`
  - `log_function_call_start()`
  - `log_function_call_complete()`
  - `log_email_response()`
- [ ] Add connection testing: `test_connection()`
- [ ] Add error handling: catch all exceptions, log to stderr
- [ ] Unit tests for logger methods (mocked Supabase client)

### Phase 3: Integration with EmailProcessor (0.5 days)
- [ ] Modify `src/guarantee_email_agent/email/processor.py`
- [ ] Initialize `SupabaseLogger` on startup
- [ ] Call `log_email_session_start()` at beginning of `process_email()`
- [ ] Call `log_email_session_complete()` at end (success or failure)
- [ ] Pass `session_id` through processing context
- [ ] Test end-to-end: email → session logged → query Supabase

### Phase 4: Integration with StepOrchestrator (0.5 days)
- [ ] Modify `src/guarantee_email_agent/orchestrator/step_orchestrator.py`
- [ ] Call `log_step_start()` before each step execution
- [ ] Call `log_step_complete()` after each step
- [ ] Capture full LLM prompt and response
- [ ] Test: verify all steps logged for a sample email

### Phase 5: Integration with FunctionDispatcher (0.25 days)
- [ ] Modify `src/guarantee_email_agent/llm/function_dispatcher.py`
- [ ] Wrap all function calls with logging:
  - `log_function_call_start()` before execution
  - `log_function_call_complete()` after execution
- [ ] Track retry count from tenacity decorator
- [ ] Test: verify all function calls logged

### Phase 6: Query Helpers and Analytics (0.25 days)
- [ ] Create `src/guarantee_email_agent/logging/queries.py`
- [ ] Implement helper functions:
  - `get_recent_sessions()`
  - `get_session_details()`
  - `get_function_call_stats()`
  - `get_failed_sessions()`
- [ ] Add CLI command: `agent logs recent --limit 50`
- [ ] Add CLI command: `agent logs session <session_id>`
- [ ] Test: query logged data and verify results

### Phase 7: Load Testing and Documentation (1 day)
- [ ] Write integration test: process sample email → verify all logs written
- [ ] Test failure scenarios: verify errors logged correctly
- [ ] Test with `SUPABASE_URL` missing → agent continues without logging
- [ ] **NEW: Load testing (CRITICAL)**:
  - [ ] Simulate 100 concurrent email sessions
  - [ ] Verify all logs written without race conditions
  - [ ] Verify `logs_finalized` flag prevents incomplete reads
  - [ ] Measure async logging overhead (must be < 50ms per log)
  - [ ] Test Supabase connection pool under load
- [ ] **NEW: Data retention testing**:
  - [ ] Insert sessions with `expires_at` in past
  - [ ] Run cleanup function
  - [ ] Verify CASCADE deletion (all related records removed)
- [ ] **NEW: PII compliance verification**:
  - [ ] Query `email_sessions` - verify no full email bodies
  - [ ] Query `email_responses` - verify no full response bodies
  - [ ] Query `step_executions` - verify full prompts only for failures
- [ ] Update README with Supabase setup instructions
- [ ] Document query helper usage
- [ ] Create example dashboard queries (SQL snippets)

## Testing Strategy

### Integration Tests

**Test 1: Complete Email Logging**
```python
async def test_email_logged_to_supabase():
    # Given: Sample email
    email = create_sample_email(subject="Test SN12345", body="Not working")

    # When: Process email
    await email_processor.process_email(email)

    # Then: Verify logged to Supabase
    session = await supabase_logger.get_session_by_email_id(email.message_id)
    assert session.status == 'completed'
    assert session.total_steps > 0
    assert len(session.step_sequence) > 0

    # Verify steps logged
    steps = await supabase_logger.get_step_executions(session.session_id)
    assert steps[0].step_name == '01-extract-serial'
    assert steps[0].llm_response is not None

    # Verify function calls logged
    calls = await supabase_logger.get_function_calls(session.session_id)
    assert any(c.function_name == 'check_warranty' for c in calls)
```

**Test 2: Failed Email Logging**
```python
async def test_failed_email_logged():
    # Given: Email that will fail (e.g., warranty API down)
    email = create_sample_email()
    mock_warranty_api_failure()

    # When: Process email (fails)
    with pytest.raises(ProcessingError):
        await email_processor.process_email(email)

    # Then: Verify failure logged
    session = await supabase_logger.get_session_by_email_id(email.message_id)
    assert session.status == 'failed'
    assert session.error_message is not None
    assert 'warranty_api' in session.error_message.lower()
```

**Test 3: Function Call Logging**
```python
async def test_function_calls_logged():
    # Given: Email that triggers create_ticket
    email = create_valid_warranty_email()

    # When: Process email
    await email_processor.process_email(email)

    # Then: Verify create_ticket logged
    session = await supabase_logger.get_session_by_email_id(email.message_id)
    calls = await supabase_logger.get_function_calls(session.session_id)

    create_ticket_call = next(c for c in calls if c.function_name == 'create_ticket')
    assert create_ticket_call.function_args['serial_number'] is not None
    assert create_ticket_call.function_response['ticket_id'] is not None
    assert create_ticket_call.status == 'success'
```

### Query Tests

**Test 4: Recent Sessions Query**
```python
async def test_get_recent_sessions():
    # Given: Process 10 emails
    for i in range(10):
        email = create_sample_email(subject=f"Test {i}")
        await email_processor.process_email(email)

    # When: Query recent sessions
    sessions = await get_recent_sessions(limit=5)

    # Then: Returns 5 most recent
    assert len(sessions) == 5
    assert sessions[0].received_at > sessions[1].received_at
```

**Test 5: Function Call Analytics**
```python
async def test_function_call_stats():
    # Given: Process multiple emails (mix of success/failure)
    # ...

    # When: Query function stats
    stats = await get_function_call_stats(days=7)

    # Then: Returns aggregated stats
    check_warranty_stats = next(s for s in stats if s.function_name == 'check_warranty')
    assert check_warranty_stats.total_calls > 0
    assert 0 <= check_warranty_stats.success_rate <= 100
    assert check_warranty_stats.avg_duration_ms > 0
```

### Load Tests (NEW)

**Test 6: Concurrent Email Processing**
```python
async def test_concurrent_email_logging():
    # Given: 100 concurrent emails
    emails = [create_sample_email(subject=f"Test {i}") for i in range(100)]

    # When: Process all concurrently
    await asyncio.gather(*[email_processor.process_email(e) for e in emails])

    # Then: All sessions logged without race conditions
    sessions = await get_recent_sessions(limit=100)
    assert len(sessions) == 100

    # Verify logs_finalized flag set for all
    assert all(s.logs_finalized for s in sessions)

    # Verify no missing steps (integrity check)
    for session in sessions:
        steps = await get_step_executions(session.session_id)
        assert len(steps) == session.total_steps
```

**Test 7: Async Logging Performance**
```python
async def test_logging_performance_overhead():
    # Given: Email processing with logging enabled
    email = create_sample_email()

    # When: Process email and measure time
    start = time.time()
    await email_processor.process_email(email)
    duration_ms = (time.time() - start) * 1000

    # Then: Verify logging overhead < 50ms
    session = await supabase_logger.get_session_by_email_id(email.message_id)

    # Measure individual log write times
    step_logs = await get_step_executions(session.session_id)
    for step in step_logs:
        log_duration = step.completed_at - step.started_at
        assert log_duration.total_seconds() * 1000 < 50  # < 50ms per log
```

### Data Retention Tests (NEW)

**Test 8: Automatic Cleanup**
```python
async def test_expired_sessions_cleaned_up():
    # Given: Create sessions with past expiry dates
    old_session = await supabase_logger.log_email_session_start(
        email_id="old@example.com",
        from_address="customer@example.com",
        email_subject="Old email",
        email_body_hash="abc123",
        expires_at=datetime.now() - timedelta(days=1)  # Expired
    )

    # When: Run cleanup function
    deleted_count = await supabase.rpc('cleanup_expired_sessions').execute()

    # Then: Old session deleted
    session = await supabase_logger.get_session_by_email_id("old@example.com")
    assert session is None

    # Verify CASCADE deletion (related records removed)
    steps = await get_step_executions(old_session.session_id)
    assert len(steps) == 0
```

**Test 9: Retention Period Respected**
```python
async def test_retention_period_configurable():
    # Given: Config with 7-day retention
    config.supabase_retention_days = 7

    # When: Create new session
    session = await supabase_logger.log_email_session_start(...)

    # Then: expires_at set to NOW() + 7 days
    assert session.expires_at == session.created_at + timedelta(days=7)
```

### PII Compliance Tests (NEW)

**Test 10: No Email Bodies Stored**
```python
async def test_no_pii_stored_in_database():
    # Given: Email with sensitive PII
    email = create_sample_email(
        body="My phone is 555-1234 and I live at 123 Main St"
    )

    # When: Process email
    await email_processor.process_email(email)

    # Then: Query database and verify NO full body stored
    session = await supabase_logger.get_session_by_email_id(email.message_id)
    assert hasattr(session, 'email_body_hash')  # Hash stored
    assert hasattr(session, 'email_body_length')  # Length stored
    assert not hasattr(session, 'email_body')  # Full body NOT stored

    # Verify email responses also no full body
    responses = await get_email_responses(session.session_id)
    for response in responses:
        assert hasattr(response, 'template_name')
        assert hasattr(response, 'template_variables')
        assert not hasattr(response, 'body')  # Full body NOT stored
```

**Test 11: LLM Prompts Only for Failures**
```python
async def test_llm_prompts_only_stored_for_failures():
    # Given: Successful email processing
    success_email = create_valid_warranty_email()
    await email_processor.process_email(success_email)

    # Then: Verify NO full prompts stored for success steps
    session = await supabase_logger.get_session_by_email_id(success_email.message_id)
    steps = await get_step_executions(session.session_id)

    for step in steps:
        if step.status == 'success':
            assert step.llm_prompt is None  # No full prompt
            assert step.llm_response is None  # No full response
            assert step.llm_prompt_hash is not None  # Hash exists
            assert step.parsed_output is not None  # Structured output exists

    # Given: Failed email processing
    fail_email = create_sample_email()
    mock_llm_failure()  # Simulate LLM error

    with pytest.raises(ProcessingError):
        await email_processor.process_email(fail_email)

    # Then: Verify FULL prompts stored for failed steps
    fail_session = await supabase_logger.get_session_by_email_id(fail_email.message_id)
    fail_steps = await get_step_executions(fail_session.session_id)

    failed_step = next(s for s in fail_steps if s.status == 'failed')
    assert failed_step.llm_prompt is not None  # Full prompt stored for debugging
    assert failed_step.llm_response is not None  # Full response stored
```

**Test 12: Supabase Unavailable - Graceful Degradation**
```python
async def test_agent_continues_when_supabase_down():
    # Given: Supabase connection fails
    mock_supabase_connection_error()

    # When: Process email
    email = create_valid_warranty_email()
    result = await email_processor.process_email(email)

    # Then: Email processing succeeds (logging failure doesn't crash agent)
    assert result.status == 'completed'
    assert result.ticket_id is not None

    # Verify warning logged to stderr
    assert "Supabase logging failed" in captured_logs
```

## Example Queries for Dashboard

### Query 1: Recent Email Activity (Last 24 Hours)
```sql
SELECT
    received_at,
    from_address,
    email_subject,
    status,
    outcome,
    total_steps,
    total_duration_ms,
    ticket_id,
    error_message
FROM email_sessions
WHERE received_at > NOW() - INTERVAL '24 hours'
ORDER BY received_at DESC
LIMIT 100;
```

### Query 2: Step Performance Analysis
```sql
SELECT
    step_name,
    COUNT(*) as total_executions,
    AVG(duration_ms) as avg_duration_ms,
    MAX(duration_ms) as max_duration_ms,
    COUNT(*) FILTER (WHERE status = 'success') * 100.0 / COUNT(*) as success_rate
FROM step_executions
WHERE started_at > NOW() - INTERVAL '7 days'
GROUP BY step_name
ORDER BY total_executions DESC;
```

### Query 3: Function Call Success Rates
```sql
SELECT
    function_name,
    COUNT(*) as total_calls,
    COUNT(*) FILTER (WHERE status = 'success') * 100.0 / COUNT(*) as success_rate,
    AVG(duration_ms) as avg_duration_ms,
    SUM(retry_count) as total_retries
FROM function_calls
WHERE called_at > NOW() - INTERVAL '7 days'
GROUP BY function_name
ORDER BY total_calls DESC;
```

### Query 4: Most Common Failures
```sql
SELECT
    error_message,
    COUNT(*) as occurrences,
    MAX(received_at) as last_occurrence
FROM email_sessions
WHERE status = 'failed'
    AND received_at > NOW() - INTERVAL '7 days'
GROUP BY error_message
ORDER BY occurrences DESC
LIMIT 10;
```

### Query 5: Email-to-Ticket Conversion Rate
```sql
SELECT
    outcome,
    COUNT(*) as total,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM email_sessions
WHERE completed_at > NOW() - INTERVAL '7 days'
    AND status = 'completed'
GROUP BY outcome
ORDER BY total DESC;
```

### Query 6: Average Processing Time by Outcome
```sql
SELECT
    outcome,
    COUNT(*) as total_emails,
    AVG(total_duration_ms) as avg_duration_ms,
    AVG(total_steps) as avg_steps
FROM email_sessions
WHERE status = 'completed'
    AND completed_at > NOW() - INTERVAL '7 days'
GROUP BY outcome
ORDER BY total_emails DESC;
```

## Eval Scenarios

### Eval 1: Verify Session Logged
```yaml
scenario_id: supabase_session_logged_001
description: "Email session logged to Supabase with all metadata"
category: supabase-logging

input:
  email:
    subject: "Gwarancja SN12345"
    body: "Urządzenie nie działa"
    from: "customer@example.com"

  mock_function_responses:
    check_warranty:
      status: "valid"
    create_ticket:
      ticket_id: "TKT-8001"

expected_output:
  # Standard eval checks
  ticket_created: true

  # NEW: Supabase logging checks
  supabase_session_logged: true
  supabase_session_fields:
    status: "completed"
    outcome: "ticket_created"
    ticket_id: "TKT-8001"
    total_steps: 4
    step_sequence: ["01-extract-serial", "02-check-warranty", "03a-valid-warranty", "05-send-confirmation"]
    from_address: "customer@example.com"
    email_subject: "Gwarancja SN12345"
```

### Eval 2: Verify All Steps Logged
```yaml
scenario_id: supabase_steps_logged_001
description: "All step executions logged with full LLM prompts/responses"
category: supabase-logging

expected_output:
  supabase_steps_logged: true
  supabase_step_count: 4
  supabase_steps:
    - step_name: "01-extract-serial"
      llm_prompt_exists: true
      llm_response_exists: true
      parsed_output_contains: ["serial_number", "next_step"]
    - step_name: "02-check-warranty"
      function_calls: ["check_warranty"]
    - step_name: "03a-valid-warranty"
      function_calls: ["create_ticket"]
    - step_name: "05-send-confirmation"
      function_calls: ["send_email"]
```

### Eval 3: Verify Function Calls Logged
```yaml
scenario_id: supabase_function_calls_logged_001
description: "All function calls logged with args and responses"
category: supabase-logging

expected_output:
  supabase_function_calls_logged: true
  supabase_function_calls:
    - function_name: "check_warranty"
      args_contains: ["serial_number"]
      response_contains: ["status", "expiration_date"]
      status: "success"
    - function_name: "create_ticket"
      args_contains: ["serial_number", "issue_description"]
      response_contains: ["ticket_id"]
      status: "success"
    - function_name: "send_email"
      args_contains: ["to", "subject", "body"]
      status: "success"
```

### Eval 4: Verify Failed Session Logged
```yaml
scenario_id: supabase_failed_session_001
description: "Failed email processing logged with error details"
category: supabase-logging

input:
  email:
    subject: "Test failure"
    body: "Simulate API failure"

  mock_function_responses:
    check_warranty:
      error: "API timeout"

expected_output:
  processing_failed: true

  supabase_session_logged: true
  supabase_session_fields:
    status: "failed"
    error_message_contains: "API timeout"
    completed_at_exists: true
```

## CLI Commands for Log Viewing

### Command 1: View Recent Sessions
```bash
uv run python -m guarantee_email_agent logs recent --limit 50
```

Output:
```
Recent Email Sessions (Last 50)
================================================================================
2026-02-03 10:23:45 | customer@example.com | ticket_created | TKT-8001 | 4 steps | 3.2s
2026-02-03 10:22:10 | vip@example.com | ticket_created | VIP-5001 | 5 steps | 4.1s (VIP alert sent)
2026-02-03 10:20:33 | angry@example.com | escalated | - | 2 steps | 1.8s (Supervisor notified)
2026-02-03 10:19:05 | customer2@example.com | ai_opt_out | -8829 | 3 steps | 2.1s (AI disabled)
...
```

### Command 2: View Session Details
```bash
uv run python -m guarantee_email_agent logs session <session_id>
```

Output:
```
Email Session: a1b2c3d4-e5f6-7890-abcd-ef1234567890
================================================================================
From: customer@example.com
Subject: Gwarancja SN12345
Received: 2026-02-03 10:23:45
Status: completed
Outcome: ticket_created
Ticket: TKT-8001

Step Execution History (4 steps, 3.2s total):
  1. 01-extract-serial (0.8s) → 02-check-warranty
     Serial: SN12345
  2. 02-check-warranty (1.2s) → 03a-valid-warranty
     Function: check_warranty(serial_number="SN12345")
     Response: {status: "valid", expires: "2026-12-31"}
  3. 03a-valid-warranty (0.9s) → 05-send-confirmation
     Function: create_ticket(serial="SN12345", email="customer@example.com")
     Response: {ticket_id: "TKT-8001"}
  4. 05-send-confirmation (0.3s) → DONE
     Function: send_email(to="customer@example.com", ...)
     Response: {sent: true}
```

### Command 3: View Function Statistics
```bash
uv run python -m guarantee_email_agent logs stats --days 7
```

Output:
```
Function Call Statistics (Last 7 Days)
================================================================================
Function          | Calls | Success Rate | Avg Duration | Total Retries
------------------|-------|--------------|--------------|---------------
check_warranty    | 1,245 | 98.4%        | 1,203ms      | 28
create_ticket     | 1,089 | 99.7%        | 892ms        | 4
send_email        | 2,456 | 99.9%        | 234ms        | 3
check_ticket_feat | 156   | 100.0%       | 456ms        | 0
append_ticket_his | 2,178 | 99.5%        | 312ms        | 12
```

## Definition of Done

### Database & Infrastructure
- [ ] Supabase database schema created (4 tables + indexes + PII-compliant fields)
- [ ] Data retention cleanup function implemented (`cleanup_expired_sessions()`)
- [ ] Supabase Edge Function created for daily cleanup (cron: "0 2 * * *")
- [ ] All tables use PII-safe schema (no full email bodies, template names only)
- [ ] `logs_finalized` flag implemented to prevent race conditions
- [ ] `expires_at` field auto-set based on `supabase_retention_days` config

### Code Implementation
- [ ] `SupabaseLogger` class implemented with all logging methods
- [ ] Email session logging integrated into `EmailProcessor`
- [ ] Step execution logging integrated into `StepOrchestrator`
- [ ] Function call logging integrated into `FunctionDispatcher`
- [ ] Email response logging integrated into send_email tool
- [ ] Selective prompt storage: Full prompts ONLY for failed steps (config: `supabase_store_full_prompts`)
- [ ] SHA-256 hashing for email bodies and LLM prompts (deduplication + PII protection)
- [ ] Query helper functions implemented (`queries.py`)
- [ ] CLI commands for log viewing (`agent logs recent`, `agent logs session`, `agent logs stats`)

### Configuration
- [ ] Configuration and environment variables documented
- [ ] Config flags added: `supabase_logging_enabled`, `supabase_retention_days`, `supabase_store_full_prompts`, `supabase_logging_required`
- [ ] `.env.example` updated with `SUPABASE_URL` and `SUPABASE_KEY`
- [ ] Startup validation: Test Supabase connection, fail gracefully if unavailable

### Performance & Reliability
- [ ] All logging is async and non-blocking
- [ ] Failed log writes don't crash agent (graceful degradation)
- [ ] Async logging overhead verified < 50ms per log (performance test)
- [ ] Load test: 100 concurrent emails processed without race conditions
- [ ] Connection pool tested under load (no connection exhaustion)

### Testing
- [ ] Integration tests verify all logging works end-to-end (Test 1-5)
- [ ] Load tests verify concurrent processing (Test 6-7)
- [ ] Data retention tests verify auto-cleanup (Test 8-9)
- [ ] PII compliance tests verify no sensitive data stored (Test 10-11)
- [ ] Graceful degradation test when Supabase unavailable (Test 12)
- [ ] 4 eval scenarios passing (session logged, steps logged, function calls logged, failed session)

### Documentation & Compliance
- [ ] README updated with Supabase setup instructions
- [ ] Cost analysis documented ($26-29/month projected)
- [ ] Alternatives analysis documented (CloudWatch, self-hosted PostgreSQL, Datadog)
- [ ] Example dashboard queries documented (6 SQL snippets)
- [ ] GDPR compliance verified: No PII stored, 30-day retention, right to erasure supported
- [ ] PII removal strategy documented in schema comments

## Success Metrics

- ✅ 100% of email sessions logged to Supabase (metadata only, PII-compliant)
- ✅ 100% of step executions logged (structured output for success, full prompts for failures only)
- ✅ 100% of function calls logged with args and responses
- ✅ Average log write time < 50ms (non-blocking, verified via load test)
- ✅ Query response time < 500ms for recent sessions
- ✅ Zero agent crashes due to logging failures (graceful degradation)
- ✅ Dashboard queries run successfully
- ✅ Data retention: Auto-delete logs older than 30 days (configurable)
- ✅ Storage cost: $26-29/month for 5,000-10,000 emails/month (70% savings vs. original design)
- ✅ GDPR compliant: No PII stored, right to erasure supported
- ✅ Load test: 100 concurrent emails without race conditions

## Dependencies

### Python Packages
```toml
[project.dependencies]
supabase = ">=2.0.0"  # Official Supabase Python client
```

### Environment Variables
```bash
SUPABASE_URL="https://xxxxx.supabase.co"
SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # Anon public key
```

### Supabase Setup
1. Create Supabase project at https://supabase.com
2. Run migration: `migrations/001_create_telemetry_tables.sql`
3. Get URL and anon key from project settings
4. Set environment variables

## Future Enhancements (Post-Story)

- **Story 5.4**: Build Supabase + Retool dashboard for real-time monitoring (visual dashboards)
- **Story 5.5**: Add alerting (e.g., Slack notification when error rate > 5%)
- **Story 5.6**: Export logs to S3 for long-term archival (cold storage for compliance)
- **Story 5.7**: Advanced analytics (ML-based anomaly detection on step durations)

**Note:** The following originally planned enhancements are now IN SCOPE for Story 5.3:
- ✅ Data retention policy (30-day auto-delete) - NOW INCLUDED
- ✅ PII compliance (no full email bodies stored) - NOW INCLUDED
- ✅ Selective prompt storage (failures only) - NOW INCLUDED

---

**Story Status:** 📝 READY FOR DEV (REVISED - All Critical Gaps Addressed)
**Priority:** HIGH
**Dependencies:** Stories 5.1 and 5.2 completed
**Estimated Effort:** 3 days (UPDATED from 2 days)
**Complexity:** Medium-High (database setup + async logging + PII compliance + data retention)

## Revision Summary (Post-Validation)

This story has been significantly revised to address critical gaps identified during validation:

### Major Changes:
1. **PII Compliance (MANDATORY)**: Full email bodies and response bodies removed from schema
2. **Data Retention (IN SCOPE)**: 30-day auto-cleanup now mandatory, not future work
3. **Cost Analysis (ADDED)**: Projected $26-29/month with 70% savings from optimizations
4. **Load Testing (ADDED)**: 100 concurrent emails, race condition prevention
5. **Selective Storage (ADDED)**: Full LLM prompts only for failures (storage optimization)
6. **Effort Estimate (INCREASED)**: 2 days → 3 days (realistic for expanded scope)

### GDPR Compliance Features:
- No PII stored (email body hash only, not content)
- 30-day default retention (configurable)
- Right to erasure (delete by email_id cascades all records)
- Template-based email logging (variables only, not full bodies)

### Cost Optimizations:
- 70% storage reduction vs. original design
- Selective prompt storage (failures only)
- 30-day retention prevents unbounded growth
- Estimated $26-29/month for 5,000-10,000 emails/month
