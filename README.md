# Lab Finder

[![CI Pipeline](https://github.com/dingyifei/lab-finder/actions/workflows/ci.yml/badge.svg)](https://github.com/dingyifei/lab-finder/actions/workflows/ci.yml)

A Python-based tool for systematically discovering and analyzing research labs within target universities using the Claude Agent SDK.

## Overview

Lab Finder automates the research lab discovery process by:
- Discovering university department structures
- Identifying and filtering relevant professors
- Analyzing lab websites and publications
- Matching lab members via LinkedIn
- Generating comprehensive fitness reports

## Setup Instructions

### Prerequisites

- Python 3.11.7 or higher
- pip 23.3 or higher
- uv package runner (for mcp-linkedin server)
- Git

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd lab-finder
   ```

2. **Create and activate virtual environment:**
   ```bash
   # On Windows:
   py -3.11 -m venv venv
   venv\Scripts\activate

   # On macOS/Linux:
   python3.11 -m venv venv
   source venv/bin/activate
   ```

3. **Install pip-tools:**
   ```bash
   pip install pip-tools
   ```

4. **Compile and install dependencies:**
   ```bash
   # Generate requirements.txt with pinned versions
   pip-compile requirements.in

   # Install all dependencies
   pip install -r requirements.txt
   ```

5. **Install Playwright browser drivers:**
   ```bash
   playwright install chromium
   ```

6. **Install uv package runner (for mcp-linkedin):**
   ```bash
   pip install uv
   ```

7. **Verify installation:**
   ```bash
   python scripts/verify_dependencies.py
   ```

### MCP Server Configuration

Lab Finder uses two MCP (Model Context Protocol) servers for external data access:

#### 1. paper-search-mcp (Academic Publications)

**Installation:**
```bash
# paper-search-mcp is already installed as part of requirements.txt
# Verify installation:
python -m paper_search_mcp.server
# Press Ctrl+C to exit
```

**Configuration:**
- No credentials required
- Optional: Set `SEMANTIC_SCHOLAR_API_KEY` in `.env` for higher rate limits
- Used in Epic 5 for publication retrieval

**STDIO Configuration (handled by Claude Agent SDK):**
```python
{
    "type": "stdio",
    "command": "python",  # Uses current Python interpreter
    "args": ["-m", "paper_search_mcp.server"]
}
```

#### 2. mcp-linkedin (LinkedIn Profile Matching)

**Installation:**
```bash
# No pre-installation needed - runs on-demand via uvx
# Verify uvx is installed:
uvx --version
# Should output: uvx 0.8.23 or higher
```

**Configuration:**
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your LinkedIn credentials:
   ```bash
   LINKEDIN_EMAIL=your-email@example.com
   LINKEDIN_PASSWORD=your-secure-password
   ```

3. **Important:** Never commit `.env` to git (already in `.gitignore`)

**STDIO Configuration (handled by Claude Agent SDK):**
```python
{
    "type": "stdio",
    "command": "uvx",
    "args": [
        "--from",
        "git+https://github.com/adhikasp/mcp-linkedin",
        "mcp-linkedin"
    ],
    "env": {
        "LINKEDIN_EMAIL": "your-email@example.com",
        "LINKEDIN_PASSWORD": "your-secure-password"
    }
}
```

**LinkedIn MCP Server Notes:**
- Uses unofficial LinkedIn API - use at your own risk
- First run downloads package from git (may take 30-60 seconds)
- Subsequent runs are faster (cached by uvx)
- Used in Epic 6 for LinkedIn profile matching

#### MCP Server Testing

**Unit Tests:**
```bash
# Test configuration helper
pytest tests/unit/test_mcp_client.py -v
```

**Integration Tests:**
```bash
# Test server launch (fast tests only)
pytest tests/integration/test_mcp_servers.py -v -m "not slow"

# Test with actual server download (slow, requires network)
pytest tests/integration/test_mcp_servers.py -v
```

#### Using MCP Servers in Code

```python
from src.utils.mcp_client import get_mcp_server_config, validate_mcp_config
from claude_agent_sdk import ClaudeAgentOptions

# Validate credentials are configured
is_valid, errors = validate_mcp_config()
if not is_valid:
    for error in errors:
        print(f"Configuration error: {error}")

# Get MCP server configuration
mcp_config = get_mcp_server_config()

# Pass to Claude Agent SDK
options = ClaudeAgentOptions(
    mcp_servers=mcp_config,
    allowed_tools=[
        "mcp__papers__search_papers",
        "mcp__linkedin__search_people",
        "mcp__linkedin__get_profile"
    ]
)
```

### Troubleshooting

**ImportError for claude-agent-sdk:**
- Verify the Claude Agent SDK version is compatible with Python 3.11.7
- Check for pre-release versions if stable release unavailable

**Playwright installation issues:**
- Run `playwright install --help` for platform-specific options
- On Linux, you may need system dependencies: `playwright install-deps`

**MCP Server Troubleshooting:**

*paper-search-mcp issues:*
- `ModuleNotFoundError: No module named 'paper_search_mcp'`
  - Run: `pip install paper-search-mcp>=0.1.3`
  - Verify virtual environment is activated

*mcp-linkedin issues:*
- `uvx: command not found`
  - Install uv: `pip install uv`
  - Verify installation: `uvx --version`

- `Git operation failed` when launching mcp-linkedin
  - Check network connectivity
  - Verify git repository accessible: https://github.com/adhikasp/mcp-linkedin
  - Try manual clone: `git clone https://github.com/adhikasp/mcp-linkedin`

- LinkedIn authentication errors
  - Verify `.env` file exists and contains LINKEDIN_EMAIL and LINKEDIN_PASSWORD
  - Check credentials are correct (test by logging into LinkedIn web)
  - Note: LinkedIn may block automated access - use at your own risk

*General MCP issues:*
- MCP servers run as background processes via STDIO
- Claude Agent SDK handles spawning/communication automatically
- Check `src/utils/mcp_client.py` for configuration
- Review logs for MCP-related errors
- Run integration tests: `pytest tests/integration/test_mcp_servers.py -v`

## Testing

Lab Finder uses pytest for testing with comprehensive coverage reporting.

### Running Tests

**Run all tests:**
```bash
pytest
```

**Run with verbose output:**
```bash
pytest -v
```

**Run specific test file:**
```bash
pytest tests/unit/test_validator.py -v
```

**Run specific test function:**
```bash
pytest tests/unit/test_validator.py::TestSchemaLoading::test_load_schema_success -v
```

### Test Categories

**Unit Tests:**
```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with marker filtering
pytest -m unit -v
```

**Integration Tests:**
```bash
# Run all integration tests
pytest tests/integration/ -v

# Run with marker filtering
pytest -m integration -v
```

### Coverage Reports

**Generate coverage report:**
```bash
# Terminal report with missing lines
pytest --cov=src --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov=src --cov-report=html
# View at htmlcov/index.html
```

**Coverage requirements:**
- Minimum 70% code coverage required
- Configured in `pytest.ini`
- HTML reports saved to `htmlcov/` directory

### Test Organization

Tests follow the source structure:

```
tests/
├── unit/              # Unit tests (70% minimum coverage)
│   ├── test_validator.py
│   ├── test_checkpoint_manager.py
│   ├── test_example.py (example patterns)
│   └── ...
├── integration/       # Integration tests (MCP, I/O, multi-component)
│   ├── test_mcp_servers.py
│   ├── test_example_integration.py (example patterns)
│   └── ...
└── fixtures/          # Test data
    ├── sample_user_profile.json
    ├── sample_university_config.json
    ├── invalid_user_profile.json
    └── README.md (fixture documentation)
```

### Example Test Patterns

**Example test files demonstrate:**
- AAA (Arrange-Act-Assert) pattern
- Async tests with pytest-asyncio
- Mocking with pytest-mock
- Parametrized tests
- Fixture usage
- Error handling tests

**View examples:**
- Unit test patterns: `tests/unit/test_example.py`
- Integration test patterns: `tests/integration/test_example_integration.py`

### Test Fixtures

**Available fixtures:**
- `tests/fixtures/sample_user_profile.json` - Valid user profile
- `tests/fixtures/sample_university_config.json` - Valid university config
- `tests/fixtures/invalid_user_profile.json` - Invalid config for validation tests
- `tests/fixtures/invalid_university_config.json` - Invalid config for error testing

**Load fixtures in tests:**
```python
import json
from pathlib import Path

def test_with_fixture():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_user_profile.json"
    with open(fixture_path, 'r') as f:
        config = json.load(f)
    # Use config in test...
```

See `tests/fixtures/README.md` for complete fixture documentation.

### Continuous Integration

**Pre-commit checks:**
```bash
# Run linting
ruff check src/ tests/

# Run type checking
mypy src/

# Run full test suite
pytest -v
```

**CI Pipeline (when configured):**
- Linting with ruff
- Type checking with mypy
- Unit tests with coverage
- Integration tests
- Coverage report upload

## Requirements

- Python 3.11.7
- Claude Agent SDK 0.1.1+
- MCP servers: paper-search-mcp, mcp-linkedin

## Documentation

- [Product Requirements](docs/prd.md)
- [Architecture](docs/architecture.md)

## License

_(To be determined)_
