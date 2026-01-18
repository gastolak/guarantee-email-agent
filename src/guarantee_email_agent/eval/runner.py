"""Eval runner for executing test cases and validating results."""

import logging
import time
from typing import List, Tuple, Dict, Any

from guarantee_email_agent.eval.models import (
    EvalTestCase,
    EvalResult,
    EvalExpectedOutput,
)
from guarantee_email_agent.eval.mocks import create_mock_clients

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

            # TODO: Create processor with mocked clients and execute
            # For now, create a mock result based on test case
            actual_output = self._simulate_processing(test_case, mocks)

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

    def _simulate_processing(
        self, test_case: EvalTestCase, mocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate email processing for testing eval framework.

        This is a temporary placeholder until EmailProcessor integration is complete.
        """
        # Mock a successful processing
        actual_output = {
            "email_sent": False,
            "response_body": "",
            "ticket_created": False,
            "scenario_used": test_case.expected_output.scenario_instruction_used,
            "processing_time_ms": 1000,
        }
        return actual_output

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
