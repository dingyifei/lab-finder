# Lab Finder - User Stories Index

**Project:** Lab Finder
**Total Stories:** 44
**Status:** Ready for Development ✅
**Last Updated:** 2025-10-06

---

## Document Overview

This index provides a complete catalog of all user stories for the Lab Finder project, organized by epic. Use this document to:
- Navigate the complete story set
- Understand story dependencies
- Track implementation progress
- Plan development sprints

---

## Project Statistics

| Metric | Count |
|--------|-------|
| **Total Epics** | 8 |
| **Total Stories** | 42 |
| **Epic 1 (Foundation)** | 9 stories |
| **Epic 2 (University Discovery)** | 5 stories |
| **Epic 3 (Professor Discovery)** | 5 stories |
| **Epic 4 (Lab Intelligence)** | 5 stories |
| **Epic 5 (Publication Research)** | 5 stories |
| **Epic 6 (LinkedIn Integration)** | 3 stories |
| **Epic 7 (Fitness Scoring)** | 5 stories |
| **Epic 8 (Report Generation)** | 5 stories |

---

## Implementation Sequence

Stories should be implemented in **sequential epic order** with some parallelization possible within epics:

```
Epic 1 (Foundation) → Must complete FIRST
  ↓
Epic 2 (University Discovery) → Sequential
  ↓
Epic 3 (Professor Discovery) → Depends on Epic 2
  ↓
Epic 4 (Lab Intelligence) → Depends on Epic 3
  ↓
Epic 5 (Publication Research) → Parallel with Epic 6 (both depend on Epic 4)
Epic 6 (LinkedIn Integration) → Parallel with Epic 5 (both depend on Epic 4)
  ↓
Epic 7 (Fitness Scoring) → Depends on Epics 5 & 6
  ↓
Epic 8 (Report Generation) → Depends on Epic 7 (final epic)
```

---

## Epic 1: Foundation & Configuration Infrastructure

**Goal:** Establish project foundation, configuration management, testing infrastructure, and shared utilities.

**Status:** Ready for Development
**Story Count:** 9
**Dependencies:** None (starting point)

| Story | Title | Key Deliverables | Priority |
|-------|-------|------------------|----------|
| **1.0** | Project Initialization | Git repository, directory structure, Python venv, basic project files | **REQUIRED** |
| **1.1** | Project Setup & Dependency Management | Python environment, Claude SDK, directory structure | **REQUIRED** |
| **1.2** | JSON Configuration Schema & Validation | JSON schemas, validation logic, example configs | **REQUIRED** |
| **1.3** | Credential Management with CLI Prompts | Credential prompts, secure storage, config loading | **REQUIRED** |
| **1.4** | User Profile Consolidation | Resume parsing, profile markdown, research interests | **REQUIRED** |
| **1.5** | MCP Server Configuration & Testing | paper-search-mcp, mcp-linkedin, connectivity checks | **REQUIRED** |
| **1.6** | Testing Infrastructure Setup | pytest config, test structure, example tests | **REQUIRED** |
| **1.7** | Shared Utilities Implementation | checkpoint_manager, llm_helpers, progress_tracker, logger | **REQUIRED** |
| **1.8** | CI/CD Pipeline Setup | GitHub Actions workflow, automated linting/testing | **OPTIONAL** |

**Critical Note:** Story 1.0 is the absolute first story (project scaffolding). Story 1.7 must complete before Epic 2+ stories, as all subsequent stories depend on shared utilities. Story 1.8 is optional.

---

## Epic 2: University Structure Discovery & Department Filtering

**Goal:** Discover university department hierarchy, represent in JSON, and filter by relevance.

**Status:** Ready for Development
**Story Count:** 5
**Dependencies:** Epic 1 (especially Story 1.7)

| Story | Title | Key Deliverables | Dependencies |
|-------|-------|------------------|--------------|
| **2.1** | University Website Structure Discovery | Department discovery agent, Department model, web scraping | 1.7 |
| **2.2** | Department Structure JSON Representation | Hierarchical JSON, delegation utilities | 2.1 |
| **2.3** | Department Relevance Filtering | LLM-based filtering, filtered departments checkpoint | 2.1, 1.7 |
| **2.4** | Error Handling for Missing Structure Data | Data quality flags, structure gap report | 2.1 |
| **2.5** | Batch Configuration for Department Processing | Batch processing, checkpoint resumability | 2.1, 1.7 |

**Output:** `checkpoints/phase-1-relevant-departments.jsonl`

---

## Epic 3: Professor Discovery & Filtering

**Goal:** Identify professors, filter by research alignment, provide confidence scores and transparency.

**Status:** Ready for Development
**Story Count:** 5
**Dependencies:** Epic 2

| Story | Title | Key Deliverables | Dependencies |
|-------|-------|------------------|--------------|
| **3.1** | Multi-Agent Professor Discovery | Professor discovery agent, Professor model | 2.3, 1.7 |
| **3.2** | LLM-Based Professor Research Field Filtering | LLM filtering, relevance fields on Professor model | 3.1, 1.7 |
| **3.3** | Confidence Scoring for Filtering Decisions | Confidence scores, borderline cases report | 3.2 |
| **3.4** | Filtered Professor Logging & Transparency | Filtered professors report, manual overrides | 3.2 |
| **3.5** | Batch Processing for Professor Analysis | Async batch processing, checkpoint resumability | 3.1, 3.2, 1.7 |

**Output:** `checkpoints/phase-2-professors-filtered-batch-*.jsonl`

---

## Epic 4: Lab Website Intelligence & Contact Extraction

**Goal:** Scrape lab websites, analyze freshness via Archive.org, extract contacts, handle missing data.

**Status:** Ready for Development (Enhanced)
**Story Count:** 5
**Dependencies:** Epic 3

| Story | Title | Key Deliverables | Dependencies |
|-------|-------|------------------|--------------|
| **4.1** | Lab Website Discovery & Scraping | Lab model, website scraping, content extraction | 3.5 |
| **4.2** | Archive.org Integration for Website History | waybackpy integration, update frequency calculation | 4.1 |
| **4.3** | Contact Information Extraction | Email extraction, contact forms, application URLs | 4.1 |
| **4.4** | Graceful Handling of Missing/Stale Websites | Website status detection, alternative data strategy | 4.1, 4.2 |
| **4.5** | Web Scraping Error Handling & Retry Logic | Tiered fallback, retry logic, rate limiting, robots.txt | 4.1 |

**Output:** `checkpoints/phase-3-labs-batch-*.jsonl`

**Note:** Stories 4.2-4.5 enhanced with comprehensive Dev Notes and testing requirements.

---

## Epic 5: Publication Research & Member Identification

**Goal:** Retrieve publications via MCP, analyze abstracts, weight by journal reputation, infer lab members from co-authorship.

**Status:** Ready for Development
**Story Count:** 5
**Dependencies:** Epic 4

| Story | Title | Key Deliverables | Dependencies |
|-------|-------|------------------|--------------|
| **5.1** | MCP Integration for Publication Retrieval | Publication model, paper-search-mcp integration | 4.1, 1.5 |
| **5.2** | Abstract & Acknowledgment Analysis | LLM abstract analysis, relevance scoring | 5.1, 1.7 |
| **5.3** | Journal Reputation Weighting | SJR integration, reputation scoring | 5.1 |
| **5.4** | Lab Member Publication Discovery | Member publication retrieval, aggregation | 5.1, 4.1 |
| **5.5** | Lab Member Inference from Co-Authorship | Co-authorship analysis, member inference | 5.1, 4.4 |

**Output:** `checkpoints/phase-4-publications-batch-*.jsonl`

**Parallel Execution:** Can run in parallel with Epic 6 (both depend on Epic 4).

---

## Epic 6: LinkedIn Integration & PhD Position Detection

**Goal:** Match lab members to LinkedIn profiles via mcp-linkedin MCP server, detect graduating PhDs.

**Status:** Ready for Development (Validated - uses mcp-linkedin MCP)
**Story Count:** 3 (reduced from 5: removed 6.2 Parallel Access, 6.5 Error Handling - SDK handles these)
**Dependencies:** Epic 4

| Story | Title | Key Deliverables | Dependencies |
|-------|-------|------------------|--------------|
| **6.1** | mcp-linkedin MCP Server Integration | LinkedIn MCP integration, connection handling, error handling, data quality flags | 4.1, 1.5 |
| **6.2** | LinkedIn Profile Matching with Confidence Scores | LabMember model, LLM matching, confidence scores | 6.1, 1.7 |
| **6.3** | PhD Graduation & Departure Detection | Graduation detection, position availability signals | 6.2 |

**Output:** Updated `checkpoints/phase-3-labs-batch-*.jsonl` (with LinkedIn data)

**Critical:** Uses **mcp-linkedin MCP server** (NOT Playwright queue) as per architecture.

**Parallel Execution:** Can run in parallel with Epic 5 (both depend on Epic 4).

---

## Epic 7: Authorship Analysis & Fitness Scoring

**Goal:** Analyze authorship patterns, classify core vs. collaborator, identify collaborations, dynamically score lab fitness.

**Status:** Ready for Development
**Story Count:** 5
**Dependencies:** Epics 5 & 6

| Story | Title | Key Deliverables | Dependencies |
|-------|-------|------------------|--------------|
| **7.1** | Authorship Pattern Analysis | Authorship metrics, AuthorshipAnalysis model | 5.1 |
| **7.2** | Core vs. Collaborator Assessment | LLM-based role classification | 7.1, 1.7 |
| **7.3** | Collaboration Network Identification | Collaborator extraction, network analysis | 5.1, 5.2 |
| **7.4** | LLM-Driven Fitness Scoring Criteria | Dynamic criteria identification, weighting | 1.7 |
| **7.5** | Multi-Factor Fitness Scoring Execution | Fitness score calculation, scoring rationale | 7.1, 7.2, 7.3, 7.4 |

**Output:** Updated `checkpoints/phase-3-labs-batch-*.jsonl` (with fitness scores)

---

## Epic 8: Comprehensive Report Generation

**Goal:** Generate ranked overview report, comparison matrix, actionable next steps, detailed lab reports, data quality flags.

**Status:** Ready for Development
**Story Count:** 5
**Dependencies:** Epic 7

| Story | Title | Key Deliverables | Dependencies |
|-------|-------|------------------|--------------|
| **8.1** | Overview Report with Ranked Labs | Overview.md with ranked labs, summary stats | 7.5 |
| **8.2** | Comparison Matrix for Top Labs | Comparison matrix table, top 10 labs | 8.1 |
| **8.3** | Actionable Next Steps & Priority Recommendations | Next steps section, priority recommendations | 8.1 |
| **8.4** | Detailed Individual Lab Reports | Individual lab reports in labs/ directory | 8.1 |
| **8.5** | Data Quality Issue Flagging | Data quality flags in all reports | 8.1 |

**Output:**
- `output/Overview.md`
- `output/labs/*.md` (individual lab reports)

---

## Story Dependencies Graph

```
Epic 1: Foundation
├── 1.0 ★ FIRST - project scaffolding
├── 1.1 (depends on 1.0)
├── 1.2 → 1.3 → 1.4 (sequential, depend on 1.1)
├── 1.5 (parallel with 1.2-1.4, depends on 1.1)
├── 1.6 (parallel with 1.2-1.5, depends on 1.1)
├── 1.7 (depends on 1.6) ★ CRITICAL - all Epic 2+ depend on this
└── 1.8 (optional, parallel with 1.2-1.7)

Epic 2: University Discovery
├── 2.1 (depends on 1.7)
├── 2.2 (depends on 2.1)
├── 2.3 (depends on 2.1, 1.7)
├── 2.4 (depends on 2.1)
└── 2.5 (depends on 2.1, 1.7)

Epic 3: Professor Discovery
├── 3.1 (depends on 2.3, 1.7)
├── 3.2 (depends on 3.1, 1.7)
├── 3.3 (depends on 3.2)
├── 3.4 (depends on 3.2)
└── 3.5 (depends on 3.1, 3.2, 1.7)

Epic 4: Lab Intelligence
├── 4.1 (depends on 3.5)
├── 4.2 (depends on 4.1)
├── 4.3 (depends on 4.1)
├── 4.4 (depends on 4.1, 4.2)
└── 4.5 (depends on 4.1)

Epic 5: Publication Research (PARALLEL with Epic 6)
├── 5.1 (depends on 4.1, 1.5)
├── 5.2 (depends on 5.1, 1.7)
├── 5.3 (depends on 5.1)
├── 5.4 (depends on 5.1, 4.1)
└── 5.5 (depends on 5.1, 4.4)

Epic 6: LinkedIn Integration (PARALLEL with Epic 5)
├── 6.1 (depends on 4.1, 1.5) [includes error handling from removed 6.5]
├── 6.2 (depends on 6.1, 1.7) [formerly 6.3]
└── 6.3 (depends on 6.2) [formerly 6.4]

Note: Stories 6.2 (Parallel Access) and 6.5 (Error Handling) removed - functionality handled by Claude Agent SDK and merged into 6.1

Epic 7: Fitness Scoring
├── 7.1 (depends on 5.1)
├── 7.2 (depends on 7.1, 1.7)
├── 7.3 (depends on 5.1, 5.2)
├── 7.4 (depends on 1.7)
└── 7.5 (depends on 7.1, 7.2, 7.3, 7.4)

Epic 8: Report Generation
├── 8.1 (depends on 7.5)
├── 8.2 (depends on 8.1)
├── 8.3 (depends on 8.1)
├── 8.4 (depends on 8.1)
└── 8.5 (depends on 8.1)
```

---

## Key Data Models by Epic

### Epic 1 (Foundation)
- `UserProfile` - Consolidated user research profile

### Epic 2 (University Discovery)
- `Department` - University department with hierarchy

### Epic 3 (Professor Discovery)
- `Professor` - Professor with research areas and filter results

### Epic 4 (Lab Intelligence)
- `Lab` - Lab with website data, contacts, status

### Epic 5 (Publication Research)
- `Publication` - Paper with metadata, relevance score

### Epic 6 (LinkedIn Integration)
- `LabMember` - Lab member with LinkedIn data, graduation info

### Epic 7 (Fitness Scoring)
- `AuthorshipAnalysis` - Authorship patterns
- `ScoringCriteria` - Fitness scoring criteria

### Epic 8 (Report Generation)
- No new models (generates reports from existing data)

---

## Checkpoint Files Generated

| Phase | Checkpoint File(s) | Epic | Format |
|-------|-------------------|------|--------|
| Phase 0 | `checkpoints/phase-0-validation.json` | 1 | JSON |
| Phase 1 | `checkpoints/phase-1-departments.jsonl` | 2 | JSONL |
| Phase 1 | `checkpoints/phase-1-relevant-departments.jsonl` | 2 | JSONL |
| Phase 2 | `checkpoints/phase-2-professors-batch-*.jsonl` | 3 | JSONL (batched) |
| Phase 2 | `checkpoints/phase-2-professors-filtered-batch-*.jsonl` | 3 | JSONL (batched) |
| Phase 3 | `checkpoints/phase-3-labs-batch-*.jsonl` | 4, 6 | JSONL (batched) |
| Phase 4 | `checkpoints/phase-4-publications-batch-*.jsonl` | 5 | JSONL (batched) |

**Note:** All checkpoints use JSONL format for streaming support and batch-level resumability.

---

## Story File Locations

All user stories located in: `docs/stories/`

**Naming Convention:** `{epic}.{story}-{short-name}.md`

**Examples:**
- `1.0.project-initialization.md`
- `1.1.project-setup.md`
- `1.8.ci-cd-pipeline-setup.md` (optional)
- `2.3.department-relevance-filtering.md`
- `6.2.linkedin-profile-matching.md` (formerly 6.3)

---

## Testing Strategy by Epic

### Epic 1
- **Focus:** Unit tests for utilities, integration tests for config validation
- **Coverage:** 70% minimum
- **Key Tests:** checkpoint_manager, llm_helpers, progress_tracker, logger

### Epic 2
- **Focus:** Integration tests with mock HTML, unit tests for models
- **Coverage:** 70% minimum
- **Key Tests:** Department discovery, LLM filtering, batch processing

### Epic 3
- **Focus:** Unit tests with mock LLM, integration tests for discovery
- **Coverage:** 70% minimum
- **Key Tests:** Professor discovery, confidence scoring, async batch processing

### Epic 4
- **Focus:** Integration tests for web scraping, unit tests for error handling
- **Coverage:** 70% minimum
- **Key Tests:** Wayback Machine API, contact extraction, graceful degradation

### Epic 5
- **Focus:** Integration tests with mock MCP, unit tests for analysis
- **Coverage:** 70% minimum
- **Key Tests:** MCP integration, abstract analysis, co-authorship inference

### Epic 6
- **Focus:** Integration tests with mock mcp-linkedin, unit tests for matching
- **Coverage:** 70% minimum
- **Key Tests:** MCP integration, LLM matching, graduation detection

### Epic 7
- **Focus:** Unit tests for scoring logic, integration tests for LLM criteria
- **Coverage:** 70% minimum
- **Key Tests:** Authorship analysis, fitness scoring, collaboration network

### Epic 8
- **Focus:** Integration tests for report generation, unit tests for formatting
- **Coverage:** 70% minimum
- **Key Tests:** Markdown generation, comparison matrix, data quality flags

---

## Critical Technology Notes

### Story 1.5 & 1.7
- **MCP Servers Required:** paper-search-mcp, mcp-linkedin
- **Must Configure:** LinkedIn credentials in mcp-linkedin server (NOT in code)

### Story 1.6
- **Testing Framework:** pytest 7.4.4 with asyncio, mock, coverage plugins
- **Must Complete:** Before any Epic 2+ stories with test requirements

### Story 1.7
- **Critical Utilities:** checkpoint_manager, llm_helpers, progress_tracker, logger
- **Must Complete:** Before all Epic 2+ stories (they depend on these utilities)

### Story 4.2
- **Library Added:** waybackpy 3.0.6 (added to architecture tech stack)

### Epic 6 (All Stories)
- **Architecture:** Uses mcp-linkedin MCP server (NOT Playwright queue)
- **MCP Handles:** Authentication, session management, rate limiting

---

## Quick Reference: Story Statuses

All 44 stories have status: **Draft** (ready for development)

**Note:** Story 1.8 (CI/CD Pipeline Setup) is marked as **Optional** - implement based on team size and development workflow preferences.

**Validation Results:**
- ✅ All stories validated and ready
- ✅ Architecture alignment confirmed
- ✅ Dependencies verified
- ✅ Tech stack complete
- ✅ Epic 6 correctly uses mcp-linkedin MCP

---

## Development Sprint Recommendations

### Sprint 1: Foundation (2 weeks)
- Stories 1.0-1.7 (Epic 1 core complete)
- Story 1.8 (optional CI/CD) - implement if desired
- **Deliverable:** Working foundation with all utilities

### Sprint 2: University & Professor Discovery (2 weeks)
- Stories 2.1-2.5, 3.1-3.5 (Epics 2-3 complete)
- **Deliverable:** Filtered professor list with confidence scores

### Sprint 3: Lab Intelligence (2 weeks)
- Stories 4.1-4.5 (Epic 4 complete)
- **Deliverable:** Lab data with website intelligence

### Sprint 4: Publications & LinkedIn (2 weeks, parallel)
- Stories 5.1-5.5, 6.1-6.3 (Epics 5-6 complete, parallel execution)
- **Deliverable:** Publication data + LinkedIn matching
- **Note:** Epic 6 reduced from 5 to 3 stories (6.2, 6.5 removed - SDK handles parallel execution and error handling)

### Sprint 5: Scoring & Reporting (2 weeks)
- Stories 7.1-7.5, 8.1-8.5 (Epics 7-8 complete)
- **Deliverable:** Final reports with ranked labs

**Total Estimated Timeline:** 10 weeks (5 sprints)

---

## Additional Resources

- **Architecture Document:** `docs/architecture.md`
- **PRD:** `docs/prd.md`
- **Validation Report:** See QA agent validation (35 stories, 100% pass rate)

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-06 | 1.0 | Initial story index creation | Sarah (PO) |

---

**End of Story Index**
