# Integration Tests

Integration tests for Lab Finder that verify external system interactions.

## Test Categories

### MCP Server Tests
Tests in `test_mcp_servers.py` verify MCP server configuration:
- Validates `claude/.mcp.json` exists and is valid JSON
- Verifies all three required MCP servers are configured (Puppeteer, papers, linkedin)
- Checks server configurations have required fields (type, command, args)
- Validates specific server settings (npx for Puppeteer, python for papers, uvx for LinkedIn)

**Note:** The Claude Agent SDK handles actual MCP server spawning and communication via `claude/.mcp.json`. Integration tests validate configuration only.

### CI Environment Behavior

Integration tests automatically adapt to CI environments:

**Local Development:**
- Tests use real MCP servers configured in `claude/.mcp.json`
- Requires MCP servers to be installed (paper-search-mcp, mcp-linkedin)
- Tests marked with `@pytest.mark.slow` run normally

**CI Environment (CI=true):**
- Tests marked with `@pytest.mark.slow` are automatically skipped
- Faster execution for CI pipeline
- MCP configuration tests still run (validate `.mcp.json` structure only)

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

### CI Mode

```bash
# Run with CI environment flag (skips slow tests)
CI=true pytest tests/integration/ -v
```

## MCP Server Configuration

MCP servers are configured via `claude/.mcp.json` (not Python code). The SDK discovers and manages servers automatically.

**Configuration File:**
- Location: `claude/.mcp.json`
- Format: JSON with `mcpServers` key
- Required servers: `puppeteer`, `papers`, `linkedin`

**Usage in Code:**
```python
from claude_agent_sdk import ClaudeAgentOptions
from pathlib import Path

# SDK loads MCP servers from claude/.mcp.json
options = ClaudeAgentOptions(
    cwd=Path(__file__).parent.parent / "claude",  # Points to claude/ directory
    setting_sources=["project"],                   # Loads .mcp.json
    allowed_tools=["mcp__puppeteer__navigate", "mcp__puppeteer__evaluate"]
)
```

## Test Fixtures

### is_ci_environment
Returns `True` when `CI=true` environment variable is set

### skip_slow_tests_in_ci
Auto-skip tests marked `@pytest.mark.slow` in CI environment

**Note:** MCP mocking is not needed - SDK handles MCP communication. Tests validate configuration structure only.

## Test Markers

- `@pytest.mark.integration`: Marks test as integration test
- `@pytest.mark.slow`: Marks test as slow (auto-skipped in CI)

## Adding New Integration Tests

1. Create test file in `tests/integration/`
2. Mark test class or function with `@pytest.mark.integration`
3. Mark network-dependent or slow tests with `@pytest.mark.slow`
4. For MCP-related tests, validate `.mcp.json` configuration (SDK handles execution)

Example:

```python
import pytest
import json
from pathlib import Path

@pytest.mark.integration
class TestNewMCPFeature:

    def test_mcp_config_has_new_server(self):
        """Test that new MCP server is configured in .mcp.json."""
        mcp_config_path = Path("claude/.mcp.json")

        with open(mcp_config_path, "r") as f:
            config = json.load(f)

        assert "new_server" in config["mcpServers"]
        assert config["mcpServers"]["new_server"]["type"] == "stdio"
```

## Troubleshooting

**Integration tests fail locally:**
- Ensure `claude/.mcp.json` exists and is valid JSON
- Verify MCP servers are installed (pip list | grep paper-search-mcp)
- Check uvx is installed for mcp-linkedin

**Integration tests fail in CI:**
- Check that CI=true environment variable is set in workflow
- Verify slow tests are properly marked with `@pytest.mark.slow`
- Ensure `.mcp.json` validation tests don't require actual MCP servers

**MCP configuration errors:**
- Validate `.mcp.json` syntax with JSON linter
- Check all three servers are present: puppeteer, papers, linkedin
- Verify command paths match installed tools (npx, python, uvx)
