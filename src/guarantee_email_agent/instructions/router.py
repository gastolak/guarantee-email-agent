"""Scenario routing for instruction selection."""

import logging
from pathlib import Path
from typing import Optional

from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.instructions.loader import InstructionFile, load_instruction_cached
from guarantee_email_agent.utils.errors import InstructionError

logger = logging.getLogger(__name__)


class ScenarioRouter:
    """Routes scenarios to appropriate instruction files.

    Loads scenario-specific instruction files based on scenario names.
    Falls back to graceful-degradation scenario if scenario not found or load fails.
    """

    def __init__(self, config: AgentConfig):
        """Initialize scenario router.

        Args:
            config: Agent configuration with scenarios directory path

        Raises:
            InstructionError: If scenarios directory doesn't exist
        """
        self.config = config
        self.scenarios_dir = Path(config.instructions.scenarios_dir)

        # Verify scenarios directory exists
        if not self.scenarios_dir.exists():
            raise InstructionError(
                message=f"Scenarios directory not found: {self.scenarios_dir}",
                code="scenarios_dir_not_found",
                details={"path": str(self.scenarios_dir)}
            )

        logger.info(f"Scenario router initialized: {self.scenarios_dir}")

    def select_scenario(self, scenario_name: str) -> InstructionFile:
        """Select and load scenario instruction file.

        Args:
            scenario_name: Scenario identifier (e.g., "valid-warranty")

        Returns:
            Loaded InstructionFile for scenario

        Falls back to graceful-degradation on any error
        """
        try:
            # Build scenario file path
            scenario_file = self.scenarios_dir / f"{scenario_name}.md"

            # Load scenario instruction (cached)
            scenario_instruction = load_instruction_cached(str(scenario_file))

            # Verify trigger field matches (if present)
            if scenario_instruction.trigger and scenario_instruction.trigger != scenario_name:
                logger.warning(
                    f"Scenario trigger mismatch: file={scenario_name}, "
                    f"trigger={scenario_instruction.trigger}"
                )

            logger.info(
                f"Scenario loaded: {scenario_name} v{scenario_instruction.version}",
                extra={
                    "scenario_name": scenario_name,
                    "scenario_version": scenario_instruction.version,
                    "file_path": str(scenario_file)
                }
            )

            return scenario_instruction

        except FileNotFoundError:
            logger.warning(
                f"Scenario not found: {scenario_name}, using graceful-degradation",
                extra={"scenario_name": scenario_name}
            )
            return self._load_fallback_scenario()
        except InstructionError as e:
            logger.error(
                f"Failed to load scenario {scenario_name}: {e.message}, "
                f"using graceful-degradation",
                extra={"scenario_name": scenario_name, "error": e.message, "code": e.code}
            )
            return self._load_fallback_scenario()
        except Exception as e:
            logger.error(
                f"Unexpected error loading scenario {scenario_name}: {str(e)}, "
                f"using graceful-degradation",
                extra={"scenario_name": scenario_name, "error": str(e)},
                exc_info=True
            )
            return self._load_fallback_scenario()

    def _load_fallback_scenario(self) -> InstructionFile:
        """Load fallback graceful-degradation scenario.

        Returns:
            Graceful-degradation instruction file

        Raises:
            InstructionError: If fallback scenario cannot be loaded
        """
        fallback_file = self.scenarios_dir / "graceful-degradation.md"

        try:
            fallback = load_instruction_cached(str(fallback_file))
            logger.info(
                "Loaded graceful-degradation fallback scenario",
                extra={"fallback_version": fallback.version}
            )
            return fallback
        except Exception as e:
            raise InstructionError(
                message=f"Failed to load graceful-degradation fallback: {str(e)}",
                code="fallback_scenario_load_failed",
                details={"file": str(fallback_file), "error": str(e)}
            )
