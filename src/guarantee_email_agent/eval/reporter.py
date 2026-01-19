"""Eval reporting and pass rate calculation."""

import logging
from typing import List, Dict, Tuple
from collections import defaultdict

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

    def print_scenario_results(
        self, results: List[EvalResult], show_function_calls: bool = False
    ) -> None:
        """
        Print per-scenario results.

        Args:
            results: List of eval results
            show_function_calls: If True, show function call trace for each scenario
        """
        # Sort: passed first, then failed
        sorted_results = sorted(results, key=lambda r: (not r.passed, r.test_case.scenario_id))

        for result in sorted_results:
            print(result.format_for_display())
            if show_function_calls and result.actual_function_calls:
                print(result.format_function_calls())
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

    def print_detailed_failures(self, results: List[EvalResult], verbose: bool = False) -> None:
        """
        Print comprehensive detailed failure analysis for all failed scenarios.

        Args:
            results: List of eval results
            verbose: If True, include full response bodies and suggestions
        """
        failed_results = [r for r in results if not r.passed]

        if not failed_results:
            print("\n✅ All scenarios passed!")
            return

        print(f"\n{'='*80}")
        print(f"DETAILED FAILURE REPORT ({len(failed_results)} failures)")
        print(f"{'='*80}\n")

        # Group failures by category for pattern detection
        failures_by_category = self._group_failures_by_category(failed_results)

        # Print patterns first if any detected
        patterns = self._detect_patterns(failed_results)
        if patterns:
            print("⚠️  PATTERNS DETECTED:")
            for pattern in patterns:
                print(f"  • {pattern}")
            print()

        # Print each failure in detail
        for i, result in enumerate(failed_results, 1):
            self._print_single_detailed_failure(result, i, len(failed_results), verbose)

        # Print categorized summary
        print(f"\n{'='*80}")
        print("FAILURE SUMMARY BY CATEGORY")
        print(f"{'='*80}\n")
        for category, count in failures_by_category.items():
            print(f"  {category}: {count} failure(s)")

    def _print_single_detailed_failure(
        self,
        result: EvalResult,
        index: int,
        total: int,
        verbose: bool
    ) -> None:
        """Print detailed information for a single failed scenario."""
        print(f"[{index}/{total}] ❌ FAILURE: {result.test_case.scenario_id}")
        print(f"  Description: {result.test_case.description}")
        print(f"  Category: {result.test_case.category}")
        print()

        # Print function call trace if available
        if result.actual_function_calls:
            print(f"  FUNCTION CALLS:")
            print(result.format_function_calls())
            print()

        # Categorize and print failures
        categorized = self._categorize_failure_reasons(result.failures)

        for category, failures in categorized.items():
            print(f"  {category.upper()} FAILURES:")
            for failure_msg in failures:
                print(f"    - {failure_msg}")
                # Add suggestion
                suggestion = self._suggest_fix(category, failure_msg, result)
                if suggestion:
                    print(f"      💡 {suggestion}")
            print()

        # Print actual response if available and verbose
        if verbose and "response_body" in result.actual_output:
            response = result.actual_output.get("response_body", "")
            if response:
                print(f"  ACTUAL RESPONSE BODY:")
                print(f"  {'-'*76}")
                # Truncate if too long
                if len(response) > 500:
                    excerpt = response[:300] + "\n  ...\n  " + response[-200:]
                    print(f"  {excerpt}")
                else:
                    print(f"  {response}")
                print(f"  {'-'*76}")
                print()

        print(f"  Processing time: {result.processing_time_ms}ms")
        print()

    def _categorize_failure_reasons(self, failures: List[str]) -> Dict[str, List[str]]:
        """Categorize failure messages by type."""
        categories = defaultdict(list)

        for failure in failures:
            if "response_body_contains" in failure:
                categories["Response Content"].append(failure)
            elif "response_body_excludes" in failure:
                categories["Response Content"].append(failure)
            elif "scenario_instruction_used" in failure:
                categories["Scenario Routing"].append(failure)
            elif "ticket_created" in failure:
                categories["Ticket Creation"].append(failure)
            elif "ticket_field" in failure:
                categories["Ticket Fields"].append(failure)
            elif "email_sent" in failure:
                categories["Email Sending"].append(failure)
            elif "processing_time_ms" in failure:
                categories["Performance"].append(failure)
            elif "Function" in failure and ("mismatch" in failure or "missing" in failure):
                categories["Function Calls"].append(failure)
            elif "function call" in failure.lower() or "unexpected" in failure.lower():
                categories["Function Calls"].append(failure)
            elif "does not contain" in failure.lower():
                categories["Function Calls"].append(failure)
            else:
                categories["Other"].append(failure)

        return dict(categories)

    def _suggest_fix(self, category: str, failure_msg: str, result: EvalResult) -> str:
        """Generate actionable fix suggestion based on failure type."""
        scenario = result.test_case.expected_output.scenario_instruction_used

        if category == "Response Content":
            return f"Review scenario instruction: instructions/scenarios/{scenario}.md"
        elif category == "Scenario Routing":
            return "Review scenario detection logic in src/guarantee_email_agent/email/scenario_detector.py"
        elif category == "Ticket Creation" or category == "Ticket Fields":
            return "Review ticket creation logic in src/guarantee_email_agent/email/processor.py"
        elif category == "Performance":
            return "Profile execution to identify slow steps (target: <60s per NFR7)"
        elif category == "Email Sending":
            return "Review email sending logic in src/guarantee_email_agent/email/processor.py"
        elif category == "Function Calls":
            return f"Review function definitions in: instructions/scenarios/{scenario}.md"
        else:
            return "Review test case expectations or implementation logic"

    def _group_failures_by_category(self, results: List[EvalResult]) -> Dict[str, int]:
        """Group all failures by category to detect patterns."""
        category_counts = defaultdict(int)

        for result in results:
            categorized = self._categorize_failure_reasons(result.failures)
            for category in categorized.keys():
                category_counts[category] += 1

        return dict(category_counts)

    def _detect_patterns(self, results: List[EvalResult]) -> List[str]:
        """Detect patterns across multiple failures."""
        patterns = []

        # Count failures by test category
        test_categories = defaultdict(int)
        for result in results:
            test_categories[result.test_case.category] += 1

        # Detect if multiple failures in same test category
        for category, count in test_categories.items():
            if count >= 2:
                patterns.append(
                    f"{count} failures in '{category}' category - consider reviewing {category} scenarios"
                )

        # Count failures by scenario instruction
        scenario_failures = defaultdict(int)
        for result in results:
            scenario = result.test_case.expected_output.scenario_instruction_used
            scenario_failures[scenario] += 1

        # Detect if multiple failures for same scenario
        for scenario, count in scenario_failures.items():
            if count >= 2:
                patterns.append(
                    f"{count} failures expected scenario '{scenario}' - review instructions/scenarios/{scenario}.md"
                )

        return patterns
