-- Supabase Telemetry Schema for Warranty Email Agent
-- Story 5.3: Complete Agent Activity Logging with PII Compliance
-- Created: 2026-02-03
-- Purpose: Track email sessions, step executions, function calls, and email responses

-- =============================================================================
-- Main email processing sessions
-- PRIVACY NOTE: Full email bodies NOT stored to comply with GDPR
-- Only metadata and extracted fields stored for analytics
-- =============================================================================
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

-- =============================================================================
-- Individual step executions
-- PRIVACY NOTE: LLM prompts/responses stored only for FAILED steps to reduce storage
-- Success cases store only structured output for performance analytics
-- =============================================================================
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

-- =============================================================================
-- Function calls made during steps
-- =============================================================================
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

-- =============================================================================
-- Email responses sent by agent
-- PRIVACY NOTE: Full email bodies NOT stored for GDPR compliance
-- Only template name and key variables stored for audit trail
-- =============================================================================
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

-- =============================================================================
-- Indexes for fast queries
-- =============================================================================
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

-- =============================================================================
-- Auto-update timestamp trigger
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_email_sessions_updated_at BEFORE UPDATE ON email_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Data retention cleanup function
-- =============================================================================
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete expired sessions (CASCADE will delete related records)
    DELETE FROM email_sessions
    WHERE expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- Log cleanup for monitoring
    RAISE NOTICE 'Cleaned up % expired sessions', deleted_count;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Comments for documentation
-- =============================================================================
COMMENT ON TABLE email_sessions IS 'Main email processing sessions with PII-safe metadata only';
COMMENT ON COLUMN email_sessions.email_body_hash IS 'SHA-256 hash for deduplication - NOT for recovery (PII compliance)';
COMMENT ON COLUMN email_sessions.expires_at IS 'Auto-cleanup timestamp for GDPR compliance (default 30 days)';
COMMENT ON COLUMN email_sessions.logs_finalized IS 'Prevents race conditions - set TRUE after all async log writes complete';

COMMENT ON TABLE step_executions IS 'Step-by-step execution logs with selective prompt storage (failures only)';
COMMENT ON COLUMN step_executions.llm_prompt IS 'Full LLM prompt stored ONLY for failed steps (NULL for success)';
COMMENT ON COLUMN step_executions.llm_response IS 'Full LLM response stored ONLY for failed steps (NULL for success)';

COMMENT ON TABLE function_calls IS 'Function call logs with args/responses for debugging and analytics';

COMMENT ON TABLE email_responses IS 'Email responses sent by agent (template-based, no full bodies for PII compliance)';
COMMENT ON COLUMN email_responses.template_variables IS 'JSONB of template variables (ticket_id, serial_number) - no full email body';

COMMENT ON FUNCTION cleanup_expired_sessions IS 'Daily cleanup job for GDPR compliance - deletes sessions older than expires_at';
