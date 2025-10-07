# Lab Finder Product Requirements Document (PRD)

## Goals and Background Context

### Goals

- Enable efficient identification of best-fit research labs based on user's academic profile and research interests
- Automate professor and lab discovery process within a target university
- Provide comprehensive lab intelligence including recent publications, collaborations, and team composition
- Identify potential position openings through graduating PhD detection
- Assess lab engagement levels through authorship pattern analysis (first author vs. nth author, core vs. collaborator roles)
- Generate ranked reports to facilitate informed lab selection decisions

### Background Context

Finding the right research lab is a time-consuming process that requires synthesizing information from multiple sources: professor directories, lab websites, recent publications, and team member profiles. This tool addresses the need for a systematic, automated approach to lab research by leveraging the Claude Agent SDK's web scraping capabilities.

The system consolidates a user's academic profile (resume, degree program, research interests) to create a baseline for relevance matching, then systematically discovers, filters, and analyzes labs within a target university. By examining website freshness, publication patterns, authorship roles, and team composition, it provides actionable intelligence about lab activity levels and potential opportunities. The output is a ranked overview with detailed per-lab reports to support decision-making.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-06 | 0.1 | Initial PRD draft | John (pm agent) |

---

## Requirements

### Functional Requirements

#### Phase 0: Validation & Setup

**FR1:** The system configuration shall be validated against a JSON schema before execution

**FR2:** The system shall support Playwright-based authentication with credentials from configuration file to access LinkedIn and university resources requiring authentication

**FR3:** The system shall prompt users via CLI to collect and save credentials to configuration file when authentication is required but credentials are not present

**FR4:** The system shall accept user input including resume, current degree program, university, department, and research interests from separate JSON configuration sources

**FR5:** The system shall accept a configurable average PhD graduation duration value (e.g., 5.5 years) from configuration

**FR6:** The system shall combine structured JSON configuration (university name, core website link, directory link, etc.) with extracted resume highlights and streamlined research interest statements into a consolidated research profile document

#### Phase 1: University Structure Discovery

**FR7:** The system shall automatically discover and map the university's department structure (including multi-layered hierarchies such as schools, divisions, and departments)

**FR8:** The system shall represent the discovered department structure in JSON format to enable sub-agent delegation for professor discovery within specific departments

**FR9:** The system shall filter departments based on research relevance before initiating professor discovery to optimize performance

#### Phase 2: Professor Discovery & Filtering

**FR10:** The system shall identify professors within the specified university, including their department and lab affiliations, accounting for multi-layered department structures (e.g., medical schools, engineering subdivisions)

**FR11:** The system shall filter professors using LLM-based analysis, including if ANY major field matches the user's research interests (supporting interdisciplinary researchers)

**FR12:** The system shall provide confidence scores for LLM-based professor filtering decisions

**FR13:** The system shall log and report professors/labs that were filtered out with reasoning for user validation

#### Phase 3: Lab Research & Data Collection

**FR14:** The system shall scrape lab websites to determine the last update date and utilize Archive.org (Wayback Machine) to identify website change history

**FR15:** The system shall identify recent research papers (last 3 years) published by the Principal Investigator (PI) using paper-search-mcp

**FR16:** The system shall identify recent research papers (last 3 years) published by lab members using paper-search-mcp

**FR17:** The system shall use a configurable journal reputation database (e.g., SJR, Impact Factor) for publication weighting

**FR18:** The system shall identify lab collaborations with other research groups

**FR19:** The system shall identify current lab members

**FR20:** The system shall extract professor contact information (email addresses, lab website contact forms, application URLs) where available

**FR30:** The system shall analyze paper abstracts and acknowledgment sections (rather than full text) to optimize for research alignment and collaboration pattern identification

**FR31:** When lab websites are stale or missing, the system shall infer lab members from co-authorship patterns in the professor's recent 3-year publications

#### Phase 4: Advanced Analysis

**FR21:** The system shall detect graduating PhD students and recently departed PhDs by combining the configured average graduation duration with LinkedIn data (entry year) to identify potential position openings

**FR22:** The system shall use LLM-based matching to verify whether individuals listed on lab websites match LinkedIn profiles with confidence scores

**FR23:** The system shall analyze authorship patterns in publications to determine if lab members/PI are first author or nth author

**FR24:** The system shall assess whether the lab is in a core research position or a collaborator role based on publication authorship patterns

#### Phase 5: Scoring & Output

**FR25:** The system shall use Claude (LLM) to dynamically identify and apply lab fitness scoring criteria, considering factors such as (but not limited to): paper content alignment with user research interests, journal reputation weighting, authorship patterns indicating core vs. collaborative work, and PhD departure timing

**FR26:** The system shall generate an Overview.md report showing all labs ranked by fitness with performance metrics and scoring rationale

**FR27:** The system shall include actionable next steps in the Overview.md report, including priority recommendations (e.g., "Top 3 priority labs to contact based on fitness + position availability")

**FR28:** The system shall generate a comparison matrix in the Overview.md showing key metrics across top-ranked labs for side-by-side evaluation

**FR29:** The system shall generate detailed individual lab reports in a ./labs directory

**FR32:** The system shall document data quality issues, missing information, and inference-based results in the generated reports with appropriate flags

### Non-Functional Requirements

**NFR1:** The system shall be built using the Claude Agent SDK (formerly Claude Code SDK) as the core framework

**NFR2:** The system shall utilize a multi-agent architecture with support for parallel execution where applicable

**NFR3:** The system shall process one university per execution run

**NFR4:** The system shall execute professor filtering (FR11) and subsequent lab research/analysis steps (FR14-FR24) in configurable batch sizes to limit concurrent parallel agents and Playwright instances

**NFR5:** The system shall use Claude Agent SDK built-in web tools as primary method, with Playwright as fallback when built-in tools fail

**NFR6:** The system shall utilize MCP (Model Context Protocol) servers for web capabilities, including paper-search-mcp for publication retrieval

**NFR7:** The system shall be implemented in Python

**NFR8:** The system shall support single-user workflows only (not multi-user)

**NFR9:** The system shall be designed as a one-off execution tool rather than a continuous service

**NFR10:** The system shall handle web scraping ethically with appropriate rate limiting and respect for robots.txt

**NFR11:** The system shall implement configurable rate limiting per data source to prevent blocking

**NFR12:** The system shall persist intermediate results (department structure, professor lists, publication data, analysis results) at each phase to enable resumability

**NFR13:** The system shall handle common failure scenarios (unavailable websites, blocked scraping, missing data) with graceful degradation and clear error reporting

**NFR14:** The system shall provide clear progress indicators during the multi-stage research process

**NFR15:** The system shall generate human-readable markdown reports suitable for review and comparison

**NFR16:** The system shall use a single shared Playwright browser session for LinkedIn access, with subagents queuing for sequential access to prevent repeated logins and minimize ban risk

**NFR17:** The system shall provide detailed logging of all failures, missing data, and inference-based decisions for user review

---

## User Interface Design Goals

*Not applicable - This is a CLI-only tool with no UI requirements*

---

## Technical Assumptions

### Repository Structure: Monorepo

**Rationale:** Single Python project with multi-agent architecture; no need for separate repos

### Service Architecture: Monolithic Application with Multi-Agent Orchestration

**Rationale:** One-off execution tool (NFR9) with coordinated subagents; not a distributed service. The Claude Agent SDK handles agent orchestration within a single process.

### Testing Requirements: Unit + Integration Testing

**Rationale:**
- Unit tests for data processing, filtering logic, scoring algorithms
- Integration tests for web scraping workflows, MCP interactions
- Manual testing for end-to-end university analysis runs
- No continuous deployment or production users, so minimal E2E automation needed

### Additional Technical Assumptions and Requests

**Language & Framework:**
- Python 3.11+ (for modern async features)
- Claude Agent SDK (core framework per NFR1)
- Playwright for browser automation fallback (NFR5)

**Data Sources & APIs:**
- paper-search-mcp for publication retrieval (NFR6)
- Archive.org Wayback Machine API for website history (FR14)
- LinkedIn (authenticated via Playwright, NFR16)
- Configurable journal reputation database (SJR/Impact Factor) (FR17)

**Configuration Management:**
- JSON Schema for validation (FR1)
- Multiple JSON config files: user profile, university details, system parameters (FR4)
- Credential storage with CLI prompts for missing values (FR2-FR3)

**Data Persistence:**
- File-based checkpointing (JSON/JSONL) for resumability (NFR12)
- No database required - intermediate results saved to filesystem
- Report outputs: Markdown files (FR26-FR29)

**Concurrency & Performance:**
- Multi-agent architecture with configurable batch processing (NFR2, NFR4)
- MCP server integration for LinkedIn access with SDK-managed rate limiting (NFR16, NFR11)
- Configurable rate limiting per source (NFR11)
- Parallel department/professor discovery where possible

**Error Handling & Logging:**
- Detailed logging framework (NFR17)
- Graceful degradation for missing data (NFR13, FR31-FR32)
- Progress indicators for long-running operations (NFR14)

**Deployment:**
- Local execution only (one-off tool)
- No containerization required unless user requests
- Virtual environment for dependency isolation

---

## Epic List

### Epic 1: Foundation & Configuration Infrastructure
Establish project setup, configuration management with JSON schema validation, credential handling, and user profile consolidation to create the research baseline document.

### Epic 2: University Structure Discovery & Department Filtering
Implement multi-agent department structure discovery, JSON representation for delegation, and LLM-based department relevance filtering.

### Epic 3: Professor Discovery & Filtering
Build multi-agent professor identification across filtered departments, LLM-based research field matching (ANY major field), confidence scoring, and filtered professor logging with reasoning.

### Epic 4: Lab Website Intelligence & Contact Extraction
Develop web scraping capabilities (built-in tools + Playwright fallback) to gather lab websites, member identification, and contact information extraction. **Executes in parallel with Epic 5A for 15-20% timeline reduction.**

### Epic 5A: PI Publication Research (Parallel with Epic 4)
Integrate paper-search-mcp for PI publications (3-year window), abstract and acknowledgment parsing, and journal reputation weighting. **Runs concurrently with Epic 4** to optimize pipeline performance.

### Epic 5B: Lab Member Publications & Inference
Retrieve publications for lab members identified in Epic 4, and infer lab members from co-authorship patterns when websites are unavailable or stale (using PI publications from Epic 5A).

### Epic 6: LinkedIn Integration & PhD Position Detection
Implement mcp-linkedin MCP server integration for LinkedIn profile access, LLM-based person matching with confidence scores, and graduating/departed PhD detection using configurable graduation duration.

### Epic 7: Authorship Analysis & Fitness Scoring
Build authorship pattern analysis (first/nth author), core vs. collaborator assessment, collaboration identification, and LLM-driven fitness scoring with dynamically identified criteria and weighted factors.

### Epic 8: Comprehensive Report Generation
Create comprehensive reporting system with ranked Overview.md, comparison matrix, actionable recommendations, detailed individual lab reports, and data quality flagging.

---

## Epic Details

### Epic 1: Foundation & Configuration Infrastructure

**Goal:** Establish the project's foundational infrastructure including configuration management with JSON schema validation, credential handling, and user profile consolidation. This epic delivers a working configuration system that validates inputs, securely manages credentials, and produces the consolidated research profile document that drives all subsequent lab matching.

#### Story 1.1: Project Setup & Dependency Management

As a **user**,
I want **the project initialized with proper Python environment, Claude Agent SDK, and all required dependencies**,
so that **I have a working foundation to build upon**.

**Acceptance Criteria:**
1. Python 3.11+ environment created with virtual environment support
2. Claude Agent SDK installed and configured
3. Playwright installed with browser drivers
4. Project directory structure created (src/, config/, output/, logs/)
5. Requirements.txt or pyproject.toml with all dependencies
6. Basic README with setup instructions

#### Story 1.2: JSON Configuration Schema & Validation

As a **user**,
I want **my configuration files validated against a JSON schema before execution**,
so that **I catch configuration errors early instead of during long-running analysis**.

**Acceptance Criteria:**
1. JSON schemas defined for: user profile config, university config, system parameters config
2. Schema validation logic implemented with clear error messages
3. Validation runs before any processing begins (FR1)
4. Missing required fields identified with helpful guidance
5. Type mismatches and invalid values caught with specific feedback
6. Example configuration files provided with inline comments

#### Story 1.3: Credential Management with CLI Prompts

As a **user**,
I want **the system to prompt me for missing credentials and save them securely**,
so that **I don't have to manually edit configuration files or re-enter credentials on each run**.

**Acceptance Criteria:**
1. System checks for required credentials (LinkedIn, university portal if needed) at startup (FR2)
2. CLI prompts appear for missing credentials with clear instructions (FR3)
3. Credentials saved to configuration file with appropriate permissions/encryption
4. Existing credentials loaded from config without prompting
5. Option to update/refresh stored credentials
6. Credentials never logged or displayed in plain text

#### Story 1.4: Shared Utilities Implementation

As a **developer**,
I want **core shared utility modules (checkpoint_manager, llm_helpers, progress_tracker, logger) implemented before phase agents**,
so that **all subsequent agent implementations can use consistent checkpoint handling, LLM prompting, progress tracking, and logging patterns**.

**Acceptance Criteria:**
1. `src/utils/checkpoint_manager.py` created with save_batch, load_batches, get_resume_point, mark_phase_complete functions
2. `src/utils/llm_helpers.py` created with centralized LLM prompt templates for common operations
3. `src/utils/progress_tracker.py` created wrapping rich library for consistent progress bars
4. `src/utils/logger.py` created with structlog configuration including correlation IDs and phase context
5. All utilities have type hints and pass mypy type checking
6. Unit tests written for all utility modules (70% coverage minimum)
7. Example usage documented in each utility module's docstring

#### Story 1.5: MCP Server Configuration & Testing

As a **developer/user**,
I want **MCP servers (paper-search-mcp and mcp-linkedin) installed, configured, and validated before implementing publication retrieval and LinkedIn matching features**,
so that **Epic 5 and Epic 6 can proceed without blocking on missing external dependencies**.

**Acceptance Criteria:**
1. paper-search-mcp MCP server installed and accessible
2. mcp-linkedin MCP server installed with LinkedIn credentials configured
3. Both MCP servers tested with basic connectivity checks
4. MCP server configuration documented in project README
5. Error handling implemented for MCP server unavailability
6. Fallback behavior defined when MCP servers fail (skip with data quality flags)
7. MCP client wrapper utility (`src/utils/mcp_client.py`) created for consistent server interaction

#### Story 1.6: Testing Infrastructure Setup

As a **developer**,
I want **a complete testing infrastructure established with pytest framework, test directory structure, and example test templates**,
so that **I can write and run tests effectively for all subsequent stories starting from Epic 2**.

**Acceptance Criteria:**
1. pytest and all testing dependencies installed (pytest, pytest-cov, pytest-asyncio, pytest-mock)
2. Test directory structure created matching source structure (`tests/unit/`, `tests/integration/`, `tests/fixtures/`)
3. pytest configuration file created (pytest.ini) with coverage settings
4. Example test templates provided for unit and integration tests
5. Test execution successfully runs with `pytest` command
6. Coverage reporting configured to generate reports
7. Testing documentation added to README with examples

#### Story 1.7: User Profile Consolidation

As a **user**,
I want **my resume, degree program, university details, and research interests combined into a single coherent research profile document**,
so that **the system has clear baseline for matching me with relevant labs**.

**Acceptance Criteria:**
1. System reads multiple JSON config sources (resume highlights, degree info, research interests, university details) (FR4)
2. Resume content parsed and key highlights extracted (education, skills, research experience)
3. Research interest statements streamlined and clarified using LLM
4. Consolidated profile document generated in markdown format (FR6)
5. Profile includes: background, current degree program, target university, research interests, key qualifications
6. Profile saved to output directory for user review
7. Profile used as input for all subsequent filtering and matching operations

---

### Epic 2: University Structure Discovery & Department Filtering

**Goal:** Automatically discover and map the target university's complete department hierarchy (schools, divisions, departments), represent it in JSON format for sub-agent delegation, and filter out irrelevant departments before professor discovery. This epic delivers a validated department structure that optimizes subsequent processing.

**Execution Model:** Three-phase approach with parallel execution in Phase 1 and Phase 3 for ~33% timeline reduction

**Timeline:** ~7 days (vs. 10.5 days sequential)

**Phase Flow:**
- **Phase 1 (Parallel):** Infrastructure setup (Stories 2.4 || 2.5) - ~2 days
- **Phase 2 (Sequential):** Core discovery (Story 2.1) - ~3 days
- **Phase 3 (Parallel):** Post-processing (Stories 2.2 || 2.3) - ~2 days

---

#### Phase 1: Infrastructure Setup (PARALLEL)

##### Story 2.4: Error Handling for Missing Structure Data

As a **user**,
I want **the system to handle cases where department structure is unclear or incomplete**,
so that **analysis continues with graceful degradation instead of failing**.

**Acceptance Criteria:**
1. System identifies when structure discovery is incomplete or ambiguous (NFR13)
2. User notified of structure gaps with specific details
3. Partial structure data saved and used where available
4. Fallback: Process all discoverable departments even if hierarchy unclear
5. Data quality issues flagged in output (FR32)
6. Detailed logging of what couldn't be discovered (NFR17)

**Execution Dependencies:**
- **Can Start After:** Epic 1 complete (specifically Story 1.4 for shared utilities)
- **Parallel Execution:** Can run in parallel with Story 2.5
- **Blocks:** Story 2.1 (provides error handling infrastructure)
- **Provides:** Data quality flags, retry logic, graceful degradation patterns, error logging infrastructure

##### Story 2.5: Batch Configuration for Department Processing

As a **user**,
I want **department processing configured to run in reasonable batches**,
so that **the system doesn't overwhelm resources with parallel operations**.

**Acceptance Criteria:**
1. Configurable batch size for parallel department processing (NFR4)
2. Default batch size set to reasonable value (e.g., 5 departments at a time)
3. Batch size configurable in system parameters JSON
4. Progress tracking shows current batch and remaining batches
5. Checkpointing between batches for resumability (NFR12)

**Execution Dependencies:**
- **Can Start After:** Epic 1 complete (specifically Story 1.4 for checkpoint_manager)
- **Parallel Execution:** Can run in parallel with Story 2.4
- **Blocks:** Story 2.1 (provides batch processing infrastructure)
- **Provides:** Batch configuration system, batch-level checkpointing, resume from checkpoint logic

---

#### Phase 2: Core Discovery (SEQUENTIAL)

##### Story 2.1: University Website Structure Discovery

As a **user**,
I want **the system to automatically discover my target university's organizational structure**,
so that **it can comprehensively search all relevant departments without manual mapping**.

**Acceptance Criteria:**
1. System uses university core website link from config to discover structure (FR7)
2. Multi-layered hierarchies identified (schools → divisions → departments)
3. Department names, URLs, and relationships extracted
4. Built-in web tools used as primary method for discovery (NFR5)
5. Playwright fallback with screenshots when built-in tools fail
6. Progress indicators show discovery status (NFR14)

**Execution Dependencies:**
- **Can Start After:** Stories 2.4 AND 2.5 complete
- **Required Infrastructure:**
  - Story 2.4: Error handling, retry logic, data quality flags
  - Story 2.5: Batch configuration, checkpointing, resume logic
- **Blocks:** Stories 2.2 and 2.3
- **Output:** Raw discovered departments → Phase 3

---

#### Phase 3: Post-Processing (PARALLEL)

##### Story 2.2: Department Structure JSON Representation

As a **user**,
I want **the discovered department structure saved in JSON format**,
so that **sub-agents can be delegated to process specific departments in parallel**.

**Acceptance Criteria:**
1. Department hierarchy represented in structured JSON (FR8)
2. JSON includes: school name, division name, department name, department URL, hierarchy level
3. JSON enables easy iteration and sub-agent delegation
4. File saved as intermediate result for resumability (NFR12)
5. Human-readable formatting for manual review if needed
6. Schema supports multi-level hierarchies (minimum 3 levels deep)

**Execution Dependencies:**
- **Can Start After:** Story 2.1 complete
- **Parallel Execution:** Can run in parallel with Story 2.3
- **Blocks:** None (documentation artifact)
- **Input:** Raw discovered departments from 2.1
- **Output:** Hierarchical JSON (for documentation/review)

##### Story 2.3: Department Relevance Filtering

As a **user**,
I want **irrelevant departments filtered out before professor discovery**,
so that **the system doesn't waste time scraping departments with no relevant labs**.

**Acceptance Criteria:**
1. LLM analyzes each department against user's consolidated research profile (FR9)
2. Departments with ANY potential research overlap are included
3. Obviously unrelated departments excluded (e.g., literature for bioengineering student)
4. Reasoning logged for each filtering decision (NFR17)
5. Filtered departments list saved for user review
6. Remaining departments list passed to next epic
7. Progress shows "Filtered X of Y departments"

**Execution Dependencies:**
- **Can Start After:** Stories 1.7 (user profile) AND 2.1 (discovered departments) complete
- **Parallel Execution:** Can run in parallel with Story 2.2
- **Blocks:** Epic 3 (provides filtered department list)
- **Input:** Raw discovered departments from 2.1
- **Output:** Filtered departments → Epic 3

---

### Epic 3: Professor Discovery & Filtering

**Goal:** Identify all professors within filtered departments, extract their lab affiliations and research areas, then use LLM-based analysis to filter professors whose research significantly deviates from the user's interests. This epic delivers a curated list of relevant professors with confidence scores and transparent filtering rationale.

#### Story 3.1: Multi-Agent Professor Discovery

As a **user**,
I want **professors identified across all relevant departments using parallel sub-agents**,
so that **discovery is efficient even for large universities**.

**Acceptance Criteria:**
1. Sub-agents created for each department (or batch of departments) from Epic 2 output (FR10)
2. Professor directory pages discovered and scraped
3. Professor names, titles, department affiliations extracted
4. Lab affiliations identified where available
5. Research area descriptions extracted from directory listings
6. Built-in web tools used with Playwright fallback (NFR5)
7. Results aggregated from all sub-agents into master professor list

#### Story 3.2: LLM-Based Professor Research Field Filtering

As a **user**,
I want **professors filtered based on research field alignment with my interests**,
so that **I only analyze labs that are potentially good fits**.

**Acceptance Criteria:**
1. LLM analyzes each professor's research areas against user profile (FR11)
2. Matching logic: Include if ANY major research field overlaps with user interests
3. Interdisciplinary researchers appropriately handled (not over-filtered)
4. Major deviations excluded (e.g., literature professor for bioengineering student)
5. Edge cases handled: emerging fields, multi-disciplinary labs, co-appointments
6. Filtering uses consolidated research profile from Epic 1

#### Story 3.3: Confidence Scoring for Filtering Decisions

As a **user**,
I want **confidence scores provided for each filtering decision**,
so that **I can review borderline cases and understand the system's certainty**.

**Acceptance Criteria:**
1. Confidence score (0-100) generated for each professor filtering decision (FR12)
2. Score reflects LLM's certainty about research field alignment
3. Low-confidence decisions (e.g., <70%) flagged for user review
4. Confidence scores saved with professor records
5. Thresholds configurable in system parameters
6. Score rationale includes key matching factors

#### Story 3.4: Filtered Professor Logging & Transparency

As a **user**,
I want **detailed logs of filtered-out professors with reasoning**,
so that **I can validate the system didn't miss relevant labs**.

**Acceptance Criteria:**
1. All filtered professors logged with exclusion reasoning (FR13)
2. Log includes: professor name, department, research areas, confidence score, filter reason
3. Log saved to dedicated file (filtered-professors.md or similar)
4. Reasoning explains why research didn't align
5. User can review and manually add back professors if needed
6. Statistics provided: "Filtered X of Y professors (Z%)"

#### Story 3.5: Batch Processing for Professor Analysis

As a **user**,
I want **professor filtering executed in configurable batches**,
so that **the system manages parallel agents and API calls efficiently**.

**Acceptance Criteria:**
1. Professor list divided into batches based on config (NFR4)
2. Each batch processed before moving to next
3. Checkpoint saved after each batch completion (NFR12)
4. Progress indicators show: "Processing batch X of Y (Z professors)"
5. If execution interrupted, resumable from last completed batch
6. Batch size configurable (default: 10-20 professors per batch)

---

### Epic 4: Lab Website Intelligence & Contact Extraction

**Goal:** Scrape lab websites to gather foundational intelligence including last update dates, Archive.org change history, and contact information. Implement robust fallback strategies for missing or stale websites. This epic delivers baseline lab data independent of publication analysis.

#### Story 4.1: Lab Website Discovery & Scraping

As a **user**,
I want **lab websites discovered and scraped for each relevant professor**,
so that **I can assess lab activity through website maintenance and content**.

**Acceptance Criteria:**
1. Lab website URLs identified from professor directory or search (FR14)
2. Website content scraped using built-in web tools (NFR5)
3. Playwright fallback when built-in tools fail
4. Last modified/update date extracted where available
5. Lab description, research focus, news/updates extracted
6. Current website content saved for analysis
7. Missing websites flagged but don't block processing

#### Story 4.2: Archive.org Integration for Website History

As a **user**,
I want **website change history analyzed using Archive.org Wayback Machine**,
so that **I can identify stale labs with outdated websites**.

**Acceptance Criteria:**
1. Archive.org API queried for each lab website (FR14)
2. Most recent snapshot date identified
3. Snapshot dates over past 3 years collected
4. Change frequency calculated (e.g., updated monthly, yearly, not updated)
5. If current site unavailable, most recent snapshot used
6. Archive.org rate limiting respected (NFR11)
7. Missing snapshots handled gracefully (not all sites archived)

#### Story 4.3: Contact Information Extraction

As a **user**,
I want **professor and lab contact information extracted**,
so that **I can easily reach out to prioritized labs**.

**Acceptance Criteria:**
1. Email addresses extracted from lab websites and directory pages (FR20)
2. Contact form URLs identified
3. Application/prospective student URLs found if available
4. Contact information validated (basic email format check)
5. Multiple contact methods saved (direct email, lab email, contact form)
6. Missing contact info flagged but doesn't block processing

#### Story 4.4: Graceful Handling of Missing/Stale Websites

As a **user**,
I want **the system to handle missing or severely outdated websites gracefully**,
so that **these labs aren't excluded from analysis entirely**.

**Acceptance Criteria:**
1. Missing websites detected and flagged (NFR13, FR31)
2. Stale websites (>2 years since update) identified
3. Data quality issues logged for these labs (FR32)
4. System continues processing using alternative data sources (publications)
5. Reports clearly indicate "website unavailable" or "last updated: [date]"
6. No website failures cause entire analysis to fail

#### Story 4.5: Web Scraping Error Handling & Retry Logic

As a **user**,
I want **robust error handling for web scraping failures**,
so that **temporary issues don't derail the entire analysis**.

**Acceptance Criteria:**
1. Retry logic implemented for failed requests (NFR13)
2. Built-in tools tried first, then Playwright fallback (NFR5)
3. Rate limiting prevents being blocked (NFR10, NFR11)
4. robots.txt respected for ethical scraping
5. Timeout handling for slow-loading pages
6. All failures logged with details (NFR17)
7. Graceful degradation: partial data better than no data

---

### Epic 5A: PI Publication Research (Parallel with Epic 4)

**Goal:** Integrate paper-search-mcp to retrieve publications from the last 3 years for Principal Investigators, analyze abstracts and acknowledgments for research alignment and collaboration patterns, and weight publications by journal reputation. This epic delivers PI publication intelligence and **executes in parallel with Epic 4** to reduce overall timeline by 15-20%.

**Execution Model:** Stories 5.1-5.3 can begin immediately after Epic 3 completes (filtered professor list available). They do **not** depend on Epic 4 (lab websites), enabling concurrent execution.

**Checkpoint:** `checkpoints/phase-5a-pi-publications-batch-N.jsonl`

**Blocks:** Epic 5B (provides PI publications for member inference)

#### Story 5.1: MCP Integration for Publication Retrieval

As a **user**,
I want **paper-search-mcp integrated to retrieve publications for each professor**,
so that **I can analyze recent research output**.

**Acceptance Criteria:**
1. paper-search-mcp configured and connected (NFR6)
2. Publications retrieved for each PI from last 3 years (FR15)
3. Search queries constructed from professor name + university affiliation
4. Publication metadata collected: title, authors, journal, year, abstract
5. Results validated (correct professor, not name collision)
6. Missing publications handled gracefully (some professors may have none)
7. Progress tracking shows publication retrieval status

#### Story 5.2: Abstract & Acknowledgment Analysis

As a **user**,
I want **paper abstracts and acknowledgment sections analyzed for research alignment**,
so that **the system focuses on most relevant content without processing full papers**.

**Acceptance Criteria:**
1. Abstracts extracted from publication data (FR30)
2. Acknowledgment sections extracted where available
3. LLM analyzes abstract content for alignment with user research interests
4. Acknowledgments analyzed for collaboration patterns and funding sources
5. Relevance score generated for each paper
6. Analysis optimized (abstracts only, not full text) for efficiency
7. Missing abstracts handled (use title as fallback)

#### Story 5.3: Journal Reputation Weighting

As a **user**,
I want **publications weighted by journal reputation**,
so that **high-impact publications are prioritized in fitness scoring**.

**Acceptance Criteria:**
1. Journal reputation database integrated (SJR or Impact Factor) (FR17)
2. Each publication's journal matched to reputation score
3. Reputation scores normalized to consistent scale
4. Missing journal ratings handled (use citation count or default weight)
5. Conference papers handled appropriately (common in CS/engineering)
6. Reputation data cached to avoid repeated lookups
7. Weighting factors configurable in system parameters

---

### Epic 5B: Lab Member Publications & Inference

**Goal:** Retrieve publications for lab members identified in Epic 4, and infer lab members from co-authorship patterns when websites are unavailable or stale (using PI publications from Epic 5A). This epic delivers comprehensive lab member intelligence.

**Execution Model:** Stories 5.4-5.5 **require both Epic 4 and Epic 5A to be complete** before starting. Epic 4 provides lab member lists (or identifies missing websites), and Epic 5A provides PI publications for co-authorship inference.

**Dependencies:** Epic 4 (lab member lists) AND Epic 5A (PI publications)

**Checkpoint:** `checkpoints/phase-5b-member-publications-batch-N.jsonl`

**Blocks:** Epic 6 (LinkedIn Integration)

#### Story 5.4: Lab Member Publication Discovery

As a **user**,
I want **publications by lab members (not just PI) identified**,
so that **I understand the full research output of the lab**.

**Acceptance Criteria:**
1. Lab members identified from Epic 4 website scraping (FR16)
2. Publications retrieved for each lab member (last 3 years)
3. Co-authorship patterns analyzed (PI + members)
4. Member publication metrics aggregated to lab level
5. Handles missing member lists gracefully (will be addressed in 5.5)
6. Progress shows "Processing member X of Y for Lab Z"

#### Story 5.5: Lab Member Inference from Co-Authorship

As a **user**,
I want **lab members inferred from publication co-authorship when websites are missing or stale**,
so that **I still get comprehensive lab intelligence**.

**Acceptance Criteria:**
1. When lab website unavailable or severely outdated, use publications (FR31)
2. Frequent co-authors on PI's papers identified as likely lab members
3. Co-authorship patterns analyzed (repeated collaboration over time)
4. Institutional affiliations checked to confirm same university
5. Inferred members flagged as "inferred from publications" in reports (FR32)
6. Confidence levels assigned to inferences
7. Inferred member list used for Story 5.4 publication discovery

---

### Epic 6: LinkedIn Integration & PhD Position Detection

**Goal:** Implement shared Playwright browser session with subagent queuing for LinkedIn access, match lab members to LinkedIn profiles with confidence scoring, and detect graduating or recently departed PhDs based on entry year and configurable graduation duration. This epic delivers position availability intelligence.

#### Story 6.1: mcp-linkedin MCP Server Integration

As a **user**,
I want **lab members matched to LinkedIn profiles via mcp-linkedin MCP server**,
so that **I can access LinkedIn data without managing browser sessions or authentication manually**.

**Acceptance Criteria:**
1. mcp-linkedin MCP server configured in Claude Agent SDK (NFR16)
2. LinkedIn authentication managed by MCP server (not application code)
3. Search people and get profile tools available
4. Session managed by MCP server automatically
5. Graceful handling if MCP server unavailable (NFR13)
6. Rate limiting managed by MCP server internally (NFR11)
7. Progress tracking for LinkedIn operations (NFR17)
8. Missing LinkedIn data handled gracefully (NFR13)
9. Profile access failures logged appropriately (NFR17)
10. Analysis continues with partial LinkedIn data if needed
11. Error summary generated with match statistics

#### ~~Story 6.2: Subagent Queue for LinkedIn Access~~ [REMOVED - SDK handles this]

As a **user**,
I want **subagents to queue for LinkedIn access**,
so that **only one agent uses the session at a time, preventing conflicts and rate limiting issues**.

**Acceptance Criteria:**
1. Queue mechanism implemented for LinkedIn access (NFR16)
2. Subagents request queue position when needing LinkedIn
3. Only one subagent accesses LinkedIn at a time
4. Queue processed sequentially (FIFO)
5. Progress shows "LinkedIn queue: X agents waiting"
6. Timeouts prevent queue from stalling
7. Failed requests don't block queue

#### Story 6.2: LinkedIn Profile Matching with Confidence Scores (formerly 6.3)

As a **user**,
I want **lab members matched to LinkedIn profiles with confidence scores**,
so that **I can assess match reliability and avoid false positives**.

**Acceptance Criteria:**
1. LinkedIn search performed for each lab member (FR22)
2. Candidate profiles evaluated by LLM
3. Matching considers: name, university affiliation, degree program, timeline
4. Confidence score (0-100) generated for each match (FR22)
5. School affiliation differences easily identified (reduces false positives)
6. Low-confidence matches flagged for user review
7. No match found handled gracefully (not all members have LinkedIn)

#### Story 6.3: PhD Graduation & Departure Detection (formerly 6.4)

As a **user**,
I want **graduating and recently departed PhD students identified**,
so that **I can target labs with upcoming position openings**.

**Acceptance Criteria:**
1. LinkedIn profiles analyzed for entry year/start date (FR21)
2. Configured average graduation duration used (FR5, e.g., 5.5 years)
3. Expected graduation year calculated (entry year + duration)
4. Currently graduating PhDs identified (within next year)
5. Recently departed PhDs identified (graduated within last year)
6. Timeline uncertainty acknowledged (some variation in graduation timing)
7. Position availability signals saved for fitness scoring

#### ~~Story 6.5: LinkedIn Error Handling & Logging~~ [REMOVED - merged into 6.1]

As a **user**,
I want **LinkedIn access failures logged and handled gracefully**,
so that **LinkedIn issues don't block the entire analysis**.

**Acceptance Criteria:**
1. Rate limiting detected and respected (NFR11)
2. Session expiration handled with re-authentication attempt
3. Profile access failures logged (NFR17)
4. Missing data handled gracefully (NFR13)
5. Account ban warnings surfaced to user
6. Analysis continues with partial LinkedIn data if needed
7. All LinkedIn-specific failures isolated (don't crash system)

---

### Epic 7: Authorship Analysis & Fitness Scoring

**Goal:** Analyze authorship patterns to determine first vs. nth author positions and core vs. collaborator roles, identify collaborations, and use LLM to dynamically identify and apply fitness scoring criteria synthesizing all collected intelligence. This epic delivers ranked labs with transparent scoring rationale.

#### Story 7.1: Authorship Pattern Analysis

As a **user**,
I want **authorship positions analyzed across publications**,
so that **I can distinguish between labs driving research vs. contributing as collaborators**.

**Acceptance Criteria:**
1. Author order extracted from each publication (FR23)
2. First author publications identified
3. Nth author (middle/last) publications identified
4. Authorship patterns aggregated by lab
5. Metrics calculated: % first author, % last author (often PI), % middle author
6. Patterns analyzed for PI and lab members separately
7. Results saved for fitness scoring

#### Story 7.2: Core vs. Collaborator Assessment

As a **user**,
I want **labs assessed as core research drivers vs. collaborative contributors**,
so that **I can prioritize labs leading research in my area of interest**.

**Acceptance Criteria:**
1. Publication authorship patterns analyzed (FR24)
2. Core research indicators: First/last author majority, PI as corresponding author
3. Collaborator indicators: Consistent middle authorship, acknowledgment-only mentions
4. LLM synthesizes patterns into core vs. collaborator assessment
5. Assessment considers field norms (some fields emphasize different author positions)
6. Confidence score provided for assessment
7. Results included in fitness scoring

#### Story 7.3: Collaboration Network Identification

As a **user**,
I want **lab collaborations with other groups identified**,
so that **I understand the lab's research network and partnerships**.

**Acceptance Criteria:**
1. Frequent co-authors from other institutions identified (FR18)
2. Collaboration patterns analyzed from publications and acknowledgments
3. External collaborators distinguished from internal lab members
4. Major collaborations highlighted (repeated over multiple papers)
5. Collaborative institutions identified
6. Collaboration diversity assessed (single partner vs. many partners)
7. Results included in lab intelligence reports

#### Story 7.4: LLM-Driven Fitness Scoring Criteria

As a **user**,
I want **Claude to dynamically identify appropriate fitness scoring criteria**,
so that **scoring adapts to my specific research context rather than using rigid rules**.

**Acceptance Criteria:**
1. LLM analyzes user research profile and available data (FR25)
2. Scoring criteria dynamically identified (not hardcoded)
3. Suggested criteria include but not limited to: research alignment, publication recency, journal reputation, authorship patterns, position availability, website freshness, collaboration activity
4. Criteria weighted based on relevance to user's goals
5. Scoring methodology explained transparently
6. User can review criteria before scoring applied (shown in logs)

#### Story 7.5: Multi-Factor Fitness Scoring Execution

As a **user**,
I want **each lab scored against identified criteria with weighted factors**,
so that **I get ranked labs reflecting best overall fit**.

**Acceptance Criteria:**
1. Each lab scored against all identified criteria (FR25)
2. Weights applied to criteria based on importance
3. Scores normalized to consistent scale (0-100)
4. Overall fitness score calculated per lab
5. Scoring rationale documented for each lab
6. Edge cases handled (missing data doesn't zero-out score)
7. Scores saved for report generation in Epic 8

---

### Epic 8: Comprehensive Report Generation

**Goal:** Generate user-facing reports including Overview.md with ranked labs and comparison matrix, actionable next steps with priority recommendations, detailed individual lab reports, and comprehensive data quality flagging. This epic delivers the final output that enables informed decision-making.

#### Story 8.1: Overview Report with Ranked Labs

As a **user**,
I want **an Overview.md report showing all labs ranked by fitness**,
so that **I can quickly identify top candidate labs**.

**Acceptance Criteria:**
1. Overview.md generated in markdown format (FR26)
2. Labs listed in descending fitness score order
3. Each lab entry includes: PI name, department, fitness score, key highlights
4. Summary statistics provided (total labs analyzed, date range, etc.)
5. Scoring methodology summary included
6. Report saved to output directory
7. Human-readable formatting for easy review

#### Story 8.2: Comparison Matrix for Top Labs

As a **user**,
I want **a side-by-side comparison matrix of top-ranked labs**,
so that **I can easily compare key metrics across my best options**.

**Acceptance Criteria:**
1. Comparison matrix generated for top N labs (configurable, default: top 10) (FR28)
2. Matrix columns: Lab, Fitness Score, Recent Publications, Position Availability, Website Status, Key Research Areas
3. Matrix formatted as markdown table in Overview.md
4. Metrics normalized for easy comparison
5. Visual indicators used where helpful (✓/✗ for position availability)
6. Matrix appears prominently in Overview.md

#### Story 8.3: Actionable Next Steps & Priority Recommendations

As a **user**,
I want **concrete next steps and priority recommendations**,
so that **I know exactly which labs to contact and when**.

**Acceptance Criteria:**
1. "Next Steps" section added to Overview.md (FR27)
2. Top 3-5 priority labs identified based on fitness + position availability
3. Recommended contact timing provided (e.g., "Contact soon - PhD graduating in 6 months")
4. Contact methods listed for each priority lab (email, contact form link)
5. Application cycle considerations mentioned if relevant
6. Personalized recommendations based on user's profile
7. Action items formatted as checklist

#### Story 8.4: Detailed Individual Lab Reports

As a **user**,
I want **detailed reports for each lab in a dedicated directory**,
so that **I can deep-dive into specific labs of interest**.

**Acceptance Criteria:**
1. Individual lab report generated for each analyzed lab (FR29)
2. Reports saved to ./labs/ directory
3. Each report includes: PI profile, lab overview, recent publications (with abstracts), lab members, authorship analysis, collaboration network, fitness scoring breakdown, contact information, data quality flags
4. Reports named consistently (e.g., labs/PI-name-department.md)
5. Internal links from Overview.md to detailed reports
6. Markdown formatting for readability
7. Reports self-contained (can be read independently)

#### Story 8.5: Data Quality Issue Flagging

As a **user**,
I want **data quality issues and inference-based results clearly flagged in all reports**,
so that **I understand the reliability of information for each lab**.

**Acceptance Criteria:**
1. Data quality flags embedded throughout reports (FR32)
2. Flags for: missing websites, inferred lab members, low-confidence matches, missing publications, stale data
3. Consistent flag format (e.g., "⚠️ Lab members inferred from co-authorship")
4. Severity levels indicated (info, caution, warning)
5. Summary of data quality issues in each lab report
6. Overall data quality metrics in Overview.md
7. Flags help user assess information reliability

---

## Out of Scope

The following features and capabilities are explicitly **not included** in this project:

### Multi-University Support
- ❌ Batch processing of multiple universities in a single run
- ❌ Cross-university comparison or aggregated rankings
- ❌ University recommendation engine

**Rationale:** This is a focused tool for deep analysis of a single target university. Multi-university support would significantly increase complexity and reduce depth of analysis.

### Automation & Monitoring
- ❌ Real-time monitoring or alerts for new position openings
- ❌ Scheduled re-runs or periodic updates
- ❌ Automated email outreach to professors
- ❌ Calendar integration for application deadline tracking

**Rationale:** This is a one-off execution tool. Continuous monitoring and automation features would require infrastructure (databases, scheduling, notification systems) beyond project scope.

### Machine Learning & Personalization
- ❌ ML-based personalization or recommendation refinement
- ❌ Learning from user feedback to improve future rankings
- ❌ Predictive models for position availability or acceptance likelihood

**Rationale:** As a one-off tool, there's no training data or feedback loop to support ML features. Current LLM-based scoring is sufficient.

### User Interface
- ❌ Web UI or dashboard
- ❌ Interactive visualizations
- ❌ Mobile application
- ❌ Browser extension

**Rationale:** CLI-only approach keeps the project focused and implementable. Markdown reports provide sufficient readability.

### Collaborative Features
- ❌ Multi-user support or user accounts
- ❌ Sharing results with peers
- ❌ Collaborative filtering or crowdsourced ratings
- ❌ Discussion forums or commenting on labs

**Rationale:** Single-user personal tool; collaboration features unnecessary.

### Integration Features
- ❌ Integration with application tracking systems
- ❌ Export to CRM or applicant management tools
- ❌ API for external tools to consume results
- ❌ Integration with email clients for outreach

**Rationale:** Markdown reports provide sufficient output format. Additional integrations add complexity without clear value for personal use.

### Advanced Data Collection
- ❌ Sentiment analysis of lab member reviews (e.g., Glassdoor-style)
- ❌ Grant funding analysis
- ❌ Patent portfolio analysis
- ❌ Teaching load or course assignment data
- ❌ Lab culture assessment from social media

**Rationale:** These would require additional data sources and analysis complexity. Current data sources provide sufficient signals for fitness assessment.

---

## Future Enhancements

The following features could be valuable in future iterations but are deferred from the initial implementation:

### V2.0 Potential Features

**Multi-University Batch Processing**
- Extend configuration to support multiple universities
- Parallel university analysis with consolidated rankings
- Cross-university comparison reports

**Historical Tracking**
- Re-run analysis periodically (quarterly, semi-annually)
- Track changes in lab activity over time
- Identify trending labs (increasing publication rate, new collaborations)
- Alert on significant changes (new positions, PI departures)

**Enhanced Communication Tools**
- Email template generation for top labs
- Personalized message suggestions based on research alignment
- Contact timing recommendations based on academic calendar
- Follow-up tracking and reminder system

**Expanded Intelligence**
- Grant funding data integration (NIH Reporter, NSF Awards)
- Conference presentation analysis (recent talks, keynotes)
- Social media presence assessment (Twitter/X, ResearchGate activity)
- Lab culture signals (diversity statements, work-life balance mentions)
- Alumni placement tracking (where do PhD graduates go?)

**Improved User Experience**
- Simple web UI for configuration and report viewing
- Interactive filtering and sorting of results
- Visual charts for publication trends, collaboration networks
- Export to additional formats (PDF, Excel, JSON)

**Advanced Analysis**
- Network analysis to identify "clusters" of related labs
- Citation impact analysis beyond journal reputation
- Collaboration strength scoring (depth vs. breadth)
- Research trajectory analysis (evolving vs. stable focus)

### Implementation Priority

If pursuing future enhancements, recommended priority order:

1. **Historical Tracking** (High Value) - Provides ongoing utility beyond one-time use
2. **Enhanced Communication Tools** (High Value) - Direct support for taking action on results
3. **Multi-University Support** (Medium Value) - Useful for students considering multiple schools
4. **Expanded Intelligence** (Medium Value) - Deeper insights but diminishing returns
5. **Improved User Experience** (Low-Medium Value) - Quality of life improvements
6. **Advanced Analysis** (Low Value) - Interesting but not critical

---

## Checklist Results Report

### Executive Summary

**Overall PRD Completeness:** 85%

**MVP Scope Appropriateness:** Just Right - Well-defined 8 epics with 40 stories representing a complete, executable workflow

**Readiness for Architecture Phase:** **✅ READY** - The PRD provides excellent technical clarity and implementation guidance

**Assessment Notes:**
- This is a one-off personal tool, so traditional product metrics (success metrics, MVP validation approach, stakeholder alignment) are intentionally minimal
- Functional and technical requirements are exceptionally detailed and well-structured
- Epic/story breakdown is comprehensive and properly sequenced
- Out of Scope and Future Enhancements sections added for clarity

---

### Category Analysis

| Category                         | Status  | Critical Issues |
| -------------------------------- | ------- | --------------- |
| 1. Problem Definition & Context  | PARTIAL | Success metrics not defined; Acceptable for one-off personal tool |
| 2. MVP Scope Definition          | PASS    | Out-of-scope items now documented; Core scope is clear |
| 3. User Experience Requirements  | PASS    | N/A - CLI tool, appropriately minimal |
| 4. Functional Requirements       | PASS    | 32 FRs comprehensive and testable |
| 5. Non-Functional Requirements   | PASS    | 17 NFRs covering all key concerns |
| 6. Epic & Story Structure        | PASS    | 8 epics, 40 stories, excellent breakdown |
| 7. Technical Guidance            | PASS    | Clear architecture direction and constraints |
| 8. Cross-Functional Requirements | PASS    | Data, integration, operations well covered |
| 9. Clarity & Communication       | PASS    | Excellent documentation quality |

**Legend:**
- **PASS**: 90%+ complete, ready for next phase
- **PARTIAL**: 60-89% complete, acceptable with noted gaps
- **FAIL**: <60% complete, needs significant work

---

### Key Findings

**Strengths:**
- ✅ Comprehensive functional requirements (32 FRs) organized in logical phases
- ✅ Thorough non-functional requirements (17 NFRs) addressing complexity concerns
- ✅ Excellent epic/story structure with clear acceptance criteria
- ✅ Technical constraints and architecture direction well-documented
- ✅ Risk mitigation strategies identified (LinkedIn bans, web scraping brittleness, data quality)
- ✅ Clear scope boundaries now documented in Out of Scope section

**Acceptable Gaps (for one-off personal tool):**
- ⚠️ No quantified success metrics or KPIs (would add: "Analyze target university within 24 hours, identify 10+ high-fitness labs")
- ⚠️ No formal user research or competitive analysis (not applicable for personal tool)
- ⚠️ No MVP validation approach (one-off execution, not iterative product)

**Technical Readiness:**
- Multi-agent orchestration patterns clearly specified
- Data sources and APIs identified (paper-search-mcp, Archive.org, LinkedIn)
- Configuration approach documented (JSON with schema validation)
- Error handling and graceful degradation strategies defined
- Resumability and checkpointing requirements established

**Areas for Architect Investigation:**
1. Claude Agent SDK multi-agent orchestration implementation patterns
2. ~~Playwright session persistence and queue mechanism design~~ **RESOLVED:** Use mcp-linkedin MCP server (see ARCHITECTURE-ERRATA Issue #3)
3. Optimal batch sizes for different university scales
4. JSON schema definitions for configuration files
5. Checkpoint/resume mechanism technical design
6. ~~LinkedIn session management to minimize ban risk~~ **RESOLVED:** Delegated to mcp-linkedin MCP server

---

### Final Decision

**✅ READY FOR ARCHITECT**

The PRD is comprehensive, well-structured, and provides clear technical guidance. The Architect has sufficient information to design the system architecture and begin implementation planning.

**Recommended Handoff:**
- Provide this PRD to the Architecture agent
- Architect should produce `docs/architecture.md` with:
  - System architecture and component design
  - Multi-agent orchestration patterns
  - Data flow diagrams
  - Configuration file schemas
  - Error handling and logging framework
  - Deployment and execution model

---

## Next Steps

### UX Expert Prompt

**Note:** This project is CLI-only with no graphical user interface. UX considerations are limited to:
- CLI interaction patterns and prompts
- Progress indicator design
- Error message clarity
- Report formatting and readability

**Recommended Action:** Skip UX Expert phase or minimal review of CLI interaction design only.

---

### Architect Prompt

Please review the attached PRD (`docs/prd.md`) and create a comprehensive architecture document (`docs/architecture.md`) for the Lab Finder system.

**Key Focus Areas:**

1. **System Architecture**
   - Multi-agent orchestration design using Claude Agent SDK
   - Component breakdown and responsibilities
   - Data flow between agents and phases
   - Configuration management architecture

2. **Multi-Agent Design**
   - Agent hierarchy and delegation patterns
   - Parallel vs. sequential execution strategies
   - Batch processing coordination
   - Shared resource management (LinkedIn session queue)

3. **Data Models & Schemas**
   - JSON schema definitions for all configuration files
   - Intermediate data structures for checkpointing
   - Report output formats and templates

4. **Technical Implementation**
   - Web scraping strategy (Claude Agent SDK built-in tools + Playwright fallback)
   - MCP integration patterns (paper-search-mcp)
   - LinkedIn session management and queue implementation
   - Error handling and logging framework
   - Resumability and checkpoint/restore mechanism

5. **Key Technical Decisions**
   - Optimal batch sizes for different processing phases
   - Rate limiting strategies per data source
   - Credential storage and security approach
   - Progress tracking and reporting mechanism

**Deliverable:** Complete architecture document following the project's architecture template, ready for development handoff to the dev agent.

---

