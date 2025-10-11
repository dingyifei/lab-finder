# Agent Definitions

**IMPORTANT CLARIFICATION:** The Claude Agent SDK does NOT have an `AgentDefinition` class or sub-agent spawning mechanism. This section describes the **conceptual agent responsibilities and prompting strategies** using the actual Claude Agent SDK `query()` function.

All "agents" in this architecture are **application-level Python modules** that use the Claude Agent SDK's `query()` function with appropriate prompts and tool configurations. Parallel execution is achieved using Python's `asyncio.gather()`, NOT SDK-provided sub-agent spawning.

## Actual Claude Agent SDK Pattern

Lab Finder uses the Claude Agent SDK's **`query()` function** for all Claude interactions:

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

# Example: Professor discovery for a single department
async def discover_professors_for_department(department: Department) -> list[Professor]:
    """
    Application-level function that uses Claude Agent SDK query().
    This is NOT an AgentDefinition - that doesn't exist in the SDK.
    """
    options = ClaudeAgentOptions(
        allowed_tools=["WebFetch", "WebSearch"],
        max_turns=3,
        system_prompt="You are a web scraping assistant specialized in extracting professor information."
    )

    prompt = f"""
    Scrape the professor directory at: {department.url}

    Extract ALL professors with the following information:
    - Full name
    - Title (Professor, Associate Professor, etc.)
    - Research areas/interests
    - Lab name and URL (if available)
    - Email address

    Return results as a JSON array.
    """

    professors_data = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    # Parse JSON response from Claude
                    professors_data.extend(parse_professor_data(block.text))

    return convert_to_professor_models(professors_data, department)
```

**Parallel Execution** is achieved at the application level using `asyncio.gather()`:

```python
import asyncio

# Application-level parallel processing (NOT an SDK feature)
async def discover_professors_parallel(departments: list[Department]) -> list[Professor]:
    """
    Parallel execution using Python asyncio, NOT Claude Agent SDK sub-agents.
    """
    # Create tasks for each department
    tasks = [discover_professors_for_department(dept) for dept in departments]

    # Execute in parallel with asyncio.gather()
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Flatten results
    all_professors = []
    for result in results:
        if isinstance(result, Exception):
            logger.error("Department failed", error=str(result))
            continue
        all_professors.extend(result)

    return all_professors
```

---

## Phase 0: Configuration Validator

**Responsibility:** Validates JSON configurations and consolidates user profile

**Implementation:** Python module `src/agents/validator.py`

**Claude SDK Usage:**
```python
async def consolidate_profile(configs: dict) -> ConsolidatedProfile:
    """Uses Claude to summarize resume and streamline research interests."""
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write"],
        max_turns=2
    )

    prompt = f"""
    Consolidate the following user information into a research profile:
    Resume: {configs['resume']}
    Research Interests: {configs['interests']}

    Output as JSON with fields: name, research_interests (list), resume_highlights (dict)
    """

    async for message in query(prompt=prompt, options=options):
        # Parse consolidated profile
        pass

    # Save to checkpoints/phase-0-validation.json
```

**Key Tasks:**
1. Validate config files against JSON schemas
2. Load/prompt for credentials via CredentialManager
3. Use Claude SDK `query()` to summarize resume
4. Save consolidated profile to checkpoint

---

## Phase 1: University Structure Discovery

**Responsibility:** Discovers and filters university department structure

**Implementation:** Python module `src/agents/university_discovery.py`

**Claude SDK Usage:**
```python
async def discover_structure(university_url: str) -> list[Department]:
    """Scrape university structure using WebFetch."""
    options = ClaudeAgentOptions(
        allowed_tools=["WebFetch", "Bash", "Read", "Write"],
        max_turns=5
    )

    prompt = f"""
    Scrape {university_url} to discover all academic departments.
    Extract: school name, division name, department name, department URL, hierarchy level.
    Return as JSONL format.
    """

    async for message in query(prompt=prompt, options=options):
        # Extract department data from response
        pass

    # Fallback to Playwright if WebFetch insufficient
    if not departments:
        departments = await scrape_with_playwright(university_url)

    # Save to checkpoints/phase-1-departments.jsonl
```

**Filtering:**
```python
async def filter_departments(departments: list[Department], user_profile: dict[str, str]) -> list[Department]:
    """Use Claude to filter relevant departments.

    Args:
        departments: List of departments to filter
        user_profile: User profile dict with 'interests', 'degree', 'background'
    """
    options = ClaudeAgentOptions(max_turns=1)

    prompt = f"""
    User Research Interests: {user_profile['interests']}
    Departments: {[d.name for d in departments]}

    Filter to only departments relevant to the user's research. Return department names as JSON array.
    """

    async for message in query(prompt=prompt, options=options):
        # Parse filtered department names
        pass
```

---

## Phase 2: Professor Discovery & Filter

**Responsibility:** Discover professors, filter by research field alignment

**Implementation:** Python module `src/agents/professor_filter.py`

**Parallel Discovery (Application-Level):**
```python
async def discover_professors_parallel(departments: list[Department], max_concurrent: int = 5) -> list[Professor]:
    """
    Parallel professor discovery using asyncio.Semaphore.
    NOT a Claude Agent SDK feature - this is pure Python async.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_with_semaphore(dept: Department) -> list[Professor]:
        async with semaphore:
            return await discover_professors_for_department(dept)

    tasks = [process_with_semaphore(dept) for dept in departments]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return flatten_results(results)
```

**Single Department Discovery:**
```python
async def discover_professors_for_department(department: Department) -> list[Professor]:
    """Use multi-stage scraping pattern with Puppeteer MCP fallback (Pattern 7).

    See src/utils/web_scraping.py for full implementation.
    """
    from src.utils.web_scraping import scrape_with_sufficiency

    # Multi-stage pattern: WebFetch → Sufficiency → Puppeteer MCP → Re-evaluate
    result = await scrape_with_sufficiency(
        url=department.url,
        required_fields=["name", "title", "research_areas", "email", "lab_url"],
        max_attempts=3,
        correlation_id=get_correlation_id()
    )

    if not result["sufficient"]:
        # Add data quality flags for missing fields
        logger.warning("Incomplete scraping", missing=result["missing_fields"])

    return convert_to_professor_models(result["data"], department)
```

**Filtering (Story 3.2 - module-level functions):**
```python
async def filter_professor_single(
    professor: Professor,
    profile_dict: dict[str, str],
    correlation_id: str
) -> dict[str, Any]:
    """LLM-based research field filtering for single professor.

    Args:
        professor: Professor to filter
        profile_dict: User profile dict with 'research_interests', 'current_degree'
        correlation_id: Correlation ID for logging

    Returns:
        Dict with 'decision', 'confidence', 'reasoning' fields
    """
    # Calls llm_helpers.filter_professor_research() with retry logic
    # Returns {"decision": "include"|"exclude", "confidence": 0-100, "reasoning": str}
    pass

async def filter_professors(correlation_id: str) -> list[Professor]:
    """Main orchestration: loads profile, filters all professors in batches."""
    pass
```

---

## Phase 3: Lab Website Intelligence

**Responsibility:** Scrape lab websites, extract 5 data categories, check Archive.org history

**Implementation:** Python module `src/agents/lab_intelligence.py`

**Data Extraction:** 5 categories (lab_information, contact, people, research_focus, publications)

**Multi-Stage Pattern:** Uses sufficiency evaluation between WebFetch and Puppeteer MCP stages

**Claude SDK Usage:**
```python
async def scrape_lab_website(lab_url: str) -> LabWebsiteData:
    """Scrape lab website using multi-stage pattern with sufficiency evaluation."""
    from src.utils.web_scraping import scrape_with_sufficiency

    # Multi-stage pattern: WebFetch → Sufficiency → Puppeteer MCP → Re-evaluate
    result = await scrape_with_sufficiency(
        url=lab_url,
        required_fields=[
            "lab_information",  # Description, mission
            "contact",          # Email, phone, contact form URL
            "people",           # Lab members, roles
            "research_focus",   # Research areas, projects
            "publications"      # Recent publications, links
        ],
        max_attempts=3,
        correlation_id=get_correlation_id()
    )

    if not result["sufficient"]:
        # Add data quality flags for missing categories
        logger.warning("Incomplete lab data", missing=result["missing_fields"])
        for field in result["missing_fields"]:
            lab.data_quality_flags.append(f"missing_{field}")

    # Archive.org check via waybackpy (not Claude SDK)
    wayback_history = await check_archive_org(lab_url)

    return convert_to_lab_model(result["data"], wayback_history)
```

**Data Quality Flags:**
- `insufficient_webfetch`: WebFetch didn't extract all 5 categories
- `puppeteer_mcp_used`: Escalated to Puppeteer MCP fallback
- `sufficiency_evaluation_failed`: Could not determine completeness
- `missing_lab_information`, `missing_contact`, `missing_people`, `missing_research_focus`, `missing_publications`: Specific missing categories

**Reference:** `src/utils/web_scraping.py` utility for multi-stage pattern

---

## Phase 3B: Publication Retrieval

**Responsibility:** Retrieve publications via paper-search-mcp MCP server

**Implementation:** Python module `src/agents/publication_retrieval.py`

**MCP Server Configuration:**
```python
options = ClaudeAgentOptions(
    mcp_servers={
        "papers": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "paper-search-mcp"]
        }
    },
    allowed_tools=["mcp__papers__search_papers", "Read", "Write"]
)

async def fetch_publications(professor: Professor) -> list[Publication]:
    """Query paper-search-mcp MCP server for publications."""
    prompt = f"""
    Use mcp__papers__search_papers to find publications for:
    Author: {professor.name}
    Affiliation: {professor.department_name}
    Years: Last 3 years

    Return publication metadata.
    """

    async for message in query(prompt=prompt, options=options):
        # Parse publication data
        pass
```

**Abstract Analysis:**
```python
async def analyze_abstract_relevance(
    publication: Publication,
    profile_dict: dict[str, str]
) -> float:
    """LLM analyzes abstract for research alignment.

    Args:
        publication: Publication to analyze
        profile_dict: User profile dict with 'research_interests'
    """
    options = ClaudeAgentOptions(max_turns=1)

    prompt = f"""
    Abstract: {publication.abstract}
    User Interests: {profile_dict['research_interests']}

    Relevance score (0-100).
    """

    async for message in query(prompt=prompt, options=options):
        # Extract relevance score
        pass
```

---

## Phase 4: LinkedIn Integration

**Responsibility:** Match lab members to LinkedIn profiles via mcp-linkedin

**Implementation:** Python module `src/agents/linkedin_matcher.py`

**MCP Server Configuration:**
```python
options = ClaudeAgentOptions(
    mcp_servers={
        "linkedin": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "mcp-linkedin"]
        }
    },
    allowed_tools=["mcp__linkedin__search_people", "mcp__linkedin__get_profile"]
)

async def match_linkedin_profile(member: LabMember, university: str) -> LinkedInMatch:
    """Search and match LinkedIn profile."""
    prompt = f"""
    Use mcp__linkedin__search_people to find profile for:
    Name: {member.name}
    University: {university}
    Department: {member.department}

    Then use mcp__linkedin__get_profile to get education details.
    Assess match confidence (0-100).
    """

    async for message in query(prompt=prompt, options=options):
        # Parse match results
        pass
```

**Note:** The mcp-linkedin MCP server handles authentication and rate limiting internally. Parallel execution is safe - the application can call multiple LinkedIn queries concurrently.

---

## Phase 5: Authorship Analysis & Fitness Scoring

**Responsibility:** Analyze authorship patterns, score labs

**Implementation:** Python modules `src/agents/authorship_analyzer.py` and `src/agents/fitness_scorer.py`

**Authorship Analysis:**
```python
async def analyze_authorship(lab: Lab, publications: list[Publication]) -> AuthorshipAnalysis:
    """LLM analyzes authorship patterns for core vs. collaborator role."""
    options = ClaudeAgentOptions(max_turns=1)

    prompt = f"""
    PI: {lab.pi_name}
    Publications: {format_publications(publications)}

    Calculate:
    - PI first author percentage
    - PI last author percentage
    - Core vs. collaborator role assessment (considering field norms)

    Return as JSON.
    """

    async for message in query(prompt=prompt, options=options):
        # Parse authorship analysis
        pass
```

**Fitness Scoring:**
```python
async def identify_scoring_criteria(profile_dict: dict[str, str]) -> dict[str, float]:
    """LLM dynamically identifies scoring criteria and weights.

    Args:
        profile_dict: User profile dict with research interests and background
    """
    options = ClaudeAgentOptions(max_turns=1)

    prompt = f"""
    User Research Interests: {profile_dict['research_interests']}
    Degree Program: {profile_dict.get('current_degree', 'General')}

    Identify appropriate fitness scoring criteria and weights for lab matching.
    Typical criteria: research alignment, publication quality, position availability, website freshness.

    Return as JSON with criteria names as keys and weights (0-1) as values.
    """

    async for message in query(prompt=prompt, options=options):
        # Parse criteria and weights
        pass


async def score_lab(
    lab: Lab,
    criteria: dict,
    profile_dict: dict[str, str]
) -> FitnessScore:
    """Score lab against identified criteria.

    Args:
        lab: Lab to score
        criteria: Dict of criteria names to weights
        profile_dict: User profile dict with research interests
    """
    options = ClaudeAgentOptions(max_turns=2)

    prompt = f"""
    Lab: {lab.pi_name} - {lab.research_focus}
    Criteria: {criteria}
    User Interests: {profile_dict['research_interests']}

    Score this lab (0-100) for each criterion.
    Calculate weighted overall score.
    Provide scoring rationale and priority recommendation (1=top, 2=strong, 3=consider).

    Return as JSON.
    """

    async for message in query(prompt=prompt, options=options):
        # Parse fitness score
        pass
```

---

## Phase 6: Report Generation

**Responsibility:** Generate Overview.md and detailed lab reports

**Implementation:** Python module `src/agents/report_generator.py`

**Report Generation (primarily Python, minimal Claude SDK usage):**
```python
def generate_overview(ranked_labs: list[FitnessScore]) -> str:
    """Generate Overview.md with ranked labs and comparison matrix."""
    # Pure Python markdown generation
    overview = "# Lab Finder Results\n\n"
    overview += generate_ranked_list(ranked_labs)
    overview += generate_comparison_matrix(ranked_labs[:10])
    return overview


def generate_lab_report(lab: Lab, score: FitnessScore) -> str:
    """Generate detailed individual lab report."""
    # Pure Python markdown generation
    report = f"# {lab.pi_name} - {lab.lab_name}\n\n"
    report += generate_lab_sections(lab, score)
    report += flag_data_quality_issues(lab)
    return report
```

---

## Summary: No AgentDefinition in Claude Agent SDK

**Key Points:**
1. **Claude Agent SDK provides `query()` and `ClaudeSDKClient()`** - NOT `AgentDefinition`
2. **All "agents" are application-level Python modules** that call `query()` with appropriate prompts
3. **Parallel execution uses Python `asyncio.gather()`** - NOT SDK-provided sub-agent spawning
4. **Correlation IDs are application-managed** - passed as function parameters and bound to logger
5. **WebFetch/Playwright fallback is application-level** - Claude SDK tools don't auto-fallback

For complete implementation examples, see Story 3.1 Dev Notes which provide full code patterns for using the Claude Agent SDK correctly.
