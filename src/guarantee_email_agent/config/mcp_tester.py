"""MCP connection testing and validation (stub for Epic 2)."""

import re
from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.utils.errors import MCPConnectionError


def validate_mcp_connection_string(connection_string: str, service_name: str) -> None:
    """Validate MCP connection string format.

    Args:
        connection_string: MCP connection string (e.g., "mcp://gmail")
        service_name: Service name for error messages

    Raises:
        MCPConnectionError: If connection string format is invalid
    """
    # Validate format: mcp://<service-name>
    # Service name can contain lowercase letters, numbers, hyphens, and underscores
    pattern = r'^mcp://[a-z0-9\-_]+$'
    if not re.match(pattern, connection_string, re.IGNORECASE):
        raise MCPConnectionError(
            message=f"Invalid MCP connection string for {service_name}: {connection_string}",
            code="mcp_invalid_connection_string",
            details={
                "service": service_name,
                "connection_string": connection_string,
                "expected_format": "mcp://<service-name>"
            }
        )


def validate_mcp_connections(config: AgentConfig) -> None:
    """Validate MCP connection strings (stub for Epic 2).

    In Epic 2, this will actually test connections to MCP servers.
    For now, we only validate connection string format.

    Args:
        config: Agent configuration with MCP connection settings

    Raises:
        MCPConnectionError: If any connection string is invalid
    """
    # Validate Gmail connection string
    validate_mcp_connection_string(
        config.mcp.gmail.connection_string,
        service_name="gmail"
    )

    # Validate Warranty API connection string
    validate_mcp_connection_string(
        config.mcp.warranty_api.connection_string,
        service_name="warranty_api"
    )

    # Validate Ticketing System connection string
    validate_mcp_connection_string(
        config.mcp.ticketing_system.connection_string,
        service_name="ticketing_system"
    )

    # TODO (Epic 2): Implement actual MCP connection testing
    # - Import MCP Python SDK
    # - Attempt to connect to each MCP server
    # - Use 5-second timeout for each connection test
    # - Raise MCPConnectionError if connection fails
    # For now, connection string validation is sufficient
