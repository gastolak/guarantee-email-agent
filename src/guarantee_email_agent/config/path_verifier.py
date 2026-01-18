"""File path verification for configuration validation."""

from pathlib import Path
import logging

from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.utils.errors import ConfigurationError

logger = logging.getLogger(__name__)


def verify_file_exists(file_path: str, description: str = "File") -> None:
    """Verify a file exists and is readable.

    Args:
        file_path: Path to file to verify
        description: Human-readable description for error messages

    Raises:
        ConfigurationError: If file doesn't exist or isn't readable
    """
    path = Path(file_path)

    if not path.exists():
        raise ConfigurationError(
            message=f"{description} not found: {file_path}",
            code="config_file_not_found",
            details={"file_path": file_path, "description": description}
        )

    if not path.is_file():
        raise ConfigurationError(
            message=f"{description} is not a file: {file_path}",
            code="config_invalid_path",
            details={"file_path": file_path, "description": description}
        )

    # Check if readable
    try:
        with open(path, 'r') as f:
            f.read(1)  # Try reading first byte
    except PermissionError:
        raise ConfigurationError(
            message=f"Cannot read {description}: {file_path} (permission denied)",
            code="config_file_unreadable",
            details={"file_path": file_path, "description": description}
        )
    except Exception as e:
        raise ConfigurationError(
            message=f"Cannot access {description}: {file_path} ({str(e)})",
            code="config_file_error",
            details={"file_path": file_path, "description": description, "error": str(e)}
        )


def verify_instruction_paths(config: AgentConfig) -> None:
    """Verify all instruction file paths exist and are readable.

    Args:
        config: Agent configuration with instruction paths

    Raises:
        ConfigurationError: If any instruction file is missing or unreadable
    """
    # Verify main instruction file
    verify_file_exists(
        config.instructions.main,
        description="Main instruction file"
    )

    # Verify each scenario instruction file
    for scenario_path in config.instructions.scenarios:
        verify_file_exists(
            scenario_path,
            description="Scenario instruction file"
        )


def verify_eval_paths(config: AgentConfig) -> None:
    """Verify eval test suite directory exists.

    Creates the directory if it doesn't exist (with warning log).

    Args:
        config: Agent configuration with eval paths

    Raises:
        ConfigurationError: If eval directory doesn't exist and cannot be created,
                          or if path is not a directory
    """
    eval_dir = Path(config.eval.test_suite_path)

    if not eval_dir.exists():
        # Try to create directory
        try:
            eval_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Created eval directory: {config.eval.test_suite_path}")
        except Exception as e:
            raise ConfigurationError(
                message=f"Eval directory does not exist and cannot be created: {config.eval.test_suite_path}",
                code="config_directory_error",
                details={"directory": config.eval.test_suite_path, "error": str(e)}
            )

    if not eval_dir.is_dir():
        raise ConfigurationError(
            message=f"Eval path is not a directory: {config.eval.test_suite_path}",
            code="config_invalid_path",
            details={"path": config.eval.test_suite_path}
        )
