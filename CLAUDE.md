# CLAUDE.md

Project guidance for Claude Code when working with this repository.

## Claude Agent SDK Integration

**FREE SDK Usage:** All LLM interactions use **Claude Agent SDK** `ClaudeSDKClient` class (stateless mode) with isolated context configuration.

**Critical Configuration Pattern:**
```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

options = ClaudeAgentOptions(
    max_turns=1,              # Stateless one-shot
    allowed_tools=[],         # No file access
    system_prompt="You are an expert text analyst...",
    setting_sources=None      # CRITICAL: Prevents codebase context injection
)

async with ClaudeSDKClient(options=options) as client:
    await client.query(prompt)
    async for message in client.receive_response():
        # Process response...
```

**Bug Fixed (2025-10-07):** Standalone `query()` function injected unwanted codebase context. Always use `ClaudeSDKClient` class.

**Cost:** FREE (no paid Anthropic API). Do NOT use `anthropic.messages.create()` anywhere.

## Project Overview

**Lab Finder:** Python-based multi-agent research lab discovery system. Automates finding, analyzing, and ranking university research labs.

**Architecture:** Monolithic multi-agent pipeline with 8 phases, checkpoint-based resumability.

**Status:** Epic 1 complete ✅ | Epic 2 complete ✅ | Last updated 2025-10-08

## Quick Reference Commands

### Development Setup
```bash
# Windows
py -3.11 -m venv venv && venv\Scripts\activate

# macOS/Linux
python3.11 -m venv venv && source venv/bin/activate

# Install
pip-compile requirements.in && pip install -r requirements.txt
playwright install chromium
```

### Testing
```bash
pytest tests/ -v                          # All tests (70% coverage minimum)
pytest tests/unit/test_validator.py -v    # Specific file
pytest tests/integration/ -v -m integration  # Integration only
```

### Code Quality
```bash
ruff check src/ tests/ --fix              # Lint + auto-fix
mypy src/                                 # Type check
ruff check src/ tests/ && mypy src/       # Both
```

### Config Management
```bash
# Copy examples, edit, then validate
cp config/*.example.json config/
venv/Scripts/python.exe -m src.utils.validator --config config/
```

## Architecture Quick Reference

**Full details:** See `docs/architecture/` (sharded docs - use these over `architecture.md`)

**Pipeline Phases:** Validation → University Discovery → Professor Filtering → Lab Intelligence (parallel) + Publications (parallel) → LinkedIn → Analysis → Reports

**Parallel Execution:** Phase 4 (Lab Websites) + Phase 5A (PI Publications) run concurrently for 15-20% timeline reduction.

**Key Patterns:**
- **Checkpoint/Restore:** JSONL batch-level persistence (`checkpoints/phase-N-batch-M.jsonl`)
- **Graceful Degradation:** Missing data flagged, pipeline continues
- **Web Scraping:** Built-in tools → Playwright → Skip with flag
- **MCP Integration:** `paper-search-mcp`, `mcp-linkedin`

**Source Tree:** See `docs/architecture/source-tree.md`
**Tech Stack:** See `docs/architecture/tech-stack.md` (Python 3.11.7, Claude Agent SDK, Playwright, MCP)

## Critical Coding Standards

**Mandatory Rules (Full list:** `docs/architecture/coding-standards.md`**)**

1. **Never use `print()`** - Use `src/utils/logger.py` structured logger
2. **All LLM calls via `src/utils/llm_helpers.py`** - No inline prompts
3. **Checkpoint saves atomic** - Use `checkpoint_manager.py`, never write JSONL directly
4. **Always type hint** - `mypy` must pass
5. **Web scraping:** Built-in tools → Playwright → Flag and skip
6. **LinkedIn via MCP** - Use `mcp-linkedin`, never custom scraping
7. **Pydantic models for all data** - No raw dicts
8. **Optional fields:** `field: Optional[str] = None`
9. **Data quality flags mandatory** - Append to `data_quality_flags` list
10. **No hardcoded batch sizes** - Use `system_params.json`
11. **Async/await for I/O** - Web scraping, file I/O, MCP calls
12. **Correlation IDs** - Bind to logger via `get_logger()`
13. **CredentialManager for secrets** - Use `credential_manager.py`
14. **Progress via ProgressTracker** - Use `progress_tracker.py`
15. **MCP config via mcp_client** - Use `get_mcp_server_config()`

**Naming:** Classes=`PascalCase`, Functions=`snake_case`, Constants=`UPPER_SNAKE_CASE`, Private=`_leading_underscore`, Tests=`test_<module>.py`

## Essential Utilities Usage

### Checkpoint Manager
```python
# Save batch
checkpoint_manager.save_batch(phase="phase-2-professors", batch_id=3, data=[...])

# Load batches
batches = checkpoint_manager.load_batches(phase="phase-2-professors")

# Resume point
resume_batch_id = checkpoint_manager.get_resume_point(phase="phase-2-professors")
```

### LLM Helpers
```python
from src.utils.llm_helpers import analyze_relevance, filter_research_field

# Department filtering
is_relevant = await analyze_relevance(dept_desc, user_profile.research_interests)

# Professor filtering with confidence
result = await filter_research_field(prof_bio, user_profile, confidence_threshold=70.0)
```

### Structured Logging
```python
from src.utils.logger import get_logger

logger = get_logger(correlation_id="...", phase="...", component="...")
logger.info("Starting filtering", total_professors=100)
logger.warning("Low confidence", professor_name="Dr. Smith", confidence=68.5)
# Credentials auto-masked
```

### Credential Manager
```python
from src.utils.credential_manager import CredentialManager

cred_manager = CredentialManager()
api_key = cred_manager.get_credential("ANTHROPIC_API_KEY",
                                       prompt_message="Enter API key",
                                       is_secret=True)
```

### MCP Configuration
```python
from src.utils.mcp_client import get_mcp_server_config
from claude_agent_sdk import ClaudeAgentOptions

mcp_config = get_mcp_server_config()  # Loads LinkedIn creds from .env
options = ClaudeAgentOptions(mcp_servers=mcp_config)
# Available: mcp_config["papers"], mcp_config["linkedin"]
```

### Progress Tracker
```python
from src.utils.progress_tracker import ProgressTracker

tracker = ProgressTracker()
tracker.start_phase("Phase 2: Professor Discovery", total_items=100)
tracker.update(completed=20)
tracker.update_batch(batch_num=3, total_batches=8, batch_desc="Professors 21-40")
tracker.complete_phase()
```

## Testing Strategy

**Coverage:** 70% minimum enforced by `pytest.ini`
**Full details:** `docs/architecture/test-strategy-and-standards.md`

**Test Markers:**
- `@pytest.mark.integration` - External dependencies
- `@pytest.mark.slow` - Network/large data tests
- `@pytest.mark.unit` - Unit tests (default)

**AAA Pattern Example:**
```python
def test_filter_departments_empty(mocker):
    # Arrange
    mock_llm = mocker.patch('src.utils.llm_helpers.analyze_relevance')
    agent = UniversityDiscoveryAgent()
    # Act
    result = agent.filter_departments([], user_profile)
    # Assert
    assert result == []
    mock_llm.assert_not_called()
```

**Coverage Requirements:** All public methods, edge cases, error paths, mocked I/O, async patterns.

## Configuration System

**3 JSON config files in `config/`:**

1. **system_params.json** - Batch sizes, rate limits, timeouts, confidence thresholds, log level
2. **user_profile.json** - Research interests, journal filters, university preferences
3. **university_config.json** - URLs, CSS selectors, professor listing patterns

**Schemas:** `src/schemas/*_schema.json` - Validated via `Validator` utility

**Setup:**
```bash
cp config/system_params.example.json config/system_params.json
# Edit config/*.json
venv/Scripts/python.exe -m src.utils.validator --config config/
```

## Development Workflow

### Adding Features
1. Read `docs/stories/` for implementation details
2. Define Pydantic models in `src/models/`
3. Implement core logic in appropriate component
4. Add LLM prompts to `llm_helpers.py`
5. Implement checkpoint logic via Checkpoint Manager
6. Write unit tests (70% coverage minimum)
7. Update type hints (ensure `mypy` passes)
8. Run `ruff check --fix`

### Debugging
1. Check correlation IDs in structured logs
2. Examine checkpoint JSONL files
3. Review data quality flags
4. Reduce batch sizes in `system_params.json`
5. Set `log_level: "DEBUG"`

## Common Pitfalls

1. **Forgetting async/await** - All I/O must be async
2. **Writing JSONL directly** - Use `checkpoint_manager.py`
3. **Hardcoding batch sizes** - Use `system_params.json`
4. **Missing data quality flags** - Flag all inferences/skips
5. **Inline LLM prompts** - Centralize in `llm_helpers.py`
6. **Using `print()`** - Use `logger.py`
7. **No type hints** - `mypy` will fail
8. **Forgetting correlation IDs** - Pass to `get_logger()`
9. **Not testing edge cases** - Empty inputs, None, missing fields
10. **Custom LinkedIn scraping** - Use `mcp-linkedin`
11. **Hardcoding credentials** - Use `credential_manager.py`
12. **Manual progress output** - Use `progress_tracker.py`
13. **Missing pytest markers** - Mark integration tests
14. **Skipping coverage checks** - 70% enforced

## Implementation Status

### Completed ✅
**Epic 1: Foundation (COMPLETE)**
- Stories 1.0-1.7 complete (validation, credentials, utilities, MCP setup, profile consolidation)
- Story 1.8 (CI/CD) - 80/100 QA score, needs monitoring

**Epic 2: University Discovery (COMPLETE)**
- Story 2.1 complete - University structure discovery (100/100 QA score)
- Story 2.2 complete - Department structure JSON (QA approved)
- Story 2.3 complete - Department relevance filtering (98/100 QA score)
- Story 2.4 complete - Error handling (100/100 QA score)
- Story 2.5 complete - Batch configuration

**Epic 3: Professor Discovery (COMPLETE)**
- Story 3.1a complete - Professor model + basic discovery (100/100 QA score) ✅
- Story 3.1b complete - Parallel processing + batch coordination (90/100 QA score) ✅
- Story 3.1c complete - Deduplication + rate limiting + checkpointing (95/100 QA score) ✅
- Story 3.2 complete - LLM-based professor filtering (95/100 QA score) ✅
- Story 3.3 complete - Confidence scoring (95/100 QA score) ✅
- Story 3.4 complete - Filtered professor logging (95/100 QA score) ✅
- Story 3.5 complete - Batch processing for professor analysis (100/100 QA score) ✅

**Epic 4: Lab Intelligence (IN PROGRESS)**
- Story 4.1 complete - Lab website discovery & scraping (95/100 QA score) ✅

### Key Insights

**Epic 3 (Story 3.1c):**
- Deduplication: LLM-based fuzzy name matching with exact match pre-filtering (reduces LLM calls by ~70%)
- Dual threshold: Requires BOTH `decision == "yes"` AND `confidence >= 90` to confirm duplicates
- Rate limiting: DomainRateLimiter class with per-domain AsyncLimiter instances (1 req/sec default)
- Merge strategy: Prefers more complete records, combines data_quality_flags
- Orchestrator: `discover_and_save_professors()` provides complete workflow (parallel discovery → deduplication → checkpoint save)
- Performance scaling: Documented thresholds at 50, 200, 500+ professors for optimization strategies
- Checkpoint: Single batch (`phase-2-professors-batch-1.jsonl`) for consolidated professor list
- Testing: 7 comprehensive tests including critical edge case (high-confidence "no" match)
- QA score: 95/100 - production-ready code quality

**Epic 3 (Story 3.1b):**
- Parallel processing: `discover_professors_parallel()` using asyncio.gather() with Semaphore concurrency control
- Hierarchical correlation IDs: `prof-discovery-coordinator`, `prof-disc-{dept.id}-{uuid}`
- Progress tracking: Integrated ProgressTracker with real-time department processing updates
- Error handling: Graceful degradation - failed departments don't block overall processing
- Concurrency control: Configurable `max_concurrent` parameter with Semaphore enforcement
- Testing: 7 new tests covering parallel execution, semaphore limits, progress tracking, error handling, edge cases
- Key improvement: Progress tracking in finally block for reliability (QA refactoring)

**Epic 3 (Story 3.3):**
- Confidence scoring: Robust validation handling 7+ edge cases (floats, strings, booleans, negatives, out-of-range, null, malformed)
- Threshold configuration: FilteringConfig with Pydantic validation ensures 0 < low < high <= 100
- Borderline reporting: `generate_borderline_report()` creates actionable review report with override recommendations
- Statistics: `calculate_confidence_stats()` with quality assessment (warns when >30% low-confidence)
- Manual overrides: Audit trail with timestamp, original confidence, original decision for transparency
- Enhanced LLM prompt: Requests `key_factors` and `confidence_explanation` for interpretability
- Data quality flags: `low_confidence_filter`, `llm_response_error`, `manual_override`, `confidence_out_of_range`
- Output artifacts: `output/borderline-professors.md`, `output/filter-confidence-stats.json`
- Testing: 32 comprehensive tests (100% AC coverage), ruff ✅, mypy ✅
- QA score: 95/100 - exceptional quality, production-ready

**Epic 3 (Story 3.4):**
- Transparency reporting: `generate_filter_report()` creates comprehensive filtered-professors.md with executive summary, department statistics, excluded/included professors
- Filter decision logging: `log_filter_decision()` logs all filtering decisions to structlog with full context
- Statistics calculation: `calculate_filter_statistics()` with edge case handling (empty list, all included/excluded)
- Manual additions: `load_manual_additions()` + `apply_manual_additions()` enables user overrides with checkpoint saving
- Report structure: Executive summary → Department breakdown → Excluded professors (by confidence) → Included professors → Detailed reasoning → Override instructions
- Cross-referencing: Links to borderline-professors.md for low-confidence decisions requiring review
- Data quality flag: Added `manual_addition` to PROFESSOR_DATA_QUALITY_FLAGS
- UTF-8 encoding: Applied throughout for Windows cross-platform compatibility
- Testing: 17 comprehensive tests (100% AC coverage), all edge cases covered, ruff ✅, mypy ✅
- QA score: 95/100 - production-ready, excellent code quality

**Epic 4 (Story 4.1):**
- Lab website discovery: Discovers lab URLs from professor records with defensive validation
- Web scraping: ClaudeSDKClient with WebFetch tool for content extraction, Playwright fallback for JS-heavy sites
- Content extraction: Extracts description, research focus, news/updates, last updated date using BeautifulSoup
- Lab model: Pydantic model with SHA256 ID generation (professor_id:lab_name), all fields typed and validated
- Graceful degradation: Missing websites don't block processing, creates minimal Lab record with "no_website" flag
- Checkpoint resumability: Batch-based checkpointing at phase-4-labs-batch-N.jsonl
- Progress tracking: Integrated ProgressTracker with two-level updates (batch + item)
- Data quality tracking: Flags for no_website, scraping_failed, playwright_fallback, missing_description, missing_research_focus, missing_news, missing_last_updated
- Batch processing: Configurable batch sizes (default: 10 labs), resume from last completed batch
- Error handling: Retry logic (3 attempts, exponential backoff 1-10s), 30s timeout per page, graceful failure handling
- Testing: 31 comprehensive tests (4 unit Lab + 21 unit agent + 6 integration), Lab model 100% coverage, agent 62% coverage
- QA score: 95/100 - production-ready, excellent code quality

**Epic 3 (Story 3.5):**
- Batch processing: Parallel LLM calls within batches using asyncio.Semaphore for rate limiting
- Configuration: Added `professor_filtering_batch_size` (default: 15) and `max_concurrent_llm_calls` (default: 5, max: 20) to SystemParams
- Parallel execution: `filter_professor_batch_parallel()` achieves 5-10x speedup (6-12 sec vs 30-60 sec for batch of 15)
- Rate limiting: Semaphore prevents API throttling while maximizing throughput
- Error handling: Two-tier strategy - individual professor failures use inclusive fallback, infrastructure failures re-raise for resumability
- Resumability: Checkpoint-based recovery from last completed batch (`phase-2-filter` checkpoints)
- Progress tracking: Two-level progress (overall batch progress + within-batch progress)
- Performance: Batch size=15 provides optimal balance between throughput and resumability granularity
- Testing: 9 comprehensive integration tests covering all 6 ACs, parallel execution, rate limiting, resumability, failure handling
- QA score: 100/100 - exceptional quality, production-ready, zero technical debt

**Epic 3 (Story 3.2):**
- Professor filtering: LLM-based research alignment using `filter_professor_research()` from llm_helpers
- Decision logic: Confidence >= 70 → include, < 70 → exclude (configurable threshold)
- Inclusive fallback: LLM failures default to "include" with confidence=0 for human review
- Profile loading: Markdown parsing from `output/user_profile.md` with regex extraction
- Model extensions: Added `is_relevant`, `relevance_confidence`, `relevance_reasoning` to Professor model
- Data quality flags: `llm_filtering_failed`, `low_confidence_filter` for degraded operations
- Batch processing: Resumable via checkpoint manager (`phase-2-filter` checkpoints)
- Edge case handling: Interdisciplinary researchers logged separately, missing research areas included by default
- SystemParams.load(): Added classmethod for convenient config loading
- Testing: 15 comprehensive tests (100% AC coverage), ruff ✅, mypy ✅

**Epic 3 (Story 3.1a):**
- Professor model: `data_quality_flags`, research areas, lab affiliations, profile tracking
- Discovery agent: ClaudeSDKClient with WebFetch/Playwright fallback, retry logic (3 attempts, exponential backoff)
- Department loading: Loads from `checkpoints/phase-1-relevant-departments.jsonl`, filters for is_relevant=True
- Data quality flags: `scraped_with_playwright_fallback`, `missing_email`, `missing_research_areas`, `missing_lab_affiliation`, `ambiguous_lab`
- ID generation: SHA256 hash of `name:department_id` (first 16 chars)
- Key pattern: ClaudeSDKClient class with `setting_sources=None` prevents codebase context injection
- 10 comprehensive tests (basic discovery + edge cases), all passing

**Epic 2:**
- Department model: `data_quality_flags`, `is_relevant`, `relevance_reasoning` fields
- UniversityDiscoveryAgent: retry logic (tenacity), graceful degradation, manual fallback (`departments_fallback.json`), structure gap reports, 50% validation thresholds
- Department filtering: LLM-based relevance analysis, edge case detection (interdisciplinary, generic, ambiguous)
- Checkpoints: `phase-1-departments.jsonl` (all discovered), `phase-1-relevant-departments.jsonl` (filtered)
- Output reports: `filtered-departments.md` for user review
- Flags: `missing_url`, `missing_school`, `ambiguous_hierarchy`, `partial_metadata`, `inference_based`, `manual_entry`, `scraping_failed`

**Epic 1:**
- LLM prompt templates: `DEPARTMENT_RELEVANCE_TEMPLATE`, `PROFESSOR_FILTER_TEMPLATE`, `LINKEDIN_MATCH_TEMPLATE`
- ConsolidatedProfile: LLM-generated `streamlined_interests` field
- Checkpoint manager: JSONL batch-level persistence with resume support

### Next Steps

**Immediate:** Continue Epic 4 (Lab Intelligence) - Lab analysis and LinkedIn integration

**Following:** Epics 5&6 (parallel: Publications + LinkedIn) → Epic 7 (Fitness) → Epic 8 (Reports)

### Current Environment

**Working Components:** Validation, credential management, checkpoints, logging, LLM helpers, progress tracking, MCP client, profile consolidation, university discovery, department filtering, professor model, professor discovery, parallel professor discovery, deduplication, rate limiting, professor filtering, confidence scoring, filtered professor logging, batch processing, lab website discovery, lab website scraping

**Test Status:** 424 tests passing (255 from Epics 1-2 + 138 from Epic 3 + 31 from Story 4.1), ruff ✅, mypy ✅

## Documentation References

**Primary (sharded):**
- `docs/architecture/` - Architecture details (use these over `architecture.md`)
- `docs/prd/` - Product requirements (use these over `prd.md`)
- `docs/stories/` - User stories
- `docs/DEVELOPMENT-HANDOFF.md` - Handoff notes
- `docs/ARCHITECTURE-ERRATA.md` - Known issues

**Note:** If updating sharded docs, sync changes back to consolidated `architecture.md`/`prd.md`
