import pytest
from guarantee_email_agent.config.mcp_tester import (
    validate_mcp_connection_string,
    validate_mcp_connections
)
from guarantee_email_agent.config.schema import (
    AgentConfig,
    InstructionsConfig,
    MCPConfig,
    MCPConnectionConfig,
    EvalConfig,
    LoggingConfig,
    SecretsConfig
)
from guarantee_email_agent.utils.errors import MCPConnectionError


def test_validate_valid_connection_string():
    """Test validating a valid MCP connection string"""
    # Should not raise
    validate_mcp_connection_string("mcp://gmail", "gmail")
    validate_mcp_connection_string("mcp://warranty-api", "warranty")
    validate_mcp_connection_string("mcp://ticketing_system", "ticketing")


def test_validate_invalid_connection_string_format():
    """Test validating invalid connection string format"""
    with pytest.raises(MCPConnectionError) as exc_info:
        validate_mcp_connection_string("http://gmail", "gmail")

    assert exc_info.value.code == "mcp_invalid_connection_string"
    assert "mcp://" in exc_info.value.details["expected_format"]


def test_validate_empty_connection_string():
    """Test validating empty connection string"""
    with pytest.raises(MCPConnectionError):
        validate_mcp_connection_string("", "gmail")


def test_validate_connection_string_missing_protocol():
    """Test validating connection string without mcp:// protocol"""
    with pytest.raises(MCPConnectionError) as exc_info:
        validate_mcp_connection_string("gmail", "gmail")

    assert exc_info.value.code == "mcp_invalid_connection_string"


def test_validate_connection_string_wrong_protocol():
    """Test validating connection string with wrong protocol"""
    with pytest.raises(MCPConnectionError) as exc_info:
        validate_mcp_connection_string("https://gmail", "gmail")

    assert exc_info.value.code == "mcp_invalid_connection_string"


def test_validate_mcp_connections_with_valid_config():
    """Test validating all MCP connections with valid configuration"""
    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main="instructions/main.md",
            scenarios=[]
        ),
        eval=EvalConfig(test_suite_path="evals"),
        logging=LoggingConfig(level="INFO", json_format=False),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    # Should not raise
    validate_mcp_connections(config)


def test_validate_mcp_connections_with_invalid_gmail():
    """Test validating MCP connections with invalid Gmail connection string"""
    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="http://gmail"),  # Invalid
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main="instructions/main.md",
            scenarios=[]
        ),
        eval=EvalConfig(test_suite_path="evals"),
        logging=LoggingConfig(level="INFO", json_format=False),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    with pytest.raises(MCPConnectionError) as exc_info:
        validate_mcp_connections(config)

    assert exc_info.value.code == "mcp_invalid_connection_string"
    assert "gmail" in exc_info.value.details["service"]


def test_validate_mcp_connections_with_invalid_warranty_api():
    """Test validating MCP connections with invalid warranty API connection string"""
    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="invalid"),  # Invalid
            ticketing_system=MCPConnectionConfig(connection_string="mcp://ticketing")
        ),
        instructions=InstructionsConfig(
            main="instructions/main.md",
            scenarios=[]
        ),
        eval=EvalConfig(test_suite_path="evals"),
        logging=LoggingConfig(level="INFO", json_format=False),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    with pytest.raises(MCPConnectionError) as exc_info:
        validate_mcp_connections(config)

    assert exc_info.value.code == "mcp_invalid_connection_string"
    assert "warranty_api" in exc_info.value.details["service"]


def test_validate_mcp_connections_with_invalid_ticketing():
    """Test validating MCP connections with invalid ticketing connection string"""
    config = AgentConfig(
        mcp=MCPConfig(
            gmail=MCPConnectionConfig(connection_string="mcp://gmail"),
            warranty_api=MCPConnectionConfig(connection_string="mcp://warranty-api"),
            ticketing_system=MCPConnectionConfig(connection_string="ftp://ticketing")  # Invalid
        ),
        instructions=InstructionsConfig(
            main="instructions/main.md",
            scenarios=[]
        ),
        eval=EvalConfig(test_suite_path="evals"),
        logging=LoggingConfig(level="INFO", json_format=False),
        secrets=SecretsConfig(
            anthropic_api_key="test-key",
            gmail_api_key="test-gmail",
            warranty_api_key="test-warranty",
            ticketing_api_key="test-ticketing"
        )
    )

    with pytest.raises(MCPConnectionError) as exc_info:
        validate_mcp_connections(config)

    assert exc_info.value.code == "mcp_invalid_connection_string"
    assert "ticketing_system" in exc_info.value.details["service"]
