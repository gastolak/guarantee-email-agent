"""Eval reporting and pass rate calculation."""

import logging
from typing import List

from guarantee_email_agent.eval.models import EvalResult

logger = logging.getLogger(__name__)


class EvalReporter:
    """Calculate pass rates and format eval results."""

    def calculate_pass_rate(self, results: List[EvalResult]) -> float:
        """
        Calculate pass rate percentage.

        Args:
            results: List of eval results

        Returns:
            Pass rate as percentage (0-100)
        """
        if not results:
            return 0.0

        passed = sum(1 for r in results if r.passed)
        return (passed / len(results)) * 100.0

    def print_scenario_results(self, results: List[EvalResult]) -> None:
        """
        Print per-scenario results.

        Args:
            results: List of eval results
        """
        # Sort: passed first, then failed
        sorted_results = sorted(results, key=lambda r: (not r.passed, r.test_case.scenario_id))

        for result in sorted_results:
            print(result.format_for_display())
            if not result.passed and result.failures:
                for failure in result.failures:
                    print(f"  - {failure}")

    def print_summary(self, results: List[EvalResult], duration: float) -> None:
        """
        Print summary with pass rate.

        Args:
            results: List of eval results
            duration: Total execution time in seconds
        """
        if not results:
            print("\nNo eval scenarios found.")
            return

        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        pass_rate = self.calculate_pass_rate(results)

        print(f"\nPass rate: {passed}/{len(results)} ({pass_rate:.1f}%)")
        print(f"✓ Passed: {passed}")
        print(f"✗ Failed: {failed}")
        print(f"Duration: {duration:.2f}s")

        if pass_rate >= 99.0:
            print("🎉 Eval passed! (≥99% threshold)")
        else:
            print("⚠️  Eval failed (<99% threshold)")

    def print_failure_details(self, result: EvalResult) -> None:
        """
        Print detailed failure information.

        Args:
            result: Failed eval result
        """
        if result.passed:
            return

        print(f"\n❌ {result.test_case.scenario_id}: {result.test_case.description}")
        print(f"Category: {result.test_case.category}")

        for failure in result.failures:
            print(f"  • {failure}")

        # Print actual output excerpt if available
        if "response_body" in result.actual_output:
            response = result.actual_output["response_body"]
            if response:
                excerpt = response[:200] + "..." if len(response) > 200 else response
                print(f"\nActual response (excerpt):\n{excerpt}")
