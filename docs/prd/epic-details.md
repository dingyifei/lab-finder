# Epic Details

## Epic 1: Foundation & Configuration Infrastructure

**Goal:** Establish the project's foundational infrastructure including configuration management with JSON schema validation, credential handling, and user profile consolidation. This epic delivers a working configuration system that validates inputs, securely manages credentials, and produces the consolidated research profile document that drives all subsequent lab matching.

### Story 1.1: Project Setup & Dependency Management

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

### Story 1.2: JSON Configuration Schema & Validation

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

### Story 1.3: Credential Management with CLI Prompts

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

### Story 1.4: Shared Utilities Implementation

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

### Story 1.5: MCP Server Configuration & Testing

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

### Story 1.6: Testing Infrastructure Setup

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

### Story 1.7: User Profile Consolidation

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

## Epic 2: University Structure Discovery & Department Filtering

**Goal:** Automatically discover and map the target university's complete department hierarchy (schools, divisions, departments), represent it in JSON format for sub-agent delegation, and filter out irrelevant departments before professor discovery. This epic delivers a validated department structure that optimizes subsequent processing.

**Execution Model:** Three-phase approach with parallel execution in Phase 1 and Phase 3 for ~33% timeline reduction

**Timeline:** ~7 days (vs. 10.5 days sequential)

**Phase Flow:**
- **Phase 1 (Parallel):** Infrastructure setup (Stories 2.4 || 2.5) - ~2 days
- **Phase 2 (Sequential):** Core discovery (Story 2.1) - ~3 days
- **Phase 3 (Parallel):** Post-processing (Stories 2.2 || 2.3) - ~2 days

---

### Phase 1: Infrastructure Setup (PARALLEL)

#### Story 2.4: Error Handling for Missing Structure Data

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

#### Story 2.5: Batch Configuration for Department Processing

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

### Phase 2: Core Discovery (SEQUENTIAL)

#### Story 2.1: University Website Structure Discovery

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

### Phase 3: Post-Processing (PARALLEL)

#### Story 2.2: Department Structure JSON Representation

As a **user**,
I want **the discovered department structure saved in JSON format**,
so that **departments can be processed in parallel using async tasks**.

**Acceptance Criteria:**
1. Department hierarchy represented in structured JSON (FR8)
2. JSON includes: school name, division name, department name, department URL, hierarchy level
3. JSON enables easy iteration and parallel async processing
4. File saved as intermediate result for resumability (NFR12)
5. Human-readable formatting for manual review if needed
6. Schema supports multi-level hierarchies (minimum 3 levels deep)

**Execution Dependencies:**
- **Can Start After:** Story 2.1 complete
- **Parallel Execution:** Can run in parallel with Story 2.3
- **Blocks:** None (documentation artifact)
- **Input:** Raw discovered departments from 2.1
- **Output:** Hierarchical JSON (for documentation/review)

#### Story 2.3: Department Relevance Filtering

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

## Epic 3: Professor Discovery & Filtering

**Goal:** Identify all professors within filtered departments, extract their lab affiliations and research areas, then use LLM-based analysis to filter professors whose research significantly deviates from the user's interests. This epic delivers a curated list of relevant professors with confidence scores and transparent filtering rationale.

### Story 3.1: Parallel Professor Discovery

As a **user**,
I want **professors identified across all relevant departments using parallel async processing**,
so that **discovery is efficient even for large universities**.

**Acceptance Criteria:**
1. Departments loaded from Epic 2 checkpoint output (FR10)
2. Professor directory pages discovered and scraped using Claude Code WebFetch/WebSearch tools
3. Professor names, titles, department affiliations extracted
4. Lab affiliations identified where available
5. Research area descriptions extracted from directory listings
6. WebFetch/WebSearch tools used with explicit Playwright fallback when needed (NFR5)
7. Results aggregated from parallel async tasks into master professor list
8. Parallel processing uses Python asyncio.gather() with configurable concurrency limits

**Note:** Story 3.1 v0.5 provides detailed implementation patterns including asyncio.gather() parallel execution.

### Story 3.2: LLM-Based Professor Research Field Filtering

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

### Story 3.3: Confidence Scoring for Filtering Decisions

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

### Story 3.4: Filtered Professor Logging & Transparency

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

### Story 3.5: Batch Processing for Professor Analysis

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

## Epic 4: Lab Website Intelligence & Contact Extraction

**Goal:** Scrape lab websites to gather foundational intelligence including last update dates, Archive.org change history, and contact information. Implement robust fallback strategies for missing or stale websites. This epic delivers baseline lab data independent of publication analysis.

### Story 4.1: Lab Website Discovery & Scraping

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

### Story 4.2: Archive.org Integration for Website History

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

### Story 4.3: Contact Information Extraction

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

### Story 4.4: Graceful Handling of Missing/Stale Websites

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

### Story 4.5: Web Scraping Error Handling & Retry Logic

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

## Epic 5A: PI Publication Research (Parallel with Epic 4)

**Goal:** Integrate paper-search-mcp to retrieve publications from the last 3 years for Principal Investigators, analyze abstracts and acknowledgments for research alignment and collaboration patterns, and weight publications by journal reputation. This epic delivers PI publication intelligence and **executes in parallel with Epic 4** to reduce overall timeline by 15-20%.

**Execution Model:** Stories 5.1-5.3 can begin immediately after Epic 3 completes (filtered professor list available). They do **not** depend on Epic 4 (lab websites), enabling concurrent execution.

**Checkpoint:** `checkpoints/phase-5a-pi-publications-batch-N.jsonl`

**Blocks:** Epic 5B (provides PI publications for member inference)

### Story 5.1: MCP Integration for Publication Retrieval

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

### Story 5.2: Abstract & Acknowledgment Analysis

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

### Story 5.3: Journal Reputation Weighting

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

## Epic 5B: Lab Member Publications & Inference

**Goal:** Retrieve publications for lab members identified in Epic 4, and infer lab members from co-authorship patterns when websites are unavailable or stale (using PI publications from Epic 5A). This epic delivers comprehensive lab member intelligence.

**Execution Model:** Stories 5.4-5.5 **require both Epic 4 and Epic 5A to be complete** before starting. Epic 4 provides lab member lists (or identifies missing websites), and Epic 5A provides PI publications for co-authorship inference.

**Dependencies:** Epic 4 (lab member lists) AND Epic 5A (PI publications)

**Checkpoint:** `checkpoints/phase-5b-member-publications-batch-N.jsonl`

**Blocks:** Epic 6 (LinkedIn Integration)

### Story 5.4: Lab Member Publication Discovery

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

### Story 5.5: Lab Member Inference from Co-Authorship

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

## Epic 6: LinkedIn Integration & PhD Position Detection

**Goal:** Implement shared Playwright browser session with subagent queuing for LinkedIn access, match lab members to LinkedIn profiles with confidence scoring, and detect graduating or recently departed PhDs based on entry year and configurable graduation duration. This epic delivers position availability intelligence.

### Story 6.1: mcp-linkedin MCP Server Integration

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

### ~~Story 6.2: Subagent Queue for LinkedIn Access~~ [REMOVED - SDK handles this]

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

### Story 6.2: LinkedIn Profile Matching with Confidence Scores (formerly 6.3)

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

### Story 6.3: PhD Graduation & Departure Detection (formerly 6.4)

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

### ~~Story 6.5: LinkedIn Error Handling & Logging~~ [REMOVED - merged into 6.1]

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

## Epic 7: Authorship Analysis & Fitness Scoring

**Goal:** Analyze authorship patterns to determine first vs. nth author positions and core vs. collaborator roles, identify collaborations, and use LLM to dynamically identify and apply fitness scoring criteria synthesizing all collected intelligence. This epic delivers ranked labs with transparent scoring rationale.

### Story 7.1: Authorship Pattern Analysis

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

### Story 7.2: Core vs. Collaborator Assessment

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

### Story 7.3: Collaboration Network Identification

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

### Story 7.4: LLM-Driven Fitness Scoring Criteria

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

### Story 7.5: Multi-Factor Fitness Scoring Execution

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

## Epic 8: Comprehensive Report Generation

**Goal:** Generate user-facing reports including Overview.md with ranked labs and comparison matrix, actionable next steps with priority recommendations, detailed individual lab reports, and comprehensive data quality flagging. This epic delivers the final output that enables informed decision-making.

### Story 8.1: Overview Report with Ranked Labs

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

### Story 8.2: Comparison Matrix for Top Labs

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

### Story 8.3: Actionable Next Steps & Priority Recommendations

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

### Story 8.4: Detailed Individual Lab Reports

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

### Story 8.5: Data Quality Issue Flagging

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
