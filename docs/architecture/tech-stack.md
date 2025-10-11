# Tech Stack

This section defines the **DEFINITIVE technology selections** for the Lab Finder project. All implementation must adhere to these specific versions and tools.

## Cloud Infrastructure

**Provider:** Not applicable

**Rationale:** Local execution only (NFR9). No cloud deployment or managed services required.

**Storage:**
- **Local Filesystem** - All data persistence via local directories
- **Checkpoint Directory:** `./checkpoints/` - JSONL batch checkpoints
- **Output Directory:** `./output/` - Markdown reports and final deliverables
- **Configuration Directory:** `./config/` - JSON configuration files
- **Logs Directory:** `./logs/` - Structured JSON logs

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|----------|-----------|---------|---------|-----------|
| **Language** | Python | 3.11.7 | Primary development language | Modern async/await, pattern matching, LTS release with performance improvements |
| **Framework** | Claude Agent SDK | 0.1.1 | Multi-agent orchestration framework | Core framework per NFR1; provides FREE LLM access via two modes: `query()` (stateless) and `ClaudeSDKClient()` (stateful) |
| **SDK Mode 1** | `ClaudeSDKClient` | SDK built-in | One-off stateless LLM calls | PRIMARY MODE: Used for all text analysis (dept filtering, abstract scoring) and web scraping (university discovery). Stateless, no conversation memory. Configured with isolated context to prevent codebase injection. |
| **SDK Mode 2** | `ClaudeSDKClient()` | SDK built-in | Multi-turn conversations with memory | NOT CURRENTLY USED: For complex iterative workflows. May be added in future phases. |
| **Built-in Web Fetch** | WebFetch | built-in | Web page scraping | Primary web scraping; handles static HTML |
| **Built-in Web Search** | WebSearch | built-in | Web search | Augments discovery with targeted searches |
| **Browser Automation** | Playwright | 1.55.0 | Advanced web scraping | ~~Required for JS-heavy sites~~ **Accessed via Puppeteer MCP server (@modelcontextprotocol/server-puppeteer)**. Note: Direct Playwright library usage deprecated. Use Puppeteer MCP for equivalent functionality (Chrome-only acceptable for university sites). |
| **MCP Client** | mcp (Model Context Protocol) | 1.16.0 | MCP server communication | Connects to paper-search-mcp and mcp-linkedin servers (NFR6) |
| **HTTP Client** | httpx | 0.28.1 | Async HTTP requests | Archive.org API, web scraping fallback; native async support |
| **Archive.org Client** | waybackpy | 3.0.6 | Wayback Machine API wrapper | Website history snapshots (FR14); simplifies Archive.org CDX API interaction |
| **Template Engine** | Jinja2 | 3.1.5 | LLM prompt template management | Externalizes prompt templates from code for version control, easier iteration, and non-developer editing; supports template inheritance and custom filters |
| **Schema Validation** | jsonschema | 4.25.1 | JSON configuration validation | Validates user configs against schemas (FR1); industry standard |
| **Configuration** | python-dotenv | 1.1.1 | Environment variable management | Credential loading; separates secrets from code (FR2-FR3) |
| **Logging** | structlog | 25.4.0 | Structured logging framework | Correlation IDs, agent context, JSON output for multi-agent tracing (NFR17) |
| **Progress Indicators** | rich | 14.1.0 | CLI progress bars and formatting | User-facing progress tracking (NFR14); markdown preview capabilities |
| **Testing Framework** | pytest | 8.4.2 | Test runner and framework | Industry standard; excellent async support, fixtures, parametrization |
| **Test Coverage** | pytest-cov | 7.0.0 | Code coverage reporting | Tracks test coverage metrics |
| **Async Testing** | pytest-asyncio | 1.2.0 | Async test support | Handles async/await test cases for agent orchestration |
| **Mocking** | pytest-mock | 3.15.1 | Test mocking and stubbing | Mocks external services (LinkedIn, Archive.org, paper-search-mcp) |
| **Linting** | ruff | 0.13.3 | Fast Python linter | Replaces flake8, black, isort; extremely fast, comprehensive rules |
| **Type Checking** | mypy | 1.18.2 | Static type analysis | Enforces type hints; catches type errors before runtime |
| **Data Validation** | pydantic | 2.11.10 | Runtime data validation | Type-safe configuration models; complements jsonschema |
| **Date/Time Utilities** | python-dateutil | 2.9.0.post0 | Date parsing and manipulation | PhD graduation timeline calculations (FR21) |
| **Retry Logic** | tenacity | 9.1.2 | Configurable retry decorator | Web scraping error handling (NFR13); exponential backoff |
| **Rate Limiting** | aiolimiter | 1.2.1 | Async rate limiter | Per-source rate limiting (NFR11); prevents blocking |
| **CSV Processing** | pandas | 2.3.3 | Data manipulation for SJR database | Journal reputation data loading (FR17); CSV parsing |
| **JSONL Handling** | jsonlines | 4.0.0 | JSONL file read/write | Checkpoint file format; streaming support |
| **Environment** | virtualenv / venv | built-in | Virtual environment isolation | Dependency isolation; reproducible builds |
| **Package Management** | pip | 23.3+ | Dependency installation | Standard Python package manager |
| **Dependency Lock** | pip-tools | 7.5.1 | Requirements pinning | Generates requirements.txt from requirements.in; reproducible installs |

## Key Technology Decisions

**Claude Agent SDK `ClaudeSDKClient` with Isolated Context**
- Rationale: All Lab Finder operations are stateless one-off tasks; no conversation memory needed
- `ClaudeSDKClient` configured with `allowed_tools=[]`, `system_prompt`, and `setting_sources=None` for proper context isolation
- Standalone `query()` function found to inject unwanted codebase context (git status, file system) causing analysis failures
- Solution verified: `ClaudeSDKClient` class with proper configuration prevents context pollution
- Cost: Still FREE; no paid Anthropic API used anywhere in codebase

**Python 3.11.7** (not 3.12+)
- Rationale: Balance of modern features and ecosystem stability; Claude Agent SDK compatibility confirmed

**jsonschema over pydantic for validation** (complementary use)
- Rationale: jsonschema for JSON file validation (FR1 explicitly requires JSON Schema); pydantic for runtime Python object validation

**httpx over requests**
- Rationale: Native async/await support; Claude Agent SDK likely uses async patterns; HTTP/2 support for faster concurrent requests

**structlog over logging/loguru**
- Rationale: Multi-agent context requires structured logging with correlation IDs; easier to track agent hierarchy in JSON logs

**rich over tqdm**
- Rationale: Single library for progress bars, formatted console output, and markdown rendering; better CLI aesthetics

**Scimago SJR CSV (static download)**
- Rationale: Free, comprehensive, no API limits; annual updates sufficient for one-off analysis

**ruff over black + flake8 + isort**
- Rationale: 10-100x faster; single tool replaces three; actively maintained by Astral (creators of uv)

**pytest ecosystem**
- Rationale: Standard for Python testing; excellent plugin ecosystem (asyncio, cov, mock); better DX than unittest

**mcp-linkedin over Playwright**
- Rationale: MCP server handles LinkedIn authentication and rate limiting; eliminates queue complexity; allows parallel LinkedIn access

**waybackpy for Archive.org**
- Rationale: Simplifies Wayback Machine CDX API interaction; handles snapshot queries and date parsing; complements httpx for Archive.org operations

**Jinja2 for prompt template management**
- Rationale: Externalizes 155+ lines of hardcoded LLM prompt strings to separate `.j2` files; enables version-controlled prompt iteration without code changes; supports template inheritance for reusable components; allows non-developers to edit prompts; industry-standard templating engine with extensive documentation
- Implementation: All prompts stored in `prompts/` directory, loaded via `src/utils/prompt_loader.py` with singleton pattern; custom filters for text processing (e.g., strip_markdown)

---

**CRITICAL NOTES:**

⚠️ **Claude Agent SDK Implementation:** Lab Finder uses `ClaudeSDKClient` class (Mode 1 - stateless) with isolated context configuration for ALL operations. Key config: `allowed_tools=[]`, `system_prompt` override, `setting_sources=None` to prevent codebase context injection. Do NOT use paid Anthropic API `messages.create()` or standalone `query()` function. All SDK modes are FREE.

⚠️ **Claude Agent SDK Version:** Pinned to version 0.1.1 as installed in Story 1.1. Do not update without architectural review.

⚠️ **MCP Version:** Pinned to version 1.16.0 as installed in Story 1.1. Verify compatibility when configuring MCP servers (paper-search-mcp, mcp-linkedin).

⚠️ **MCP Servers Required:**

| MCP Server | Package | Command | Purpose | Tools Available | Used In |
|-----------|---------|---------|---------|----------------|---------|
| puppeteer | @modelcontextprotocol/server-puppeteer | npx | Browser automation for JS-heavy sites | navigate, screenshot, click, fill, evaluate (JavaScript execution) | Epic 3, 4 |
| papers | paper-search-mcp | python -m paper_search_mcp.server | Publication retrieval | search_papers, get_paper_details | Epic 5 |
| linkedin | mcp-linkedin (adhikasp) | uvx --from git+https://github.com/adhikasp/mcp-linkedin | LinkedIn profile access | get_profile, search_profiles | Epic 6 |

**Configuration:** All MCP servers configured via `claude/.mcp.json` with `{"type": "stdio", "command": "...", "args": [...]}`

⚠️ **Version Pinning Strategy:** All versions listed are exact pins (not ranges). This ensures reproducible builds critical for one-off execution tool reliability.

⚠️ **Dependency Updates:** Do NOT update dependencies mid-implementation without architectural review. Version drift can break agent orchestration patterns.

---

## Web Scraping Tool Selection

**Multi-Stage Pattern with Puppeteer MCP:**

1. **Stage 1: ClaudeSDKClient + WebFetch**
   - Extract data using built-in WebFetch tool
   - If successful, proceed to Stage 2

2. **Stage 2: Sufficiency Evaluation**
   - Separate LLM prompt evaluates data completeness
   - Checks all required_fields present
   - If sufficient → Return data
   - If insufficient → Proceed to Stage 3

3. **Stage 3: ClaudeSDKClient + Puppeteer MCP**
   - Use mcp__puppeteer__navigate and mcp__puppeteer__evaluate
   - Execute JavaScript for data extraction
   - Handles JS-rendered content
   - Proceed to Stage 4

4. **Stage 4: Re-evaluate Sufficiency**
   - Same evaluation as Stage 2
   - If sufficient → Return data
   - If insufficient and attempts < 3 → Loop back to Stage 3
   - If max attempts reached → Return partial data + missing_fields flag

**Data Quality Flags:**
- `insufficient_webfetch`: WebFetch didn't extract all required fields
- `puppeteer_mcp_used`: Escalated to Puppeteer MCP fallback
- `sufficiency_evaluation_failed`: Could not determine completeness

**Tool Usage Examples:**
- Static department directory → WebFetch (Stage 1) ✓
- JS-rendered professor listing → WebFetch → Puppeteer MCP (Stages 1-3) ✓
- LinkedIn profile → mcp-linkedin MCP server (not web scraping) ✓
- Archive.org snapshots → WebFetch (Stage 1) ✓

---

## SDK Working Directory Configuration

**Pattern:** Isolated `claude/` directory for SDK context

**Directory Structure:**
```
C:\Users\yifei\Documents\Research/
├── claude/                          # SDK working directory (isolated)
│   ├── .mcp.json                   # MCP server configuration
│   └── .claude/                    # SDK configuration directory
│       └── settings.json           # SDK settings
├── src/                            # Lab Finder application code
│   └── ...
```

**Why Isolated:**
- Keeps SDK configuration separate from Lab Finder codebase
- `.mcp.json` doesn't pollute project root
- Clear separation of concerns: `claude/` = SDK, `src/` = application

**Usage in Code:**
```python
from claude_agent_sdk import ClaudeAgentOptions
from pathlib import Path

options = ClaudeAgentOptions(
    cwd=Path(__file__).parent.parent / "claude",  # Points to claude/ directory
    setting_sources=["project"],                   # Loads .mcp.json
    allowed_tools=["mcp__puppeteer__navigate", "mcp__puppeteer__evaluate"]
)
```
