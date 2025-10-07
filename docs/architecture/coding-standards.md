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
- **Web scraping must try built-in tools first:** Pattern: `try built-in → except → fallback to Playwright → except → flag and skip`
- **LinkedIn access must use MCP:** Never implement custom LinkedIn scraping. Always use mcp-linkedin MCP server tools.
- **Pydantic models for all data:** No raw dicts for domain entities. Use Pydantic models with validation.
- **Optional fields must have None defaults:** All optional Pydantic fields: `field: Optional[str] = None`
- **Data quality flags are mandatory:** When inferring data or skipping errors, append to `data_quality_flags` list.
- **No hardcoded batch sizes:** Use `system_parameters.json` config values, not magic numbers.
- **Async/await for I/O operations:** All web scraping, file I/O, MCP calls must use `async def` and `await`.
- **Correlation IDs in all log statements:** Always bind correlation_id to logger context.

---

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Classes | PascalCase | `UniversityDiscoveryAgent` |
| Functions | snake_case | `discover_structure()` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRIES = 3` |
| Private methods | `_leading_underscore` | `_validate_credentials()` |
| Pydantic models | PascalCase | `UserProfile`, `FitnessScore` |
| Files | snake_case | `university_discovery.py` |
| Test files | `test_<module>.py` | `test_checkpoint_manager.py` |
