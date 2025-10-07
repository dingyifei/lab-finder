# Lab Finder - Development Handoff Document

**Project:** Lab Finder - Research Lab Discovery and Analysis Tool
**Version:** 1.0
**Date:** 2025-10-06
**Status:** Ready for Development ✅

---

## Executive Summary

This document provides comprehensive guidance for implementing the Lab Finder project. All planning artifacts (PRD, architecture, user stories) are complete and validated. The project is ready for immediate development.

**Key Facts:**
- **42 user stories** across 8 epics, all validated and ready
- **Architecture:** Multi-agent phased pipeline with checkpoint-based resumability
- **Tech Stack:** Python 3.11.7, Claude Agent SDK, Playwright, MCP servers
- **Timeline:** 10 weeks (5 sprints) estimated
- **Team Size:** Recommended 2-3 developers

**Critical Success Factors:**
1. Complete Epic 1 (Foundation) first - all other epics depend on it
2. Story 1.4 (Shared Utilities) is the most critical dependency
3. Follow checkpoint patterns consistently for resumability
4. Use mcp-linkedin MCP server for Epic 6 (NOT Playwright queue)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Prerequisites & Setup](#prerequisites--setup)
3. [Architecture Overview](#architecture-overview)
4. [Development Guidelines](#development-guidelines)
5. [Implementation Roadmap](#implementation-roadmap)
6. [Key Technical Decisions](#key-technical-decisions)
7. [Testing Requirements](#testing-requirements)
8. [Common Patterns & Utilities](#common-patterns--utilities)
9. [Quality Assurance](#quality-assurance)
10. [Troubleshooting & Support](#troubleshooting--support)

---

## Project Overview

### What is Lab Finder?

Lab Finder is a CLI-based tool that systematically discovers, analyzes, and ranks research labs at a target university based on the user's research interests and academic profile.

**Core Workflow:**
```
User Config + Resume → Profile Consolidation → University Discovery →
Professor Discovery & Filtering → Lab Website Intelligence →
Publication Retrieval → LinkedIn Analysis → Fitness Scoring →
Comprehensive Reports (Overview.md + Individual Lab Reports)
```

**Primary Value:**
- Automates time-consuming lab research process
- Provides comprehensive intelligence (publications, team, activity level)
- Generates ranked recommendations with actionable next steps

### Key Documents

| Document | Location | Purpose |
|----------|----------|---------|
| **PRD** | `docs/prd.md` | Product requirements, functional/non-functional requirements |
| **Architecture** | `docs/architecture.md` | System architecture, tech stack, design decisions |
| **Story Index** | `docs/stories/STORY-INDEX.md` | Complete story catalog with dependencies |
| **User Stories** | `docs/stories/*.md` | 42 detailed user stories (1.1-8.5) |

---

## Prerequisites & Setup

### Development Environment

**Required:**
- Python 3.11.7 (not 3.12+ for Claude SDK compatibility)
- Node.js 18+ (for MCP servers)
- Git
- Code editor (VS Code recommended)

**Installation Steps:**

```bash
# 1. Clone repository
cd /path/to/project

# 2. Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install Python dependencies (after Epic 1.1 creates requirements.txt)
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install MCP servers (Story 1.5)
npm install -g @modelcontextprotocol/server-paper-search
npm install -g mcp-linkedin

# 5. Verify installations
python --version  # Should be 3.11.7
pytest --version  # Should be 7.4.4
playwright --version  # Should be 1.40.0
```

### Required External Services

**MCP Servers (Story 1.5):**
1. **paper-search-mcp** - Publication retrieval
   - Installation: `npm install -g @modelcontextprotocol/server-paper-search`
   - Configuration: No credentials needed
   - Testing: See Story 1.5, Task 4

2. **mcp-linkedin** - LinkedIn profile access
   - Installation: `npm install -g mcp-linkedin`
   - Repository: https://github.com/adhikasp/mcp-linkedin
   - Documentation: https://lobehub.com/mcp/adhikasp-mcp-linkedin
   - **Configuration:** LinkedIn credentials configured in MCP server settings (NOT in application code)
   - Testing: See Story 1.5, Task 4

**Archive.org:**
- No setup required (public API)
- Rate limit: 15 requests/minute (Story 4.2)

**Journal Reputation Database (Story 5.3):**
- Download SJR CSV: https://www.scimagojr.com/journalrank.php
- Place in `data/sjr-journal-rankings.csv`

### Development Tools

**Recommended:**
- **IDE:** VS Code with Python extension
- **Linting:** ruff (configured in pyproject.toml)
- **Type Checking:** mypy (must pass with no errors)
- **Testing:** pytest with coverage, asyncio, mock plugins

**VS Code Extensions:**
- Python (Microsoft)
- Pylance
- Python Test Explorer
- GitLens

---

## Architecture Overview

### System Architecture

**Pattern:** Phased Pipeline with Multi-Agent Orchestration

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI Coordinator                         │
│              (Manages sequential phases)                    │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   Phase 0-1         Phase 2-3         Phase 4-6
  Validation &     University &      Lab Research &
   Setup           Professor           Analysis
                   Discovery
```

### Phased Execution Model

| Phase | Epic | Agent(s) | Checkpoint Output |
|-------|------|----------|-------------------|
| **Phase 0** | 1 | Configuration Validator | `phase-0-validation.json` |
| **Phase 1** | 2 | University Discovery Agent | `phase-1-relevant-departments.jsonl` |
| **Phase 2** | 3 | Professor Discovery/Filter Agents | `phase-2-professors-filtered-batch-*.jsonl` |
| **Phase 3** | 4 | Lab Research Agent | `phase-3-labs-batch-*.jsonl` |
| **Phase 4** | 5 | Publication Retrieval Agent | `phase-4-publications-batch-*.jsonl` |
| **Phase 5** | 6 | LinkedIn Matcher Agent | Updates `phase-3-labs` with LinkedIn data |
| **Phase 6** | 7 | Fitness Scorer Agent | Updates `phase-3-labs` with scores |
| **Phase 7** | 8 | Report Generator Agent | `output/Overview.md`, `output/labs/*.md` |

**Key Principle:** Each phase produces checkpoints enabling resumability. If execution fails, restart from the last completed checkpoint.

### Technology Stack Summary

**Core:**
- Python 3.11.7 (async/await)
- Claude Agent SDK (multi-agent orchestration)
- Playwright 1.40.0 (fallback web scraping)
- MCP 1.0.0 (paper-search-mcp, mcp-linkedin)

**Data & Validation:**
- Pydantic 2.5.3 (data models)
- jsonschema 4.21.1 (config validation)
- jsonlines 4.0.0 (checkpoint JSONL)

**Testing:**
- pytest 7.4.4 (test framework)
- pytest-asyncio 0.23.3 (async tests)
- pytest-cov 4.1.0 (coverage)
- pytest-mock 3.12.0 (mocking)

**Utilities:**
- structlog 24.1.0 (structured logging)
- rich 13.7.0 (progress bars)
- tenacity 8.2.3 (retry logic)
- aiolimiter 1.1.0 (rate limiting)
- waybackpy 3.0.6 (Archive.org API)

**See `docs/architecture.md` for complete tech stack table.**

---

## Development Guidelines

### Coding Standards

**1. Type Hints (REQUIRED)**
```python
# ✅ CORRECT
def filter_professors(professors: list[Professor], profile: UserProfile) -> list[Professor]:
    """Filter professors by research alignment."""
    pass

# ❌ INCORRECT - No type hints
def filter_professors(professors, profile):
    pass
```

**2. Logging (REQUIRED)**
```python
# ✅ CORRECT - Use structlog
from src.utils.logger import get_logger

logger = get_logger(correlation_id="abc-123", phase="phase-2", component="professor_filter")
logger.info("Filtering professors", total=len(professors))

# ❌ INCORRECT - Never use print()
print("Filtering professors")
```

**3. Checkpoint Management (REQUIRED)**
```python
# ✅ CORRECT - Use checkpoint_manager
from src.utils.checkpoint_manager import save_batch

save_batch(phase="phase-2", batch_id=1, data=professors)

# ❌ INCORRECT - Never write JSONL directly
with open("checkpoint.jsonl", "w") as f:
    for p in professors:
        f.write(json.dumps(p.model_dump()) + "\n")
```

**4. Web Scraping (REQUIRED)**
```python
# ✅ CORRECT - Try built-in tools first, then Playwright fallback
try:
    content = await built_in_fetch(url)
except Exception:
    content = await playwright_fetch(url)

# ❌ INCORRECT - Using Playwright directly without trying built-in first
content = await playwright_fetch(url)
```

**5. LLM Calls (REQUIRED)**
```python
# ✅ CORRECT - Use llm_helpers module
from src.utils.llm_helpers import call_llm_with_retry, PROFESSOR_FILTER_PROMPT

response = call_llm_with_retry(
    prompt=PROFESSOR_FILTER_PROMPT.format(name=prof.name, interests=interests)
)

# ❌ INCORRECT - Inline LLM prompts
response = llm.call("Is this professor relevant?")
```

### File Organization

**Project Structure:**
```
lab-finder/
├── src/                          # Source code
│   ├── agents/                   # Phase agents
│   │   ├── university_discovery.py
│   │   ├── professor_discovery.py
│   │   ├── professor_filter.py
│   │   ├── lab_research.py
│   │   ├── publication_retrieval.py
│   │   ├── linkedin_matcher.py
│   │   ├── authorship_analyzer.py
│   │   ├── fitness_scorer.py
│   │   └── report_generator.py
│   ├── models/                   # Pydantic models
│   │   ├── user_profile.py
│   │   ├── department.py
│   │   ├── professor.py
│   │   ├── lab.py
│   │   ├── publication.py
│   │   ├── lab_member.py
│   │   └── authorship_analysis.py
│   ├── utils/                    # Shared utilities (Epic 1.7)
│   │   ├── checkpoint_manager.py
│   │   ├── llm_helpers.py
│   │   ├── progress_tracker.py
│   │   ├── logger.py
│   │   ├── mcp_client.py
│   │   └── web_scraper.py
│   ├── coordinator.py            # CLI coordinator (main entry point)
│   └── __init__.py
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── fixtures/                 # Test data fixtures
├── config/                       # Configuration files
│   ├── user-profile.json
│   ├── university-config.json
│   ├── system-parameters.json
│   └── .env                      # Credentials (gitignored)
├── checkpoints/                  # JSONL checkpoints (gitignored)
├── output/                       # Generated reports (gitignored)
│   └── labs/                     # Individual lab reports
├── logs/                         # Structured logs (gitignored)
├── data/                         # Static data (SJR CSV)
├── docs/                         # Documentation
├── requirements.txt              # Python dependencies
├── pytest.ini                    # pytest configuration
├── pyproject.toml                # ruff, mypy configuration
└── README.md                     # Project README
```

### Git Workflow

**Branch Strategy:**
- `main` - Production-ready code
- `develop` - Integration branch
- `epic/{N}-{name}` - Epic feature branches
- `story/{N}.{M}-{name}` - Story feature branches

**Commit Convention:**
```
[Story X.Y] Brief description

- Detailed change 1
- Detailed change 2

Addresses: Story X.Y - Title
```

**Pull Request Template:**
```markdown
## Story
Story X.Y - Title

## Changes
- Implementation detail 1
- Implementation detail 2

## Testing
- [ ] Unit tests passing (70% coverage)
- [ ] Integration tests passing
- [ ] mypy passes with no errors
- [ ] Manual testing completed

## Checklist
- [ ] Type hints on all functions
- [ ] No print() statements (using structlog)
- [ ] Checkpoint patterns followed
- [ ] Documentation updated
```

---

## Implementation Roadmap

### Epic 1: Foundation (Sprint 1 - Week 1-2)

**Stories:** 1.1-1.7
**Critical Path:** Story 1.4 must complete before any Epic 2+ work begins

**Implementation Order:**
```
Week 1:
- Story 1.1: Project Setup (Day 1-2)
- Story 1.2: JSON Schema Validation (Day 2-3)
- Story 1.6: Testing Infrastructure (Day 3-4)
- Story 1.5: MCP Server Setup (Day 4-5, parallel with 1.6)

Week 2:
- Story 1.4: Shared Utilities (Day 1-3) ★ CRITICAL
  - checkpoint_manager.py
  - llm_helpers.py
  - progress_tracker.py
  - logger.py
- Story 1.3: Credential Management (Day 4)
- Story 1.7: User Profile Consolidation (Day 5)
```

**Deliverable:** Working foundation with all shared utilities tested and ready

**Acceptance Criteria:**
- ✅ All Story 1.4 utilities implemented and tested
- ✅ pytest infrastructure working
- ✅ MCP servers connected and tested
- ✅ Type checking (mypy) passes
- ✅ 70% code coverage achieved

### Epic 2: University Discovery (Sprint 2 - Week 3-4, Part 1)

**Stories:** 2.1-2.5
**Dependencies:** Epic 1 complete (especially Story 1.4)

**Implementation Order:**
```
Week 3:
- Story 2.1: University Discovery Agent (Day 1-3)
  - Department model
  - Web scraping with fallback
  - Sub-agent spawning
- Story 2.4: Error Handling (Day 3-4, parallel with 2.1)
- Story 2.5: Batch Configuration (Day 4-5)

Week 4:
- Story 2.2: JSON Representation (Day 1)
- Story 2.3: Department Filtering (Day 2-3)
- Testing & Integration (Day 4-5)
```

**Deliverable:** `checkpoints/phase-1-relevant-departments.jsonl`

### Epic 3: Professor Discovery (Sprint 2 - Week 3-4, Part 2)

**Stories:** 3.1-3.5
**Dependencies:** Epic 2 complete

**Implementation Order:**
```
Week 3-4 (overlaps with Epic 2 completion):
- Story 3.1: Professor Discovery (Day 1-2)
- Story 3.2: LLM Filtering (Day 2-3)
- Story 3.3: Confidence Scoring (Day 3-4)
- Story 3.4: Logging & Transparency (Day 4)
- Story 3.5: Batch Processing (Day 5)
```

**Deliverable:** `checkpoints/phase-2-professors-filtered-batch-*.jsonl`

### Epic 4: Lab Intelligence (Sprint 3 - Week 5-6)

**Stories:** 4.1-4.5
**Dependencies:** Epic 3 complete

**Implementation Order:**
```
Week 5:
- Story 4.1: Lab Website Scraping (Day 1-3)
  - Lab model
  - Website discovery
  - Content extraction
- Story 4.5: Error Handling (Day 3-4, parallel with 4.1)

Week 6:
- Story 4.2: Archive.org Integration (Day 1-2)
- Story 4.3: Contact Extraction (Day 2-3)
- Story 4.4: Missing Website Handling (Day 3-4)
- Testing & Integration (Day 5)
```

**Deliverable:** `checkpoints/phase-3-labs-batch-*.jsonl`

### Epic 5 & 6: Publications & LinkedIn (Sprint 4 - Week 7-8, PARALLEL)

**Stories:** 5.1-5.5, 6.1-6.5
**Dependencies:** Epic 4 complete
**Note:** These epics can be developed in parallel by different developers

**Epic 5 Implementation (Developer A):**
```
Week 7:
- Story 5.1: MCP Publication Retrieval (Day 1-2)
- Story 5.2: Abstract Analysis (Day 3-4)
- Story 5.3: Journal Weighting (Day 5)

Week 8:
- Story 5.4: Lab Member Publications (Day 1-2)
- Story 5.5: Member Inference (Day 3-4)
- Testing (Day 5)
```

**Epic 6 Implementation (Developer B):**
```
Week 7:
- Story 6.1: mcp-linkedin Integration (Day 1-2)
- Story 6.2: Parallel Matching (Day 3)
- Story 6.3: Profile Matching (Day 4-5)

Week 8:
- Story 6.4: PhD Detection (Day 1-2)
- Story 6.5: Error Handling (Day 3)
- Testing (Day 4-5)
```

**Deliverables:**
- `checkpoints/phase-4-publications-batch-*.jsonl`
- Updated `checkpoints/phase-3-labs-batch-*.jsonl` (with LinkedIn data)

### Epic 7: Fitness Scoring (Sprint 5 - Week 9-10, Part 1)

**Stories:** 7.1-7.5
**Dependencies:** Epics 5 & 6 complete

**Implementation Order:**
```
Week 9:
- Story 7.1: Authorship Analysis (Day 1-2)
- Story 7.2: Core vs Collaborator (Day 2-3)
- Story 7.3: Collaboration Network (Day 3-4)
- Story 7.4: LLM Criteria (Day 5)

Week 10:
- Story 7.5: Fitness Scoring (Day 1-2)
```

**Deliverable:** Updated `checkpoints/phase-3-labs-batch-*.jsonl` (with fitness scores)

### Epic 8: Report Generation (Sprint 5 - Week 9-10, Part 2)

**Stories:** 8.1-8.5
**Dependencies:** Epic 7 complete

**Implementation Order:**
```
Week 10:
- Story 8.1: Overview Report (Day 2-3)
- Story 8.2: Comparison Matrix (Day 3)
- Story 8.3: Next Steps (Day 4)
- Story 8.4: Detailed Reports (Day 4-5)
- Story 8.5: Data Quality Flags (Day 5)
```

**Deliverables:**
- `output/Overview.md`
- `output/labs/*.md`

---

## Key Technical Decisions

### 1. Checkpoint Format: JSONL with Batch-Level Granularity

**Decision:** Use JSONL (JSON Lines) with batch-level checkpoints

**Rationale:**
- Enables streaming read/write
- Batch-level granularity allows mid-phase resumability
- Human-readable for debugging

**Pattern:**
```python
# Save batch
from src.utils.checkpoint_manager import save_batch

save_batch(
    phase="phase-2-filter",
    batch_id=3,
    data=[professor.model_dump() for professor in batch]
)
# Creates: checkpoints/phase-2-filter-batch-3.jsonl

# Resume from checkpoint
from src.utils.checkpoint_manager import get_resume_point

resume_batch = get_resume_point("phase-2-filter")
# Returns: 4 (first incomplete batch)
```

### 2. Web Scraping: Tiered Fallback (Built-in → Playwright)

**Decision:** Try Claude Agent SDK built-in tools first, fallback to Playwright

**Rationale:**
- Built-in tools faster and simpler for most public pages
- Playwright needed for JS-heavy or authenticated pages
- NFR5 requirement

**Pattern:**
```python
async def fetch_with_fallback(url: str) -> str:
    try:
        # Try built-in first
        content = await built_in_fetch(url)
        logger.info(f"Built-in tools succeeded for {url}")
        return content
    except Exception as e:
        logger.warning(f"Built-in failed, trying Playwright: {e}")
        # Fallback to Playwright
        content = await playwright_fetch(url)
        logger.info(f"Playwright succeeded for {url}")
        return content
```

### 3. LinkedIn Integration: mcp-linkedin MCP Server (NOT Playwright Queue)

**Decision:** Use mcp-linkedin MCP server for all LinkedIn operations

**Rationale:**
- MCP server handles authentication, session management, rate limiting
- Eliminates queue complexity
- Enables parallel LinkedIn access
- Architecture requirement

**CRITICAL:** Do NOT implement Playwright queue pattern for LinkedIn. Use mcp-linkedin MCP server.

**Pattern:**
```python
from src.utils.mcp_client import search_linkedin_profile

# MCP server handles all session/auth complexity
profiles = await search_linkedin_profile(
    name=member.name,
    university=university_name
)
```

### 4. LLM Calls: Centralized Prompts in llm_helpers.py

**Decision:** All LLM prompts defined in `src/utils/llm_helpers.py`

**Rationale:**
- Centralized prompt management
- Easy to update prompts across codebase
- Consistent retry logic
- Architecture requirement

**Pattern:**
```python
# In src/utils/llm_helpers.py
PROFESSOR_FILTER_PROMPT = """
User Research Interests: {interests}
Professor: {name}
Research Areas: {areas}

Should this professor be included? Respond in JSON:
{{"decision": "include/exclude", "confidence": 0-100, "reasoning": "..."}}
"""

# Usage in agents
from src.utils.llm_helpers import call_llm_with_retry, PROFESSOR_FILTER_PROMPT

response = call_llm_with_retry(
    prompt=PROFESSOR_FILTER_PROMPT.format(
        interests=profile.research_interests,
        name=professor.name,
        areas=professor.research_areas
    )
)
```

### 5. Error Handling: Graceful Degradation with Data Quality Flags

**Decision:** Never fail pipeline for missing data; flag and continue

**Rationale:**
- Partial data better than no data
- Transparency through data quality flags
- NFR13 requirement

**Pattern:**
```python
try:
    lab.website_content = await scrape_website(lab.lab_url)
except Exception as e:
    logger.error(f"Failed to scrape {lab.lab_url}: {e}")
    lab.data_quality_flags.append("scraping_failed")
    # Continue processing with partial data

# Lab object still valid, just flagged
return lab
```

---

## Testing Requirements

### Coverage Requirements

**Minimum Coverage:** 70% across all modules

**Enforcement:**
```ini
# pytest.ini
[pytest]
addopts =
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=70
```

### Test Organization

```
tests/
├── unit/                         # Fast, isolated tests
│   ├── test_checkpoint_manager.py
│   ├── test_llm_helpers.py
│   ├── test_professor_filter.py
│   └── ...
├── integration/                  # Multi-component tests
│   ├── test_university_discovery.py
│   ├── test_mcp_client.py
│   └── ...
└── fixtures/                     # Test data
    ├── mock_university_structure.html
    ├── mock_professor_directory.html
    └── sample_config.json
```

### Test Patterns

**Unit Test Example (AAA Pattern):**
```python
def test_filter_professors_includes_relevant(mocker):
    # Arrange
    mock_llm = mocker.patch('src.utils.llm_helpers.call_llm_with_retry')
    mock_llm.return_value = '{"decision": "include", "confidence": 95, "reasoning": "Strong match"}'

    professor = Professor(id="1", name="Dr. Smith", research_areas=["AI", "ML"])
    profile = UserProfile(research_interests="Machine Learning")
    agent = ProfessorFilterAgent()

    # Act
    result = agent.filter_professors([professor], profile)

    # Assert
    assert len(result) == 1
    assert result[0].is_relevant == True
    assert result[0].relevance_confidence == 95
```

**Async Test Example:**
```python
@pytest.mark.asyncio
async def test_scrape_lab_website(mocker):
    # Arrange
    mock_fetch = mocker.patch('src.agents.lab_research.built_in_fetch')
    mock_fetch.return_value = "<html><h1>Lab Overview</h1></html>"

    agent = LabResearchAgent()

    # Act
    result = await agent.scrape_lab_website("https://lab.edu")

    # Assert
    assert "Lab Overview" in result
    mock_fetch.assert_called_once()
```

**Integration Test Example:**
```python
@pytest.mark.integration
def test_checkpoint_save_and_load(tmp_path):
    # Arrange
    manager = CheckpointManager(checkpoint_dir=tmp_path)
    data = [Professor(id="1", name="Dr. Smith")]

    # Act
    manager.save_batch("phase-2", batch_id=1, data=data)
    loaded = manager.load_batches("phase-2")

    # Assert
    assert len(loaded) == 1
    assert loaded[0]["name"] == "Dr. Smith"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_checkpoint_manager.py

# Run specific test
pytest tests/unit/test_checkpoint_manager.py::test_save_batch

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with verbose output
pytest -v

# Run async tests
pytest -v tests/unit/test_async_operations.py
```

---

## Common Patterns & Utilities

### Pattern 1: Checkpoint Save/Load

**Every agent should save checkpoints:**

```python
from src.utils.checkpoint_manager import save_batch, load_batches, get_resume_point

# Save batch
save_batch(
    phase="phase-2-filter",
    batch_id=batch_num,
    data=[p.model_dump() for p in professors_batch]
)

# Resume from checkpoint
resume_point = get_resume_point("phase-2-filter")
if resume_point > 0:
    logger.info(f"Resuming from batch {resume_point}")
    completed = load_batches("phase-2-filter")

# Mark phase complete
mark_phase_complete("phase-2-filter")
```

### Pattern 2: Progress Tracking

**Every long-running operation should show progress:**

```python
from src.utils.progress_tracker import ProgressTracker

tracker = ProgressTracker()

# Start phase
tracker.start_phase("Professor Filtering", total_items=len(professors))

# Update progress
for i, professor in enumerate(professors):
    result = filter_professor(professor)
    tracker.update(i + 1)

# Complete phase
tracker.complete_phase()
# Output: "Phase: Professor Filtering complete: 150 items processed"
```

### Pattern 3: Structured Logging

**Every component should use structured logging:**

```python
from src.utils.logger import get_logger

logger = get_logger(
    correlation_id="run-abc-123",
    phase="phase-2",
    component="professor_filter"
)

# Log with context
logger.info(
    "Filtering professor",
    professor_name=professor.name,
    department=professor.department,
    research_areas=professor.research_areas
)

logger.warning(
    "Low confidence match",
    professor_id=professor.id,
    confidence_score=65,
    threshold=70
)
```

### Pattern 4: LLM Calls with Retry

**All LLM calls should use retry logic:**

```python
from src.utils.llm_helpers import call_llm_with_retry, PROFESSOR_FILTER_PROMPT

prompt = PROFESSOR_FILTER_PROMPT.format(
    interests=profile.research_interests,
    name=professor.name,
    areas=", ".join(professor.research_areas)
)

# Automatically retries on failure (max 3 attempts)
response = call_llm_with_retry(prompt)

# Parse JSON response
import json
result = json.loads(response)
```

### Pattern 5: Batch Processing

**Process large datasets in batches:**

```python
from src.utils.batch import divide_into_batches
from src.utils.checkpoint_manager import get_resume_point, save_batch

batch_size = config["batch_config"]["professor_filtering_batch_size"]
batches = divide_into_batches(professors, batch_size)

# Resume from checkpoint
resume_batch = get_resume_point("phase-2-filter")

# Process remaining batches
for batch_id in range(resume_batch, len(batches)):
    batch = batches[batch_id]

    # Process batch
    results = await process_batch_async(batch)

    # Save checkpoint
    save_batch("phase-2-filter", batch_id, results)

    # Update progress
    progress_tracker.update(batch_id + 1)
```

### Pattern 6: Error Handling

**Never crash on expected failures:**

```python
async def scrape_lab_website_safe(lab: Lab) -> Lab:
    """Scrape with comprehensive error handling."""
    if not lab.lab_url:
        lab.data_quality_flags.append("no_website")
        return lab

    try:
        # Rate limiting
        await rate_limiter.acquire(lab.lab_url)

        # Fetch with timeout
        content = await fetch_with_timeout(lab.lab_url, timeout=30)

        # Parse content
        lab.website_content = content
        lab.description = extract_description(content)

    except TimeoutError:
        logger.warning(f"Timeout scraping {lab.lab_url}")
        lab.data_quality_flags.append("timeout")
    except Exception as e:
        logger.error(f"Failed to scrape {lab.lab_url}: {e}")
        lab.data_quality_flags.append("scraping_failed")

    # Always return lab object (with or without data)
    return lab
```

---

## Quality Assurance

### Pre-Commit Checklist

Before committing code:

- [ ] **Type checking passes:** `mypy src/`
- [ ] **Linting passes:** `ruff check src/`
- [ ] **Tests pass:** `pytest`
- [ ] **Coverage >= 70%:** `pytest --cov=src`
- [ ] **No print() statements** (use structlog)
- [ ] **Type hints on all functions**
- [ ] **Docstrings on public functions**
- [ ] **Checkpoint patterns followed**

### Code Review Checklist

When reviewing PRs:

**Architecture Alignment:**
- [ ] Follows phased pipeline architecture
- [ ] Uses shared utilities from Story 1.4
- [ ] Checkpoint save/load implemented correctly
- [ ] Progress tracking integrated

**Code Quality:**
- [ ] Type hints on all functions
- [ ] No print() statements (using structlog)
- [ ] Error handling with graceful degradation
- [ ] Data quality flags used appropriately

**Testing:**
- [ ] Unit tests cover new code (70%+)
- [ ] Integration tests for multi-component features
- [ ] AAA pattern (Arrange, Act, Assert)
- [ ] Mocks used for external dependencies

**Documentation:**
- [ ] Docstrings on public functions
- [ ] README updated if needed
- [ ] Story status updated to "Complete"

### Validation Gates

**Epic Completion Gates:**

1. **All stories in epic complete**
2. **All tests passing**
3. **Code coverage >= 70%**
4. **mypy passes with no errors**
5. **Integration test with real data successful**
6. **Checkpoint files generated correctly**
7. **Documentation updated**

---

## Troubleshooting & Support

### Common Issues

**Issue 1: MCP Server Connection Failure**
```
Error: Cannot connect to mcp-linkedin server
```

**Solution:**
1. Verify MCP server installed: `npm list -g mcp-linkedin`
2. Check MCP server running: See Story 1.5 connectivity tests
3. Verify LinkedIn credentials configured in MCP server (NOT in code)

---

**Issue 2: Checkpoint Not Resuming**
```
Error: get_resume_point returns 0 but checkpoints exist
```

**Solution:**
1. Check checkpoint file naming: Must match pattern `phase-{N}-batch-{M}.jsonl`
2. Verify `_phase_completion_markers.json` exists
3. Check checkpoint_manager.py logic

---

**Issue 3: Type Checking Failures**
```
Error: mypy - Incompatible types in assignment
```

**Solution:**
1. Add type hints to all function parameters and return values
2. Use `Optional[Type]` for nullable fields
3. Use `list[Type]` not `List[Type]` (Python 3.11+)

---

**Issue 4: Test Coverage Below 70%**

**Solution:**
1. Identify uncovered lines: `pytest --cov=src --cov-report=term-missing`
2. Add unit tests for uncovered functions
3. Use mocks for external dependencies

---

**Issue 5: Web Scraping Blocked**
```
Error: 429 Too Many Requests
```

**Solution:**
1. Check rate limiting configured correctly (Story 4.5)
2. Reduce batch sizes in `system-parameters.json`
3. Add delays between requests: `await asyncio.sleep(1)`

---

### Getting Help

**Documentation:**
- Architecture: `docs/architecture.md`
- User Stories: `docs/stories/*.md`
- Story Index: `docs/stories/STORY-INDEX.md`

**Key Contacts:**
- Architect: Winston (architecture questions)
- PO: Sarah (requirements, story clarifications)

**Development Notes:**
- Every story has a "Dev Notes" section with architecture references
- Every story has testing requirements and examples
- Refer to Story 1.4 for shared utilities documentation

---

## Appendix

### Quick Reference Commands

```bash
# Setup
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Testing
pytest                                    # Run all tests
pytest --cov=src --cov-report=html        # With coverage
pytest tests/unit/                        # Unit tests only
pytest -v -k "test_checkpoint"            # Specific test pattern

# Type Checking
mypy src/                                 # Type check

# Linting
ruff check src/                           # Lint
ruff format src/                          # Format

# Run Application (after implementation)
python -m src.coordinator --config config/user-profile.json
```

### Key File Locations Quick Reference

| File | Location |
|------|----------|
| Main entry point | `src/coordinator.py` |
| Shared utilities | `src/utils/` |
| Agents | `src/agents/` |
| Pydantic models | `src/models/` |
| Tests | `tests/` |
| Config | `config/` |
| Checkpoints | `checkpoints/` |
| Output reports | `output/` |
| Documentation | `docs/` |

---

**End of Development Handoff Document**

**Status:** Ready for Development ✅

**Next Steps:**
1. Review this document with development team
2. Set up development environment (Prerequisites section)
3. Begin Epic 1, Story 1.1
4. Follow implementation roadmap sequentially

**Good luck with the implementation!** 🚀

