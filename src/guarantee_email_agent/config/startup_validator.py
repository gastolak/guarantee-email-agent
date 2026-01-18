"""Startup validation orchestrator for complete agent initialization checks."""

import time
import logging

from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.config.path_verifier import verify_instruction_paths, verify_eval_paths
from guarantee_email_agent.config.mcp_tester import validate_mcp_connections

logger = logging.getLogger(__name__)


def validate_startup(config: AgentConfig) -> None:
    """Complete startup validation orchestrator.

    Validates all configuration, file paths, and MCP connections.
    Logs progress and timing for each stage.

    Args:
        config: Complete agent configuration

    Raises:
        ConfigurationError: If file paths are invalid
        MCPConnectionError: If MCP connections fail
    """
    start_time = time.time()

    # Stage 1: Verify instruction file paths
    logger.info("Verifying instruction file paths...")
    stage_start = time.time()
    verify_instruction_paths(config)
    logger.info(f"Instruction paths verified ({time.time() - stage_start:.2f}s)")

    # Stage 2: Verify eval directory
    logger.info("Verifying eval directory...")
    stage_start = time.time()
    verify_eval_paths(config)
    logger.info(f"Eval paths verified ({time.time() - stage_start:.2f}s)")

    # Stage 3: Validate MCP connection strings (stub for Epic 2)
    logger.info("Validating MCP connection strings...")
    stage_start = time.time()
    validate_mcp_connections(config)
    logger.info(f"MCP connections validated ({time.time() - stage_start:.2f}s)")

    # Calculate total startup time
    total_time = time.time() - start_time
    logger.info(f"Startup validation complete ({total_time:.2f}s)")

    # Warn if approaching 30-second limit (NFR9)
    if total_time > 25:
        logger.warning(f"Startup validation took {total_time:.2f}s (approaching 30s limit)")
    elif total_time > 30:
        logger.error(f"Startup validation exceeded 30s limit: {total_time:.2f}s")
