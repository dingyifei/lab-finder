# Integration Tests

Integration tests for Lab Finder that verify external system interactions.

## Test Categories

### MCP Server Tests
Tests in `test_mcp_servers.py` verify MCP server connectivity and configuration:
- Paper search MCP server launch and configuration
- LinkedIn MCP server launch via uvx
- MCP configuration structure validation

### CI Environment Behavior

Integration tests automatically adapt to CI environments:

**Local Development:**
- Tests use real MCP servers
- Requires MCP servers to be installed and configured
- Tests marked with `@pytest.mark.slow` run normally

**CI Environment (CI=true):**
- Tests use mocked MCP clients (see `conftest.py`)
- No actual MCP server installation required
- Tests marked with `@pytest.mark.slow` are automatically skipped
- Faster execution for CI pipeline

## Running Integration Tests

### Locally (Real MCP Servers)

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run without slow tests
pytest tests/integration/ -v -m "not slow"

# Run specific test file
pytest tests/integration/test_mcp_servers.py -v
```

### CI Mode (Mocked MCP Servers)

```bash
# Run with CI environment flag
CI=true pytest tests/integration/ -v

# This will:
# - Use mocked MCP clients from conftest.py
# - Skip slow tests automatically
# - Complete faster (suitable for CI pipeline)
```

## MCP Mocking Details

The `conftest.py` file provides fixtures that detect the CI environment:

### Fixtures

- `is_ci_environment`: Returns True when `CI=true` environment variable is set
- `mcp_papers_client`: Returns `MockMCPPapersClient` in CI, None otherwise
- `mcp_linkedin_client`: Returns `MockMCPLinkedInClient` in CI, None otherwise
- `skip_slow_tests_in_ci`: Auto-skip tests marked `@pytest.mark.slow` in CI

### Mock Clients

**MockMCPPapersClient:**
- Provides fake paper search results
- No actual paper-search-mcp server required
- Returns sample paper metadata

**MockMCPLinkedInClient:**
- Provides fake LinkedIn profile search results
- No actual mcp-linkedin server or credentials required
- Returns sample profile data

### Usage in Tests

```python
import pytest

@pytest.mark.integration
async def test_paper_search(mcp_papers_client):
    # mcp_papers_client is automatically mocked in CI
    if mcp_papers_client:
        # CI environment - use mock
        results = await mcp_papers_client.search_paper("machine learning")
    else:
        # Local environment - initialize real MCP client
        from src.utils.mcp_client import get_real_papers_client
        client = await get_real_papers_client()
        results = await client.search_paper("machine learning")

    assert "papers" in results
```

## Test Markers

- `@pytest.mark.integration`: Marks test as integration test
- `@pytest.mark.slow`: Marks test as slow (auto-skipped in CI)

## Adding New Integration Tests

1. Create test file in `tests/integration/`
2. Mark test class or function with `@pytest.mark.integration`
3. Use MCP client fixtures for automatic CI mocking
4. Mark network-dependent or slow tests with `@pytest.mark.slow`

Example:

```python
import pytest

@pytest.mark.integration
class TestNewFeature:

    async def test_feature_with_mcp(self, mcp_papers_client):
        """Test that adapts to CI environment automatically."""
        # Test code here - mcp_papers_client is mocked in CI
        pass

    @pytest.mark.slow
    async def test_slow_network_operation(self):
        """This test will be skipped in CI."""
        # Slow test code here
        pass
```

## Troubleshooting

**Integration tests fail locally:**
- Ensure MCP servers are installed (`pip list | grep paper-search-mcp`)
- Check credentials are configured in `.env`
- Verify uvx is installed for mcp-linkedin

**Integration tests fail in CI:**
- Check that CI=true environment variable is set in workflow
- Verify conftest.py fixtures are being used
- Check that slow tests are properly marked with `@pytest.mark.slow`

**Mock clients not working:**
- Ensure `is_ci_environment` fixture returns True
- Check that CI environment variable is exactly "true" (case-insensitive)
- Verify mock clients are imported correctly in conftest.py
