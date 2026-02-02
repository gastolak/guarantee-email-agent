"""Eval runner for executing test cases and validating results."""

import asyncio
import logging
import time
from typing import List, Tuple, Dict, Any, Optional

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
    ActualFunctionCall,
)
from guarantee_email_agent.eval.mocks import (
    create_mock_clients,
    create_mock_function_dispatcher,
)
from guarantee_email_agent.eval.validator import validate_function_calls
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

            # Create mock function dispatcher if using function calling
            mock_dispatcher = None
            if test_case.input.mock_function_responses:
                mock_dispatcher = create_mock_function_dispatcher(test_case)

            # Process email with real EmailProcessor using mocked clients
            actual_output = await self._process_with_mocks(
                test_case, mocks, mock_dispatcher
            )

            # Measure processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Get actual function calls from mock dispatcher
            actual_function_calls: List[ActualFunctionCall] = []
            if mock_dispatcher:
                actual_function_calls = mock_dispatcher.get_function_calls()

            # Validate output
            passed, failures = self.validate_output(
                test_case.expected_output,
                actual_output,
                mocks,
                processing_time_ms,
                actual_function_calls,
            )

            return EvalResult(
                test_case=test_case,
                passed=passed,
                failures=failures,
                actual_output=actual_output,
                processing_time_ms=processing_time_ms,
                actual_function_calls=actual_function_calls,
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
        self,
        test_case: EvalTestCase,
        mocks: Dict[str, Any],
        mock_dispatcher=None,
    ) -> Dict[str, Any]:
        """Process email using real EmailProcessor with mocked clients.

        Args:
            test_case: Eval test case with input email
            mocks: Mock clients (gmail, warranty, ticketing)
            mock_dispatcher: Optional mock function dispatcher for function calling

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

        # Create processor with mocked tools
        processor = EmailProcessor(
            config=config,
            parser=parser,
            extractor=extractor,
            detector=detector,
            gmail_tool=mocks["gmail_tool"],
            crm_abacus_tool=mocks["crm_abacus_tool"],
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

        # Process email - use function calling if mock dispatcher provided
        if mock_dispatcher is not None:
            result = await processor.process_email_with_functions(
                raw_email,
                use_function_calling=True,
                function_dispatcher=mock_dispatcher
            )
        else:
            result = await processor.process_email(raw_email)

        # Get response body from mock gmail tool (last sent email)
        response_body = ""
        if mocks["gmail_tool"].sent_emails:
            response_body = mocks["gmail_tool"].sent_emails[-1].get("body", "")

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
            ToolsConfig,
            GmailToolConfig,
            CrmAbacusToolConfig,
            TicketDefaults,
            SecretsConfig,
        )

        return AgentConfig(
            agent=AgentRuntimeConfig(polling_interval_seconds=60),
            instructions=InstructionConfig(
                main="instructions/main.md",
                scenarios_dir="instructions/scenarios",
            ),
            logging=LoggingConfig(level="INFO"),
            tools=ToolsConfig(
                gmail=GmailToolConfig(
                    api_endpoint="https://gmail.googleapis.com/gmail/v1",
                    timeout_seconds=10
                ),
                crm_abacus=CrmAbacusToolConfig(
                    base_url="http://mock-crm.local",
                    ticket_defaults=TicketDefaults()
                )
            ),
            secrets=SecretsConfig(anthropic_api_key="mock-key-for-eval"),
        )

    def validate_output(
        self,
        expected: EvalExpectedOutput,
        actual: Dict[str, Any],
        mocks: Dict[str, Any],
        processing_time_ms: int,
        actual_function_calls: Optional[List[ActualFunctionCall]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validate actual output against expected output.

        Args:
            expected: Expected output from test case
            actual: Actual processing result
            mocks: Mock clients with captured data
            processing_time_ms: Actual processing time
            actual_function_calls: Function calls made during execution

        Returns:
            Tuple of (passed, list of failure reasons)
        """
        failures = []

        # Validate function calls if expected
        if expected.expected_function_calls and actual_function_calls is not None:
            function_failures = validate_function_calls(
                expected.expected_function_calls,
                actual_function_calls
            )
            failures.extend(function_failures)

        # Check email sent (legacy validation - also checked via function calls)
        email_sent = len(mocks["gmail_tool"].sent_emails) > 0
        if expected.email_sent is not None and expected.email_sent != email_sent:
            failures.append(f"email_sent: expected {expected.email_sent}, got {email_sent}")

        # Check response body contains
        if mocks["gmail_tool"].sent_emails:
            response_body = mocks["gmail_tool"].sent_emails[0]["body"]
            for phrase in expected.response_body_contains:
                if phrase.lower() not in response_body.lower():
                    failures.append(f"response_body_contains: missing phrase '{phrase}'")

            # Check response body excludes
            for phrase in expected.response_body_excludes:
                if phrase.lower() in response_body.lower():
                    failures.append(
                        f"response_body_excludes: unwanted phrase '{phrase}' present"
                    )

        # Check ticket created (only if explicitly expected, skip for function calling mode)
        ticket_created = len(mocks["crm_abacus_tool"].created_tickets) > 0
        if expected.ticket_created is not None and expected.ticket_created != ticket_created:
            failures.append(
                f"ticket_created: expected {expected.ticket_created}, got {ticket_created}"
            )

        # Check ticket fields if ticket created
        if expected.ticket_created and ticket_created and expected.ticket_fields:
            actual_ticket = mocks["crm_abacus_tool"].created_tickets[0]
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
