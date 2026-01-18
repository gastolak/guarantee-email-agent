"""Load and validate eval test cases from YAML files."""

import logging
from pathlib import Path
from typing import List, Dict, Any
import yaml

from guarantee_email_agent.eval.models import (
    EvalTestCase,
    EvalInput,
    EvalExpectedOutput,
    EvalEmail,
)
from guarantee_email_agent.utils.errors import EvalError

logger = logging.getLogger(__name__)


class EvalLoader:
    """Load and validate eval test cases from YAML files."""

    def load_eval_test_case(self, file_path: str) -> EvalTestCase:
        """
        Load and parse single eval test case from YAML.

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed EvalTestCase

        Raises:
            EvalError: If YAML invalid or schema validation fails
        """
        try:
            # Read YAML file
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)

            # Validate schema
            self.validate_test_case(data, file_path)

            # Parse sections
            eval_email = EvalEmail(
                subject=data["input"]["email"]["subject"],
                body=data["input"]["email"]["body"],
                from_address=data["input"]["email"]["from"],
                received=data["input"]["email"]["received"],
            )

            eval_input = EvalInput(
                email=eval_email,
                mock_responses=data["input"].get("mock_responses", {}),
            )

            eval_expected = EvalExpectedOutput(
                email_sent=data["expected_output"]["email_sent"],
                response_body_contains=data["expected_output"].get(
                    "response_body_contains", []
                ),
                response_body_excludes=data["expected_output"].get(
                    "response_body_excludes", []
                ),
                ticket_created=data["expected_output"]["ticket_created"],
                ticket_fields=data["expected_output"].get("ticket_fields"),
                scenario_instruction_used=data["expected_output"][
                    "scenario_instruction_used"
                ],
                processing_time_ms=data["expected_output"].get(
                    "processing_time_ms", 60000
                ),
            )

            test_case = EvalTestCase(
                scenario_id=data["scenario_id"],
                description=data["description"],
                category=data["category"],
                created=data["created"],
                input=eval_input,
                expected_output=eval_expected,
            )

            logger.debug(f"Loaded eval test case: {test_case.scenario_id}")
            return test_case

        except FileNotFoundError:
            raise EvalError(
                message=f"Eval file not found: {file_path}",
                code="eval_file_not_found",
                details={"file_path": file_path},
            )
        except yaml.YAMLError as e:
            raise EvalError(
                message=f"Invalid YAML in eval file: {file_path}",
                code="eval_yaml_invalid",
                details={"file_path": file_path, "error": str(e)},
            )
        except KeyError as e:
            raise EvalError(
                message=f"Missing required field in eval file: {file_path} - {e}",
                code="eval_missing_field",
                details={"file_path": file_path, "field": str(e)},
            )

    def validate_test_case(self, data: Dict[str, Any], file_path: str) -> None:
        """
        Validate eval test case schema.

        Args:
            data: Parsed YAML data
            file_path: File path for error messages

        Raises:
            EvalError: If validation fails
        """
        required_top_level = [
            "scenario_id",
            "description",
            "category",
            "created",
            "input",
            "expected_output",
        ]
        for field in required_top_level:
            if field not in data:
                raise EvalError(
                    message=f"Missing required field: {field}",
                    code="eval_missing_field",
                    details={"file_path": file_path, "field": field},
                )

        # Validate input section
        if "email" not in data["input"]:
            raise EvalError(
                message="Missing input.email section",
                code="eval_missing_field",
                details={"file_path": file_path, "field": "input.email"},
            )

        required_email_fields = ["subject", "body", "from", "received"]
        for field in required_email_fields:
            if field not in data["input"]["email"]:
                raise EvalError(
                    message=f"Missing input.email.{field}",
                    code="eval_missing_field",
                    details={"file_path": file_path, "field": f"input.email.{field}"},
                )

        # Validate expected_output section
        required_output_fields = [
            "email_sent",
            "ticket_created",
            "scenario_instruction_used",
        ]
        for field in required_output_fields:
            if field not in data["expected_output"]:
                raise EvalError(
                    message=f"Missing expected_output.{field}",
                    code="eval_missing_field",
                    details={
                        "file_path": file_path,
                        "field": f"expected_output.{field}",
                    },
                )

    def discover_test_cases(self, directory: str) -> List[EvalTestCase]:
        """
        Discover all eval test cases in directory.

        Args:
            directory: Path to evals/scenarios directory

        Returns:
            List of EvalTestCase objects

        Note:
            Files must match pattern: {category}_{number}.yaml
        """
        test_cases = []
        eval_dir = Path(directory)

        if not eval_dir.exists():
            logger.warning(f"Eval directory not found: {directory}")
            return []

        # Find all .yaml files
        yaml_files = sorted(eval_dir.glob("*.yaml"))

        logger.info(f"Discovering eval test cases in {directory}")

        for yaml_file in yaml_files:
            try:
                test_case = self.load_eval_test_case(str(yaml_file))
                test_cases.append(test_case)
                logger.debug(f"Discovered: {test_case.scenario_id}")
            except EvalError as e:
                logger.error(f"Failed to load {yaml_file.name}: {e.message}")
                # Continue loading other files

        logger.info(f"Discovered {len(test_cases)} eval test cases")
        return test_cases
