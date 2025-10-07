"""
Integration Test Configuration

Provides fixtures and configuration for integration tests.
When running in CI environment (CI=true), MCP servers are mocked to avoid
requiring actual MCP server installations.
"""

import os
import pytest
from unittest.mock import AsyncMock


@pytest.fixture
def is_ci_environment() -> bool:
    """
    Detect if tests are running in CI environment.

    Returns:
        True if CI environment variable is set to 'true'
    """
    return os.getenv("CI", "").lower() == "true"


@pytest.fixture
def mcp_papers_client(is_ci_environment):
    """
    Provide paper-search-mcp client (real or mocked based on environment).

    Args:
        is_ci_environment: Fixture indicating CI environment

    Returns:
        MockMCPPapersClient in CI, or None (for real client) otherwise
    """
    if is_ci_environment:
        return MockMCPPapersClient()
    else:
        # Return None to indicate real client should be used
        # Integration tests will initialize real MCP client when None
        return None


@pytest.fixture
def mcp_linkedin_client(is_ci_environment):
    """
    Provide mcp-linkedin client (real or mocked based on environment).

    Args:
        is_ci_environment: Fixture indicating CI environment

    Returns:
        MockMCPLinkedInClient in CI, or None (for real client) otherwise
    """
    if is_ci_environment:
        return MockMCPLinkedInClient()
    else:
        # Return None to indicate real client should be used
        return None


class MockMCPPapersClient:
    """
    Mock paper-search-mcp client for CI testing.

    Provides fake responses for paper search queries without requiring
    actual MCP server to be running.
    """

    def __init__(self):
        """Initialize mock papers client with sample data."""
        self.search_paper = AsyncMock(
            return_value={
                "papers": [
                    {
                        "title": "Sample Paper Title",
                        "authors": ["Author One", "Author Two"],
                        "year": 2024,
                        "abstract": "Sample abstract for testing",
                        "venue": "Sample Conference",
                        "citations": 10,
                    }
                ]
            }
        )

    async def close(self):
        """Mock close operation."""
        pass


class MockMCPLinkedInClient:
    """
    Mock mcp-linkedin client for CI testing.

    Provides fake responses for LinkedIn profile searches without requiring
    actual MCP server to be running or LinkedIn credentials.
    """

    def __init__(self):
        """Initialize mock LinkedIn client with sample data."""
        self.search_profile = AsyncMock(
            return_value={
                "profiles": [
                    {
                        "name": "Sample User",
                        "title": "PhD Student",
                        "institution": "Sample University",
                        "url": "https://linkedin.com/in/sample-user",
                    }
                ]
            }
        )

    async def close(self):
        """Mock close operation."""
        pass


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
