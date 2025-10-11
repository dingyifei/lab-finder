"""
Integration Test Configuration

Provides fixtures and configuration for integration tests.
When running in CI environment (CI=true), slow tests are automatically skipped.
"""

import os
import pytest


@pytest.fixture
def is_ci_environment() -> bool:
    """
    Detect if tests are running in CI environment.

    Returns:
        True if CI environment variable is set to 'true'
    """
    return os.getenv("CI", "").lower() == "true"


@pytest.fixture(autouse=True)
def skip_slow_tests_in_ci(request, is_ci_environment):
    """
    Automatically skip slow integration tests when running in CI.

    Slow tests (marked with @pytest.mark.slow) are skipped in CI to keep
    workflow execution time under target (10 minutes).

    Args:
        request: pytest request fixture
        is_ci_environment: Fixture indicating CI environment
    """
    if is_ci_environment and request.node.get_closest_marker("slow"):
        pytest.skip("Skipping slow test in CI environment")
