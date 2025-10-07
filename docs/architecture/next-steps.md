# Next Steps

This architecture document is ready for development. The recommended next steps are:

## 1. Development Agent Handoff

**Action:** Provide this architecture document to the Development agent to begin implementation.

**Story-by-Story Implementation:**
- Start with **Epic 1 (Foundation)** stories 1.1-1.4
- Implement in order: Setup → Validation → Credentials → Profile Consolidation
- Each story should be completed with tests before moving to next

**Key Focus Areas:**
- Establish project structure per Source Tree section
- Implement Pydantic models as defined in Data Models section
- Build Checkpoint Manager utility first (used by all phases)
- Validate tech stack versions during setup

---

## 2. Configuration Schema Creation

**Action:** Define JSON schemas for all configuration files before coding begins.

**Schemas to Create:**
- `src/schemas/user-profile.schema.json` - User research profile
- `src/schemas/university.schema.json` - University details
- `src/schemas/system-parameters.schema.json` - Batch sizes, rate limits, etc.

**Validation:** Test schemas with sample config files from `tests/fixtures/`

---

## 3. External Dependencies Setup

**Action:** Configure external services and download static data.

**Tasks:**
- Install and configure `paper-search-mcp` MCP server
- Install and configure `mcp-linkedin` MCP server with LinkedIn credentials
- Download Scimago Journal Rank CSV to `data/` directory
- Set up Playwright with browser drivers (for web scraping fallback only)
- Document MCP server configuration in README

---

## 4. Iterative Development by Epic

**Recommended Implementation Order:**
1. **Epic 1:** Foundation (Stories 1.1-1.4) - Establish infrastructure
2. **Epic 2:** University Discovery (Stories 2.1-2.5) - First agent implementation
3. **Epic 3:** Professor Filtering (Stories 3.1-3.5) - Validate batch processing
4. **Epic 4:** Lab Intelligence (Stories 4.1-4.5) - Test web scraping patterns
5. **Epic 5:** Publications (Stories 5.1-5.5) - Validate MCP integration
6. **Epic 6:** LinkedIn (Stories 6.1-6.5) - Implement queue pattern
7. **Epic 7:** Scoring (Stories 7.1-7.5) - Test LLM-driven analysis
8. **Epic 8:** Reporting (Stories 8.1-8.5) - Final output generation

---

## 5. Testing Milestones

**After Each Epic:**
- Unit tests for all new components (70% coverage)
- Integration tests for external service interactions
- Manual smoke test of checkpoint/resume functionality

**Before Release:**
- Full E2E test on small university dataset
- Performance test (ensure reasonable runtime for large universities)
- Documentation review (README, architecture docs, inline comments)

---

## 6. Documentation Updates

**Living Documents:**
- Update this architecture document if significant design changes occur
- Maintain CHANGELOG.md for version history
- Update README.md with setup instructions and examples

---

## Development Agent Prompt

Please implement the Lab Finder system according to the architecture defined in `docs/architecture.md`.

**Start with Epic 1, Story 1.1:** Project Setup & Dependency Management

Follow the architecture's specifications for:
- Python 3.11.7 with pinned dependencies from Tech Stack section
- Source tree structure as defined in Source Tree section
- Pydantic models matching Data Models section
- Coding standards from Coding Standards section
- Test strategy from Test Strategy section

Reference the PRD (`docs/prd.md`) for detailed functional requirements and acceptance criteria for each story.

**Critical:** Adhere to the architecture's design patterns:
- Hierarchical agent coordination
- Batch-level JSONL checkpointing
- LLM-based matching (not algorithmic)
- Graceful degradation with data quality flags
- MCP server integration for LinkedIn and publication retrieval

Proceed story-by-story with tests. Checkpoint progress after each completed story.

