# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Claude Agent SDK Integration

This project uses the **Claude Agent SDK** (FREE) for all LLM interactions. The SDK provides two operational modes:

### SDK Implementation: ClaudeSDKClient with Isolated Context

**Primary Mode: `ClaudeSDKClient` - Stateless with Context Isolation (CURRENT IMPLEMENTATION)**
- **Purpose:** Single request-response operations with no conversation memory and NO codebase context injection
- **When to use:** Department filtering, abstract scoring, profile consolidation, professor matching
- **Implementation:** All functions in `src/utils/llm_helpers.py` use this pattern
- **Configuration:** `ClaudeAgentOptions(max_turns=1, allowed_tools=[], system_prompt="...", setting_sources=None)`
- **Cost:** FREE (included with Claude Agent SDK)

**Critical Bug Fixed (2025-10-07):** The standalone `query()` function was found to inject unwanted codebase context (git status, file system) even with `allowed_tools=[]`, causing Claude to respond in "coding assistant" mode instead of analyzing provided data. Solution: Use `ClaudeSDKClient` class with proper isolation configuration.

**Alternative Mode: Multi-turn conversations (NOT CURRENTLY USED)**
- **Purpose:** Complex iterative tasks requiring context across multiple turns
- **Status:** Not currently used in Lab Finder (may be added in future phases)
- **Cost:** FREE (included with Claude Agent SDK)

### Key Architectural Points

1. **ClaudeSDKClient Configuration for Context Isolation**
   ```python
   from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

   options = ClaudeAgentOptions(
       max_turns=1,              # Stateless one-shot
       allowed_tools=[],         # No file access
       system_prompt="You are an expert text analyst. Respond directly to user prompts with the requested analysis.",
       setting_sources=None      # CRITICAL: Prevents codebase context injection
   )

   async with ClaudeSDKClient(options=options) as client:
       await client.query(prompt)
       async for message in client.receive_response():
           # Process response...
   ```

2. **Lab Finder uses `ClaudeSDKClient` for all LLM helpers**
   - `call_llm_with_retry()` uses `ClaudeSDKClient` with isolated context
   - `analyze_department_relevance()` uses `ClaudeSDKClient` for text analysis
   - `filter_professor_research()` uses `ClaudeSDKClient` for matching
   - All one-off, stateless operations with proper context isolation

3. **Web scraping uses SDK with tools enabled**
   - University discovery: `ClaudeSDKClient` with `allowed_tools=["WebFetch", "WebSearch"]`
   - Professor scraping: `ClaudeSDKClient` with tools enabled
   - Still stateless mode, but with tool access and context isolation

4. **No paid Anthropic API used**
   - All LLM calls go through Claude Agent SDK `ClaudeSDKClient`
   - No `anthropic.messages.create()` calls anywhere in codebase
   - Do NOT use standalone `query()` function (context injection bug)
   - Everything is FREE via Claude Agent SDK

## Project Overview

Lab Finder is a Python-based multi-agent research lab discovery system built with the Claude Agent SDK. It automates the process of finding, analyzing, and ranking research labs within universities by:
- Discovering university department structures
- Identifying and filtering relevant professors
- Scraping lab websites and analyzing publications
- Matching lab members via LinkedIn
- Generating comprehensive fitness reports with scoring and recommendations

**Architecture:** Monolithic multi-agent Python application with phased pipeline orchestration. Each phase produces checkpoints for resumability.

**Implementation Status:** Epic 1 (Foundation) complete ✅ | Epic 2 (University Discovery) in progress 🚧 | Story 2.4 complete
**Last Updated:** 2025-10-07

## Commands

### Development Environment Setup

```bash
# Create and activate virtual environment (Windows)
py -3.11 -m venv venv
venv\Scripts\activate

# Create and activate virtual environment (macOS/Linux)
python3.11 -m venv venv
source venv/bin/activate

# Compile and install dependencies
pip-compile requirements.in
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Verify installation
python scripts/verify_dependencies.py
```

### Testing

```bash
# Run all tests (coverage automatic via pytest.ini)
# - 70% minimum coverage enforced
# - Terminal report shows missing lines
# - HTML report generated to htmlcov/
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_validator.py -v

# Run single test function
pytest tests/unit/test_validator.py::TestSchemaLoading::test_load_schema_success -v

# Run integration tests only
pytest tests/integration/ -v -m integration

# Run unit tests only (exclude integration)
pytest tests/unit/ -v

# Run tests with verbose output and stop on first failure
pytest tests/ -v -x

# View HTML coverage report (auto-generated)
# Open htmlcov/index.html in browser after running pytest
```

### Code Quality

```bash
# Run ruff linter (check only)
ruff check src/ tests/

# Run ruff linter with auto-fix
ruff check src/ tests/ --fix

# Run mypy type checker
mypy src/

# Run both linting and type checking
ruff check src/ tests/ && mypy src/
```

### Dependency Management

```bash
# Add new dependency to requirements.in, then:
pip-compile requirements.in
pip install -r requirements.txt

# Update all dependencies to latest versions
pip-compile requirements.in --upgrade
pip install -r requirements.txt
```

### Running the Application

```bash
# Run full pipeline (not yet implemented - will be in main.py)
venv/Scripts/python.exe main.py --config config/university.json

# Validate configurations only
venv/Scripts/python.exe -m src.utils.validator --config config/
```

## High-Level Architecture

### Phased Pipeline Design

The system executes in 8 sequential phases with checkpoint-based resumability:

1. **Phase 0 - Validation:** JSON schema validation, credential management, user profile consolidation
2. **Phase 1 - University Discovery:** Scrape department structure, filter relevant departments via LLM
3. **Phase 2 - Professor Filtering:** Discover professors, filter by research field with confidence scoring
4. **Phase 3 - Lab Intelligence:** Scrape lab websites, check Archive.org history, extract contact info
5. **Phase 5 - Publications:** Retrieve publications via paper-search-mcp, analyze abstracts, assign journal scores
6. **Phase 6 - LinkedIn Integration:** Match lab members via mcp-linkedin, detect graduating PhDs
7. **Phase 7 - Analysis:** Authorship pattern analysis, collaboration network identification, fitness scoring
8. **Phase 8 - Reports:** Generate Overview.md with comparison matrix and detailed lab reports

**Parallel Execution:** Phase 4 (Lab Websites) and Phase 5A (PI Publications) run concurrently for 15-20% timeline reduction. They converge before Phase 5B (Lab Member Publications).

### Agent Orchestration Pattern

**Hierarchical Coordinator with Batch Delegation:**
- CLI Coordinator agent manages phase progression
- Each phase uses Python modules that call Claude Agent SDK's `ClaudeSDKClient` class
- Parallel execution achieved using Python's `asyncio.gather()` with Semaphore for concurrency control
- Agents have isolated contexts; state passes via JSONL checkpoints
- Batch-level checkpointing enables mid-phase resume

### Key Architectural Patterns

**Checkpoint/Restore:**
- JSONL format for efficient batch processing
- Checkpoints stored in `checkpoints/phase-N-batch-M.jsonl`
- Resume logic: Load completed batches, restart from first incomplete batch

**Graceful Degradation:**
- Missing data flagged but doesn't block pipeline
- Example: Missing lab website → infer members from co-authorship → flag as "inferred"
- Data quality flags propagate to final reports with ⚠️ markers

**Web Scraping Strategy:**
- Tiered fallback: Claude Agent SDK built-in tools → Playwright → Skip with flag
- Built-in tools for public pages (faster, simpler)
- Playwright for authenticated pages and JS-heavy sites

**MCP Integration:**
- `paper-search-mcp` for publication retrieval
- `mcp-linkedin` for LinkedIn profile matching (handles auth and rate limiting)
- No application-level queue needed for LinkedIn access

## Critical Coding Standards

### Mandatory Rules

1. **Never use `print()` for logging** - Always use `src/utils/logger.py` structured logger
2. **All LLM calls via `src/utils/llm_helpers.py`** - No inline prompts scattered in code
3. **Checkpoint saves must be atomic** - Use `src/utils/checkpoint_manager.py`, never write JSONL directly
4. **Always type hint function signatures** - `mypy` must pass without errors
5. **Web scraping: built-in tools first** - Pattern: `try built-in → except → Playwright → except → flag and skip`
6. **LinkedIn access only via MCP** - Never custom LinkedIn scraping; use `mcp-linkedin` tools
7. **Pydantic models for all data** - No raw dicts for domain entities
8. **Optional fields must have None defaults** - `field: Optional[str] = None`
9. **Data quality flags mandatory** - When inferring or skipping, append to `data_quality_flags` list
10. **No hardcoded batch sizes** - Use `system_params.json` config values
11. **Async/await for I/O** - Web scraping, file I/O, MCP calls must use `async def` and `await`
12. **Correlation IDs in all logs** - Always bind `correlation_id` to logger context via `get_logger()`
13. **Use CredentialManager for secrets** - Never hardcode API keys; use `src/utils/credential_manager.py`
14. **Progress bars via ProgressTracker** - Use `src/utils/progress_tracker.py` for consistent UX
15. **MCP config via mcp_client** - Use `src/utils/mcp_client.get_mcp_server_config()` for Claude Agent SDK

### Naming Conventions

- Classes: `PascalCase` (e.g., `UniversityDiscoveryAgent`)
- Functions: `snake_case` (e.g., `discover_structure()`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES = 3`)
- Private methods: `_leading_underscore` (e.g., `_validate_credentials()`)
- Files: `snake_case` (e.g., `university_discovery.py`)
- Tests: `test_<module>.py` (e.g., `test_checkpoint_manager.py`)

## Module Organization

```
src/
├── agents/          # Phase-specific agent implementations
│   ├── profile_consolidator.py        # ✅ User profile consolidation (Story 1.7)
│   └── university_discovery.py        # ✅ University structure discovery with error handling (Story 2.4)
├── models/          # Pydantic data models
│   ├── profile.py                     # ✅ ConsolidatedProfile model (Story 1.7)
│   └── department.py                  # ✅ Department model with data quality flags (Story 2.4)
├── schemas/         # JSON schemas for configuration validation
│   ├── system_params_schema.json      # Batch sizes, rate limits, timeouts
│   ├── user_profile_schema.json       # Research interests, filters
│   └── university_config_schema.json  # University-specific scraping config
├── utils/           # Shared utilities (✅ Epic 1 Story 1.4 complete)
│   ├── checkpoint_manager.py          # ✅ JSONL checkpoint persistence
│   ├── credential_manager.py          # ✅ Secure credential storage with CLI prompts (Story 1.3)
│   ├── llm_helpers.py                 # ✅ Centralized LLM interaction functions
│   ├── logger.py                      # ✅ Structured logging with correlation IDs
│   ├── mcp_client.py                  # ✅ MCP server configuration helper (Story 1.5)
│   ├── progress_tracker.py            # ✅ Rich-based progress bars
│   └── validator.py                   # ✅ JSON schema validation (Story 1.2)
└── __init__.py

tests/
├── unit/            # Unit tests (70% coverage minimum enforced by pytest.ini)
│   └── test_error_handling_structure.py  # ✅ Story 2.4 tests (36 tests, 94% coverage)
├── integration/     # Integration tests (MCP, web scraping, I/O)
├── fixtures/        # Test data (sample configs, mock HTML)
└── __init__.py

docs/
├── architecture/    # Detailed architecture documentation
├── prd/             # Product requirements
├── qa/
│   └── gates/       # Quality gate definitions (YAML)
└── stories/         # User stories with implementation details

config/
├── system_params.example.json       # Template for system configuration
├── user_profile.example.json        # Template for user research profile
└── university_config.example.json   # Template for university scraping config
# User copies .example.json → .json and customizes (git-ignored)

checkpoints/
└── (Runtime checkpoint files - not in repo)

output/
└── (Generated reports - not in repo)
```

## Component Interactions

### Data Flow

```
Config Files → Validator → User Profile
              ↓
University Discovery → Department List (checkpoint)
              ↓
Professor Filtering → Filtered Professors (batch checkpoints)
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
Lab Websites      PI Publications (parallel)
    ↓                   ↓
    └─────────┬─────────┘ (convergence)
              ↓
    Member Publications
              ↓
    LinkedIn Matching
              ↓
    Authorship Analysis
              ↓
    Fitness Scoring
              ↓
    Report Generation → Markdown Reports
```

### Checkpoint Manager Usage

All phase components must use the Checkpoint Manager for state persistence:

```python
# Save batch checkpoint
checkpoint_manager.save_batch(
    phase="phase-2-professors",
    batch_id=3,
    data=[professor1, professor2, ...]  # List of Pydantic models
)

# Load completed batches
batches = checkpoint_manager.load_batches(phase="phase-2-professors")

# Get resume point
resume_batch_id = checkpoint_manager.get_resume_point(phase="phase-2-professors")

# Mark phase complete
checkpoint_manager.mark_phase_complete(phase="phase-2-professors")
```

### LLM Interaction Pattern

All LLM calls must go through `src/utils/llm_helpers.py`:

```python
from src.utils.llm_helpers import analyze_relevance, filter_research_field

# Department filtering
is_relevant = await analyze_relevance(
    department_description,
    user_profile.research_interests
)

# Professor filtering with confidence
result = await filter_research_field(
    professor_bio,
    user_profile,
    confidence_threshold=70.0
)
```

### Credential Manager Usage

Use `CredentialManager` for secure credential storage with CLI prompts:

```python
from src.utils.credential_manager import CredentialManager

# Initialize (loads from .env or creates from .env.example)
cred_manager = CredentialManager()

# Get credential (prompts if missing, saves to .env)
api_key = cred_manager.get_credential(
    key="ANTHROPIC_API_KEY",
    prompt_message="Enter your Anthropic API key",
    is_secret=True  # Hides input
)

# Check if credential exists without prompting
if cred_manager.has_credential("LINKEDIN_EMAIL"):
    email = cred_manager.get_credential("LINKEDIN_EMAIL", prompt_if_missing=False)
```

### Logger Usage

Use structured logging with correlation IDs for multi-agent tracing:

```python
from src.utils.logger import get_logger

# Get logger with context binding
logger = get_logger(
    correlation_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    phase="professor_filter",
    component="professor_filter_agent"
)

# Log with additional context (correlation_id automatically included)
logger.info("Starting professor filtering", total_professors=100)
logger.warning("Low confidence match", professor_name="Dr. Smith", confidence=68.5)
logger.error("LLM call failed", error="Timeout after 30s")

# Credentials are automatically masked in logs
logger.debug("Calling API", api_key="sk-ant-1234...")  # Logged as "***MASKED***"
```

### MCP Client Configuration

Configure MCP servers for Claude Agent SDK:

```python
from src.utils.mcp_client import get_mcp_server_config
from claude_agent_sdk import ClaudeAgentOptions

# Get MCP server configurations (loads LinkedIn credentials from .env)
mcp_config = get_mcp_server_config()

# Pass to Claude Agent SDK
options = ClaudeAgentOptions(mcp_servers=mcp_config)

# Available servers:
# - mcp_config["papers"] - paper-search-mcp for publication retrieval
# - mcp_config["linkedin"] - mcp-linkedin for profile matching
```

### Progress Tracker Usage

Display progress bars for long-running operations:

```python
from src.utils.progress_tracker import ProgressTracker

tracker = ProgressTracker()

# Start phase
tracker.start_phase("Phase 2: Professor Discovery", total_items=100)

# Update progress as work completes
tracker.update(completed=20)

# Show batch-level progress
tracker.update_batch(
    batch_num=3,
    total_batches=8,
    batch_desc="Processing professors 21-40"
)

# Complete phase
tracker.complete_phase()
```

## Testing Strategy

### Test Organization

- **Unit tests:** `tests/unit/` - 70% code coverage minimum enforced by `pytest.ini`
- **Integration tests:** `tests/integration/` - Test MCP servers, web scraping, file I/O
- **E2E tests:** Manual only - Full pipeline on real university data

**Test Markers (defined in pytest.ini):**
- `@pytest.mark.integration` - Integration tests with external dependencies
- `@pytest.mark.slow` - Network-dependent or large data processing tests
- `@pytest.mark.unit` - Unit tests (default, no marking needed)

**Pytest Configuration (`pytest.ini`):**
- Asyncio mode: Auto-detect async tests
- Coverage enforcement: 70% minimum (`--cov-fail-under=70`)
- Coverage reports: Terminal (missing lines) + HTML (`htmlcov/`)
- Strict markers: Prevents typos in test markers
- Test discovery: `tests/` path with `test_*.py` pattern

### Test Patterns

**AAA Pattern (Arrange-Act-Assert):**
```python
def test_filter_departments_empty_list(mocker):
    # Arrange
    mock_llm = mocker.patch('src.utils.llm_helpers.analyze_relevance')
    agent = UniversityDiscoveryAgent()

    # Act
    result = agent.filter_departments([], user_profile)

    # Assert
    assert result == []
    mock_llm.assert_not_called()
```

**Async Test Pattern:**
```python
@pytest.mark.asyncio
async def test_scrape_lab_website_success(mocker):
    # Arrange
    mock_fetch = mocker.patch('src.agents.lab_scraper.fetch_page')
    mock_fetch.return_value = "<html>...</html>"

    # Act
    result = await scrape_lab_website("https://example.edu/lab")

    # Assert
    assert result.contact_email is not None
```

**Test Coverage Requirements:**
- All public methods and functions
- Edge cases: empty inputs, None values, missing fields
- Error handling paths
- Mock LLM calls, web scraping, file I/O
- Async/await patterns

## Configuration System

### Configuration Files

The system uses three JSON configuration files in the `config/` directory:

**1. system_params.json** - System execution parameters
```json
{
  "batch_sizes": {
    "departments": 5,      // Parallel department processing batch size
    "professors": 20,      // Parallel professor filtering batch size
    "labs": 10            // Parallel lab analysis batch size
  },
  "rate_limits": {
    "archive_org": 30,    // Archive.org requests per minute
    "linkedin": 10,       // LinkedIn MCP requests per minute
    "paper_search": 20    // Paper search MCP requests per minute
  },
  "timeouts": {
    "web_scraping": 30,   // Web scraping timeout (seconds)
    "mcp_query": 60       // MCP query timeout (seconds)
  },
  "confidence_thresholds": {
    "professor_filter": 70.0,  // Min confidence for professor relevance
    "linkedin_match": 75.0     // Min confidence for LinkedIn matching
  },
  "publication_years": 3,  // Years of publication history to retrieve
  "log_level": "INFO"      // DEBUG, INFO, WARNING, ERROR, CRITICAL
}
```

**2. user_profile.json** - User research interests and filters
- Research interests, keywords, and field descriptions
- Preferred journal categories and publication filters
- Target university characteristics

**3. university_config.json** - University-specific scraping configuration
- University URL and department directory structure
- CSS selectors for scraping department pages
- Professor listing page patterns

### Schema Validation

All configuration files are validated against JSON schemas in `src/schemas/`:
- `system_params_schema.json` - Validates system parameters
- `user_profile_schema.json` - Validates user profile
- `university_config_schema.json` - Validates university config

Use the Validator utility to validate configurations:
```python
from src.utils.validator import Validator

validator = Validator(schema_dir="src/schemas/")
is_valid = validator.validate_config(
    config_file="config/system_params.json",
    schema_name="system_params_schema.json"
)
```

### Setup Instructions

1. Copy example files to create your configurations:
   ```bash
   cp config/system_params.example.json config/system_params.json
   cp config/user_profile.example.json config/user_profile.json
   cp config/university_config.example.json config/university_config.json
   ```

2. Edit `config/*.json` files with your settings (these are git-ignored)

3. Validate configurations before running:
   ```bash
   venv/Scripts/python.exe -m src.utils.validator --config config/
   ```

## Development Workflow

### When Adding New Features

1. **Read relevant story documents** - Check `docs/stories/` for implementation details
2. **Define Pydantic models** - Create data models in `src/models/`
3. **Implement core logic** - Add functionality to appropriate component
4. **Add LLM prompts to llm_helpers** - Centralize all LLM interactions
5. **Implement checkpoint logic** - Use Checkpoint Manager for state
6. **Write unit tests** - Maintain 70% coverage minimum
7. **Update type hints** - Ensure `mypy` passes
8. **Run linter** - `ruff check --fix`

### When Debugging Issues

1. **Check correlation IDs** - Use structured logs to trace execution
2. **Examine checkpoints** - JSONL files show exact state at failure
3. **Review data quality flags** - Identify inferred or missing data
4. **Test with small batches** - Reduce batch sizes in system_params.json for faster iteration
5. **Use verbose logging** - Set `log_level: "DEBUG"` in system_params.json

## Key Dependencies

### Core Framework
- **Python 3.11.7** - Exact version required
- **claude-agent-sdk 0.1.1** - Multi-agent orchestration framework
- **mcp 1.16.0** - Model Context Protocol integration
- **paper-search-mcp 0.1.3** - Academic publication retrieval MCP server

### Data & Validation
- **pydantic 2.11.10** - Data models with validation
- **jsonschema 4.25.1** - JSON schema validation
- **pandas 2.3.3** - CSV processing (SJR journal scores)
- **jsonlines 4.0.0** - JSONL checkpoint file processing

### Web Scraping & HTTP
- **playwright 1.55.0** - Browser automation fallback
- **httpx 0.28.1** - Async HTTP client
- **beautifulsoup4 4.14.2** - HTML parsing
- **waybackpy 3.0.6** - Archive.org Wayback Machine integration

### Utilities
- **structlog 25.4.0** - Structured logging with correlation IDs
- **python-dotenv 1.1.1** - Environment variable and credential management
- **rich 14.1.0** - CLI progress bars and formatting
- **aiolimiter 1.2.1** - Async rate limiting
- **tenacity 9.1.2** - Retry logic with exponential backoff

### Testing
- **pytest 8.4.2** - Test framework
- **pytest-asyncio 1.2.0** - Async test support
- **pytest-cov 7.0.0** - Coverage reporting (70% minimum enforced)
- **pytest-mock 3.15.1** - Mocking utilities
- **mypy 1.18.2** - Static type checking
- **ruff 0.13.3** - Fast Python linter

## Common Pitfalls

1. **Forgetting async/await** - All I/O operations must be async
2. **Writing JSONL directly** - Always use `checkpoint_manager.py`
3. **Hardcoding batch sizes** - Use `system_params.json` config values
4. **Missing data quality flags** - Flag all inferences and skipped data
5. **Inline LLM prompts** - Centralize in `llm_helpers.py`
6. **Using print() instead of logger** - Use `logger.py` structured logging
7. **Not type hinting** - `mypy` will fail
8. **Forgetting correlation IDs** - Pass to `get_logger()` for tracing
9. **Not testing edge cases** - Empty inputs, None values, missing fields
10. **Custom LinkedIn scraping** - Always use `mcp-linkedin` MCP server
11. **Hardcoding credentials** - Use `credential_manager.py` with `.env` storage
12. **Manual progress output** - Use `progress_tracker.py` for consistent UX
13. **Direct MCP server config** - Use `mcp_client.get_mcp_server_config()`
14. **Missing pytest markers** - Mark integration tests with `@pytest.mark.integration`
15. **Skipping coverage checks** - `pytest.ini` enforces 70% minimum

## Implementation Progress & Status

### Completed Stories ✅

**Epic 1: Foundation & Configuration Infrastructure (COMPLETE ✅ - all required stories done)**
- ✅ **Story 1.0** - Project Initialization
- ✅ **Story 1.1** - Core Dependency Installation
- ✅ **Story 1.2** - JSON Schema Validation (`src/utils/validator.py`)
- ✅ **Story 1.3** - Credential Management (`src/utils/credential_manager.py`)
- ✅ **Story 1.4** - Shared Utilities Implementation:
  - `src/utils/checkpoint_manager.py` - JSONL checkpoint persistence
  - `src/utils/llm_helpers.py` - Centralized LLM prompts with retry logic
  - `src/utils/progress_tracker.py` - Rich-based progress bars
  - `src/utils/logger.py` - Structured logging with correlation IDs
- ✅ **Story 1.5** - MCP Server Setup (`src/utils/mcp_client.py`)
- ✅ **Story 1.6** - Testing Infrastructure (pytest.ini, test structure)
- ✅ **Story 1.7** - User Profile Consolidation:
  - `src/models/profile.py` - ConsolidatedProfile Pydantic model
  - `src/agents/profile_consolidator.py` - Profile consolidation agent
- 🔶 **Story 1.8** - CI/CD Pipeline Setup (OPTIONAL - implemented, needs monitoring):
  - `.github/workflows/ci.yml` - 4-stage workflow (lint, type-check, unit-tests, integration-tests)
  - `tests/integration/conftest.py` - MCP mocking fixtures for CI environment
  - QA Score: 80/100 (concerns: needs monitoring for <10min execution time)
  - Status: Functional but requires post-deployment monitoring

**Epic 2: University Structure Discovery (IN PROGRESS 🚧)**
- ✅ **Story 2.4** - Error Handling for Missing Structure Data:
  - `src/models/department.py` - Department model with data quality flags
  - `src/agents/university_discovery.py` - University discovery with retry logic, graceful degradation, and error handling
  - `tests/unit/test_error_handling_structure.py` - 36 tests, 94% coverage
  - QA Score: 100/100 (production-ready, exemplary implementation)
- ⏳ **Story 2.1** - University Website Structure Discovery (may be partially in 2.4 implementation)
- ⏳ **Story 2.2** - Department Structure JSON Representation
- ⏳ **Story 2.3** - Department Relevance Filtering
- ⏳ **Story 2.5** - Batch Configuration for Department Processing

### Key Implementation Insights

**From Story 2.4 (Error Handling):**
- Department model includes `data_quality_flags` field for tracking issues
- UniversityDiscoveryAgent implements comprehensive error handling:
  - Retry logic using tenacity (exponential backoff, max 3 attempts)
  - Graceful degradation for missing data (placeholders, partial data)
  - Manual fallback configuration support (`departments_fallback.json`)
  - Structure gap report generation (`output/structure-gaps.md`)
  - Validation with 50% thresholds (blocks pipeline if <50% data)
- Data quality flags: `missing_url`, `missing_school`, `ambiguous_hierarchy`, `partial_metadata`, `inference_based`, `manual_entry`, `scraping_failed`

**From Epic 1 (Foundation):**
- All shared utilities follow consistent patterns (async/await, type hints, structured logging)
- LLM helpers centralize prompts: `DEPARTMENT_RELEVANCE_TEMPLATE`, `PROFESSOR_FILTER_TEMPLATE`, `LINKEDIN_MATCH_TEMPLATE`
- Checkpoint manager handles JSONL batch-level persistence with resume support
- CredentialManager prompts for missing credentials and saves to `.env`
- ConsolidatedProfile model includes LLM-generated `streamlined_interests` field

### Next Steps

**Immediate (Epic 2 Remaining Stories):**
1. Complete Story 2.1, 2.2, 2.3, 2.5 to finish university discovery phase
2. Verify checkpoint generation: `checkpoints/phase-1-relevant-departments.jsonl`
3. Integration test full Epic 2 workflow

**Following Epics:**
- **Epic 3** - Professor Discovery & Filtering (Stories 3.1-3.5)
- **Epic 4** - Lab Website Intelligence (Stories 4.1-4.5)
- **Epics 5 & 6** - Publications & LinkedIn (parallel execution)
- **Epic 7** - Fitness Scoring
- **Epic 8** - Report Generation

### Current Development Environment

**Working Components:**
- Validation (`src/utils/validator.py`)
- Credential management (`src/utils/credential_manager.py`)
- Checkpoint system (`src/utils/checkpoint_manager.py`)
- Structured logging (`src/utils/logger.py`)
- LLM helpers (`src/utils/llm_helpers.py`)
- Progress tracking (`src/utils/progress_tracker.py`)
- MCP client configuration (`src/utils/mcp_client.py`)
- Profile consolidation (`src/agents/profile_consolidator.py`)
- University discovery with error handling (`src/agents/university_discovery.py`)

**Test Coverage:**
- Story 2.4: 94% coverage (36 tests)
- All tests passing (183 total, 1 skipped)
- ruff linting: ✅ passing
- mypy type checking: ✅ passing

## Documentation References

- **Architecture details:** `docs/architecture/` (individual files) or `docs/architecture.md` (pre-shard consolidated version)
- **Product requirements:** `docs/prd/` (individual files) or `docs/prd.md` (pre-shard consolidated version)
- **User stories:** `docs/stories/`
- **Development handoff:** `docs/DEVELOPMENT-HANDOFF.md`
- **Architecture errata:** `docs/ARCHITECTURE-ERRATA.md`

**Note:** The `architecture.md` and `prd.md` files are pre-sharded consolidated versions. The `docs/architecture/` and `docs/prd/` directories contain the same content split into focused topic files for easier navigation.
- use shard epics and architecture, meaning use the docs/prd/ over prd.md. if updating shard documents, bright these modifications in shard documents back into the un-shard docs