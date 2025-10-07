# Requirements

## Functional Requirements

### Phase 0: Validation & Setup

**FR1:** The system configuration shall be validated against a JSON schema before execution

**FR2:** The system shall support Playwright-based authentication with credentials from configuration file to access LinkedIn and university resources requiring authentication

**FR3:** The system shall prompt users via CLI to collect and save credentials to configuration file when authentication is required but credentials are not present

**FR4:** The system shall accept user input including resume, current degree program, university, department, and research interests from separate JSON configuration sources

**FR5:** The system shall accept a configurable average PhD graduation duration value (e.g., 5.5 years) from configuration

**FR6:** The system shall combine structured JSON configuration (university name, core website link, directory link, etc.) with extracted resume highlights and streamlined research interest statements into a consolidated research profile document

### Phase 1: University Structure Discovery

**FR7:** The system shall automatically discover and map the university's department structure (including multi-layered hierarchies such as schools, divisions, and departments)

**FR8:** The system shall represent the discovered department structure in JSON format to enable sub-agent delegation for professor discovery within specific departments

**FR9:** The system shall filter departments based on research relevance before initiating professor discovery to optimize performance

### Phase 2: Professor Discovery & Filtering

**FR10:** The system shall identify professors within the specified university, including their department and lab affiliations, accounting for multi-layered department structures (e.g., medical schools, engineering subdivisions)

**FR11:** The system shall filter professors using LLM-based analysis, including if ANY major field matches the user's research interests (supporting interdisciplinary researchers)

**FR12:** The system shall provide confidence scores for LLM-based professor filtering decisions

**FR13:** The system shall log and report professors/labs that were filtered out with reasoning for user validation

### Phase 3: Lab Research & Data Collection

**FR14:** The system shall scrape lab websites to determine the last update date and utilize Archive.org (Wayback Machine) to identify website change history

**FR15:** The system shall identify recent research papers (last 3 years) published by the Principal Investigator (PI) using paper-search-mcp

**FR16:** The system shall identify recent research papers (last 3 years) published by lab members using paper-search-mcp

**FR17:** The system shall use a configurable journal reputation database (e.g., SJR, Impact Factor) for publication weighting

**FR18:** The system shall identify lab collaborations with other research groups

**FR19:** The system shall identify current lab members

**FR20:** The system shall extract professor contact information (email addresses, lab website contact forms, application URLs) where available

**FR30:** The system shall analyze paper abstracts and acknowledgment sections (rather than full text) to optimize for research alignment and collaboration pattern identification

**FR31:** When lab websites are stale or missing, the system shall infer lab members from co-authorship patterns in the professor's recent 3-year publications

### Phase 4: Advanced Analysis

**FR21:** The system shall detect graduating PhD students and recently departed PhDs by combining the configured average graduation duration with LinkedIn data (entry year) to identify potential position openings

**FR22:** The system shall use LLM-based matching to verify whether individuals listed on lab websites match LinkedIn profiles with confidence scores

**FR23:** The system shall analyze authorship patterns in publications to determine if lab members/PI are first author or nth author

**FR24:** The system shall assess whether the lab is in a core research position or a collaborator role based on publication authorship patterns

### Phase 5: Scoring & Output

**FR25:** The system shall use Claude (LLM) to dynamically identify and apply lab fitness scoring criteria, considering factors such as (but not limited to): paper content alignment with user research interests, journal reputation weighting, authorship patterns indicating core vs. collaborative work, and PhD departure timing

**FR26:** The system shall generate an Overview.md report showing all labs ranked by fitness with performance metrics and scoring rationale

**FR27:** The system shall include actionable next steps in the Overview.md report, including priority recommendations (e.g., "Top 3 priority labs to contact based on fitness + position availability")

**FR28:** The system shall generate a comparison matrix in the Overview.md showing key metrics across top-ranked labs for side-by-side evaluation

**FR29:** The system shall generate detailed individual lab reports in a ./labs directory

**FR32:** The system shall document data quality issues, missing information, and inference-based results in the generated reports with appropriate flags

## Non-Functional Requirements

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
