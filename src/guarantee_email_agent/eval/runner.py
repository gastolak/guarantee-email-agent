"""Eval runner for executing test cases and validating results."""

import asyncio
import logging
import time
from typing import List, Tuple, Dict, Any

from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.config import load_config
from guarantee_email_agent.email.parser import EmailParser
from guarantee_email_agent.email.processor import EmailProcessor
from guarantee_email_agent.email.scenario_detector import ScenarioDetector
from guarantee_email_agent.email.serial_extractor import SerialNumberExtractor
from guarantee_email_agent.eval.models import (
    EvalTestCase,
    EvalResult,
    EvalExpectedOutput,
)
from guarantee_email_agent.eval.mocks import create_mock_clients
from guarantee_email_agent.instructions.loader import load_instruction_cached
from guarantee_email_agent.llm.response_generator import ResponseGenerator

logger = logging.getLogger(__name__)


class EvalRunner:
    """Execute eval test cases and validate results.

    Note: This is a simplified implementation for Story 4.1.
    Full integration with EmailProcessor will be completed when
    dependencies are ready.
    """

    def __init__(self, config=None):
        """Initialize eval runner.

        Args:
            config: Agent configuration (optional for now)
        """
        self.config = config
        logger.info("Eval runner initialized")

    async def run_test_case(self, test_case: EvalTestCase) -> EvalResult:
        """
        Execute single eval test case.

        Args:
            test_case: Eval test case to execute

        Returns:
            EvalResult with pass/fail and details
        """
        logger.info(f"Executing eval: {test_case.scenario_id}")

        start_time = time.time()

        try:
            # Create mock clients
            mocks = create_mock_clients(test_case)

            # Process email with real EmailProcessor using mocked clients
            actual_output = await self._process_with_mocks(test_case, mocks)

            # Measure processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Validate output
            passed, failures = self.validate_output(
                test_case.expected_output, actual_output, mocks, processing_time_ms
            )

            return EvalResult(
                test_case=test_case,
                passed=passed,
                failures=failures,
                actual_output=actual_output,
                processing_time_ms=processing_time_ms,
            )

        except Exception as e:
            logger.error(
                f"Eval execution failed: {test_case.scenario_id} - {e}", exc_info=True
            )
            return EvalResult(
                test_case=test_case,
                passed=False,
                failures=[f"Execution error: {str(e)}"],
                actual_output={},
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

    async def _process_with_mocks(
        self, test_case: EvalTestCase, mocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process email using real EmailProcessor with mocked clients.

        Args:
            test_case: Eval test case with input email
            mocks: Mock clients (gmail, warranty, ticketing)

        Returns:
            Processing result dictionary
        """
        # Load configuration (use default config.yaml)
        try:
            config = load_config("config.yaml")
        except Exception as e:
            logger.warning(f"Could not load config.yaml, using minimal config: {e}")
            # Create minimal config for eval
            config = self._create_minimal_config()

        # Load main instruction
        main_instruction = load_instruction_cached(config.instructions.main)

        # Create processor components with mocks
        parser = EmailParser()
        extractor = SerialNumberExtractor(config, main_instruction.body)
        detector = ScenarioDetector(config, main_instruction.body)
        response_generator = ResponseGenerator(config, main_instruction)

        # Create processor with mocked clients
        processor = EmailProcessor(
            config=config,
            parser=parser,
            extractor=extractor,
            detector=detector,
            gmail_client=mocks["gmail"],
            warranty_client=mocks["warranty"],
            ticketing_client=mocks["ticketing"],
            response_generator=response_generator,
        )

        # Build raw email from test case
        # Remove 'Z' suffix from ISO format as Python's fromisoformat doesn't handle it
        received_time = test_case.input.email.received.replace('Z', '+00:00')

        raw_email = {
            "subject": test_case.input.email.subject,
            "body": test_case.input.email.body,
            "from": test_case.input.email.from_address,
            "received": received_time,
        }

        # Process email
        result = await processor.process_email(raw_email)

        # Get response body from mock gmail client (last sent email)
        response_body = ""
        if mocks["gmail"].sent_emails:
            response_body = mocks["gmail"].sent_emails[-1].get("body", "")

        # Return simplified dict for validation
        return {
            "email_sent": result.success and result.response_sent,
            "response_body": response_body,
            "ticket_created": result.ticket_id is not None,
            "scenario_used": result.scenario_used or "unknown",
            "processing_time_ms": result.processing_time_ms,
        }

    def _create_minimal_config(self) -> AgentConfig:
        """Create minimal config for eval when config.yaml not available."""
        from guarantee_email_agent.config.schema import (
            AgentRuntimeConfig,
            InstructionConfig,
            LoggingConfig,
            MCPConfig,
            MCPServerConfig,
            SecretsConfig,
        )

        return AgentConfig(
            agent=AgentRuntimeConfig(polling_interval_seconds=60),
            instructions=InstructionConfig(
                main="instructions/main.md",
                scenarios_dir="instructions/scenarios",
            ),
            logging=LoggingConfig(level="INFO"),
            mcp=MCPConfig(
                gmail=MCPServerConfig(connection_string="stdio://mock"),
                warranty_api=MCPServerConfig(connection_string="stdio://mock"),
                ticketing_system=MCPServerConfig(connection_string="stdio://mock"),
            ),
            secrets=SecretsConfig(anthropic_api_key="mock-key-for-eval"),
        )

    def validate_output(
        self,
        expected: EvalExpectedOutput,
        actual: Dict[str, Any],
        mocks: Dict[str, Any],
        processing_time_ms: int,
    ) -> Tuple[bool, List[str]]:
        """
        Validate actual output against expected output.

        Args:
            expected: Expected output from test case
            actual: Actual processing result
            mocks: Mock clients with captured data
            processing_time_ms: Actual processing time

        Returns:
            Tuple of (passed, list of failure reasons)
        """
        failures = []

        # Check email sent
        email_sent = len(mocks["gmail"].sent_emails) > 0
        if expected.email_sent != email_sent:
            failures.append(f"email_sent: expected {expected.email_sent}, got {email_sent}")

        # Check response body contains
        if mocks["gmail"].sent_emails:
            response_body = mocks["gmail"].sent_emails[0]["body"]
            for phrase in expected.response_body_contains:
                if phrase.lower() not in response_body.lower():
                    failures.append(f"response_body_contains: missing phrase '{phrase}'")

            # Check response body excludes
            for phrase in expected.response_body_excludes:
                if phrase.lower() in response_body.lower():
                    failures.append(
                        f"response_body_excludes: unwanted phrase '{phrase}' present"
                    )

        # Check ticket created
        ticket_created = len(mocks["ticketing"].created_tickets) > 0
        if expected.ticket_created != ticket_created:
            failures.append(
                f"ticket_created: expected {expected.ticket_created}, got {ticket_created}"
            )

        # Check ticket fields if ticket created
        if expected.ticket_created and ticket_created and expected.ticket_fields:
            actual_ticket = mocks["ticketing"].created_tickets[0]["data"]
            for key, expected_value in expected.ticket_fields.items():
                if actual_ticket.get(key) != expected_value:
                    failures.append(
                        f"ticket_field[{key}]: expected '{expected_value}', "
                        f"got '{actual_ticket.get(key)}'"
                    )

        # Check scenario instruction used
        if actual.get("scenario_used") != expected.scenario_instruction_used:
            failures.append(
                f"scenario_instruction_used: expected '{expected.scenario_instruction_used}', "
                f"got '{actual.get('scenario_used')}'"
            )

        # Check processing time
        if processing_time_ms > expected.processing_time_ms:
            failures.append(
                f"processing_time_ms: {processing_time_ms}ms exceeds threshold "
                f"{expected.processing_time_ms}ms"
            )

        passed = len(failures) == 0
        return passed, failures

    async def run_suite(self, test_cases: List[EvalTestCase]) -> List[EvalResult]:
        """
        Execute complete eval suite.

        Args:
            test_cases: List of eval test cases

        Returns:
            List of EvalResults
        """
        logger.info(f"Running eval suite: {len(test_cases)} scenarios")

        results = []
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"Executing {i}/{len(test_cases)}: {test_case.scenario_id}")
            result = await self.run_test_case(test_case)
            results.append(result)

        logger.info(f"Eval suite complete: {len(results)} results")
        return results
