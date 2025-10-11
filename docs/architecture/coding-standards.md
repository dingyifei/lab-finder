# Coding Standards

These standards are **MANDATORY** for AI agents and human developers. This section focuses on project-specific conventions and critical rules only.

## Core Standards

- **Languages & Runtimes:** Python 3.11.7 exclusively (no 3.12+ features, no Python 2 compatibility)
- **Style & Linting:** `ruff` with default configuration (enforces PEP 8, import sorting, etc.)
- **Test Organization:** Tests mirror source structure: `tests/unit/test_<module>.py` matches `src/<module>.py`

---

## Critical Rules

- **Never use print() for logging:** Always use `structlog` logger. `print()` breaks structured logging.
- **All LLM calls must use llm_helpers module:** Centralize prompt templates in `src/utils/llm_helpers.py`. No inline LLM prompts scattered in code.
- **Checkpoint saves must be atomic:** Use `checkpoint_manager.save_batch()` - never write JSONL files directly.
- **Always type hint function signatures:** Use `-> ReturnType` and parameter hints. MyPy must pass without errors.
- **Web scraping uses multi-stage pattern:** `WebFetch → Sufficiency Evaluation → Puppeteer MCP fallback → Re-evaluate → Retry (max 3)`
- **MCP servers must be configured via .mcp.json:** Configure in `claude/` directory, NOT via Python code
- **Always use cwd parameter for MCP access:** Point to `claude/` when instantiating ClaudeSDKClient for MCP discovery
- **Sufficiency evaluation uses strong prompts:** thinking parameter not supported in SDK v0.1.1 - use detailed prompt instructions instead
- **LinkedIn access must use MCP:** Never implement custom LinkedIn scraping. Always use mcp-linkedin MCP server tools.
- **Pydantic models for all data:** No raw dicts for domain entities. Use Pydantic models with validation.
- **Optional fields must have None defaults:** All optional Pydantic fields: `field: Optional[str] = None`
- **Data quality flags are mandatory:** When inferring data or skipping errors, append to `data_quality_flags` list.
- **No hardcoded batch sizes:** Use `system_parameters.json` config values, not magic numbers.
- **Async/await for I/O operations:** All web scraping, file I/O, MCP calls must use `async def` and `await`.
- **Correlation IDs in all log statements:** Always bind correlation_id to logger context.

**Example: Multi-Stage Web Scraping Pattern**

```python
# CORRECT: Multi-stage web scraping with Puppeteer MCP
from src.utils.web_scraping import scrape_with_sufficiency

result = await scrape_with_sufficiency(
    url=department_url,
    required_fields=["name", "email", "research_areas"],
    max_attempts=3,
    correlation_id=correlation_id
)

if not result["sufficient"]:
    # Add data quality flags for missing fields
    professor.data_quality_flags.append("insufficient_scraping")
```

**Reference:** `experiments/test_multistage_pattern.py` for full implementation

---

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Classes | PascalCase | `UniversityDiscoveryAgent` |
| Functions | snake_case | `discover_structure()` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRIES = 3` |
| Private methods | `_leading_underscore` | `_validate_credentials()` |
| Pydantic models | PascalCase | `ConsolidatedProfile`, `Professor`, `FitnessScore` |
| Files | snake_case | `university_discovery.py` |
| Test files | `test_<module>.py` | `test_checkpoint_manager.py` |
