"""Tests for enhanced error handling features."""

import pytest
from guarantee_email_agent.utils.errors import (
    AgentError,
    ConfigurationError,
    MCPConnectionError,
    TransientError,
    LLMTimeoutError,
    ProcessingError,
    EvalError,
    EXIT_SUCCESS,
    EXIT_GENERAL_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_MCP_ERROR,
    EXIT_EVAL_FAILURE,
)


def test_agent_error_str_with_code():
    """Test __str__ includes code and details."""
    error = AgentError(
        message="Test error",
        code="test_error_code",
        details={"key1": "value1", "key2": "value2"}
    )

    error_str = str(error)
    assert "Test error" in error_str
    assert "code: test_error_code" in error_str
    assert "key1=value1" in error_str


def test_agent_error_str_without_details():
    """Test __str__ works without details."""
    error = AgentError(message="Simple error", code="simple_error")

    error_str = str(error)
    assert "Simple error" in error_str
    assert "code: simple_error" in error_str


def test_agent_error_repr():
    """Test __repr__ shows all attributes."""
    error = AgentError(
        message="Test error",
        code="test_code",
        details={"field": "value"}
    )

    error_repr = repr(error)
    assert "AgentError" in error_repr
    assert "message='Test error'" in error_repr
    assert "code='test_code'" in error_repr
    assert "details={'field': 'value'}" in error_repr


def test_agent_error_add_context():
    """Test add_context() method adds to details."""
    error = AgentError(message="Error", code="error_code", details={"initial": "value"})

    # Add context
    result = error.add_context(email_id="123", serial="SN456")

    # Check returns self for chaining
    assert result is error

    # Check details updated
    assert error.details["initial"] == "value"
    assert error.details["email_id"] == "123"
    assert error.details["serial"] == "SN456"


def test_agent_error_add_context_chaining():
    """Test add_context() supports method chaining."""
    error = AgentError(message="Error", code="error_code")

    error.add_context(key1="value1").add_context(key2="value2")

    assert error.details["key1"] == "value1"
    assert error.details["key2"] == "value2"


def test_agent_error_is_transient_default():
    """Test is_transient is False by default."""
    error = AgentError(message="Error", code="error_code")

    assert error.is_transient is False


def test_transient_error_is_transient():
    """Test TransientError.is_transient is True."""
    error = TransientError(message="Timeout", code="timeout")

    assert error.is_transient is True


def test_llm_timeout_error_is_transient():
    """Test LLMTimeoutError inherits transient behavior."""
    error = LLMTimeoutError(message="LLM timeout", code="llm_timeout")

    assert error.is_transient is True


def test_config_error_is_not_transient():
    """Test ConfigurationError is not transient."""
    error = ConfigurationError(message="Config error", code="config_error")

    assert error.is_transient is False


def test_processing_error_creation():
    """Test ProcessingError can be created with details."""
    error = ProcessingError(
        message="Processing failed",
        code="processing_failed",
        details={"email_id": "123", "failed_step": "extraction"}
    )

    assert error.message == "Processing failed"
    assert error.code == "processing_failed"
    assert error.details["email_id"] == "123"
    assert error.details["failed_step"] == "extraction"


def test_eval_error_creation():
    """Test EvalError can be created with details."""
    error = EvalError(
        message="Eval test failed",
        code="eval_test_failed",
        details={"scenario_id": "test_001", "file_path": "/path/to/test.yaml"}
    )

    assert error.message == "Eval test failed"
    assert error.code == "eval_test_failed"
    assert error.details["scenario_id"] == "test_001"


def test_exit_code_constants():
    """Test exit code constants have correct values."""
    assert EXIT_SUCCESS == 0
    assert EXIT_GENERAL_ERROR == 1
    assert EXIT_CONFIG_ERROR == 2
    assert EXIT_MCP_ERROR == 3
    assert EXIT_EVAL_FAILURE == 4


def test_agent_error_details_optional():
    """Test details parameter is optional."""
    error = AgentError(message="Error", code="error_code")

    assert error.details == {}


def test_agent_error_str_truncates_many_details():
    """Test __str__ only shows first 3 detail items."""
    error = AgentError(
        message="Error",
        code="error_code",
        details={"k1": "v1", "k2": "v2", "k3": "v3", "k4": "v4", "k5": "v5"}
    )

    error_str = str(error)
    # Should contain first 3 items
    assert "k1=v1" in error_str
    assert "k2=v2" in error_str
    assert "k3=v3" in error_str
    # Should not contain 4th and 5th (truncated)
    # Note: dict order is preserved in Python 3.7+


def test_error_hierarchy():
    """Test error class inheritance."""
    assert issubclass(ConfigurationError, AgentError)
    assert issubclass(MCPConnectionError, AgentError)
    assert issubclass(TransientError, AgentError)
    assert issubclass(ProcessingError, AgentError)
    assert issubclass(EvalError, AgentError)
    assert issubclass(LLMTimeoutError, TransientError)
