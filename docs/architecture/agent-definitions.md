# Agent Definitions

This section provides the complete `AgentDefinition` implementations for all Lab Finder agents. Each agent is configured with a specific description, detailed prompt, tool restrictions, and model selection.

## Phase 0: Configuration Validator Agent

```python
config_validator = AgentDefinition(
    description="Validates JSON configurations and consolidates user profile",
    prompt="""Phase 0: Configuration Validation & Profile Consolidation

Your task: Validate all configuration files and create consolidated user profile

Steps:
1. Validate each config file against JSON schemas in src/schemas/
2. Load or prompt for LinkedIn credentials from .env
3. Use LLM to summarize resume into key highlights
4. Streamline research interests into clear statements
5. Save consolidated profile: checkpoints/phase-0-validation.json

Output format (JSON):
{
  "name": "...",
  "target_university": "...",
  "target_department": "...",
  "research_interests": [...],
  "resume_highlights": {...},
  "preferred_graduation_duration": 5.5
}
""",
    tools=["Read", "Write"],
    model="sonnet"
)
```

## Phase 1: University Structure Discovery Agent

```python
university_discovery = AgentDefinition(
    description="Discovers and filters university department structure",
    prompt="""Phase 1: University Structure Discovery

Your task: Discover and filter relevant departments

Steps:
1. Scrape university website for organizational structure
   - Try WebFetch first (fast for static pages)
   - If fails, use Bash to invoke Playwright script
2. Extract hierarchy: school → division → department
3. Filter departments by relevance to target_department
4. Save results to: checkpoints/phase-1-departments.jsonl

Output format (JSONL):
{"id": "dept-001", "name": "Computer Science", "school": "Engineering",
 "url": "...", "is_relevant": true, "relevance_reasoning": "..."}
""",
    tools=["WebFetch", "Bash", "Read", "Write", "Glob"],
    model="sonnet"
)
```

## Phase 2: Professor Discovery Agent

```python
professor_discovery = AgentDefinition(
    description="Discovers professors from department directories",
    prompt="""Phase 2A: Professor Discovery

Your task: Scrape professor directories from departments

Steps:
1. For each department from Phase 1 checkpoint:
   - Scrape professor directory page (WebFetch primary, Playwright fallback)
   - Extract: name, title, email, research areas, lab name/URL
2. Save batch results: checkpoints/phase-2-professors-batch-N.jsonl

Output format (JSONL):
{"id": "prof-001", "name": "Dr. Jane Smith", "department_id": "dept-001",
 "lab_name": "Vision Lab", "lab_url": "...", "research_areas": [...]}

Process in batches of 20 professors per checkpoint.
""",
    tools=["WebFetch", "Bash", "Read", "Write", "Glob"],
    model="sonnet"
)
```

## Phase 2: Professor Filter Agent

```python
professor_filter = AgentDefinition(
    description="Filters professors by research field alignment using LLM",
    prompt="""Phase 2B: Professor Filtering

Your task: Filter professors by research field match with user interests

Context: You receive user profile and professor list from checkpoints

Steps:
1. For each professor batch:
   - Compare research_areas against user research_interests
   - Provide confidence score (0-100)
   - Provide reasoning for inclusion/exclusion
2. Update professor records with filter results
3. Save filtered batch: checkpoints/phase-2-filtered-batch-N.jsonl

Output format (JSONL):
{"id": "prof-001", "is_filtered": false, "filter_confidence": 95.0,
 "filter_reasoning": "Strong alignment with CV and ML interests", ...}

Only pass professors with filter_confidence >= 75.
""",
    tools=["Read", "Write"],
    model="sonnet"
)
```

## Phase 3: Lab Scraper Agent

```python
lab_scraper = AgentDefinition(
    description="Scrapes lab websites and checks Archive.org history",
    prompt="""Phase 3A: Lab Website Intelligence

Your task: Scrape lab websites and analyze freshness

Steps:
1. For each filtered professor with lab_url:
   - Scrape lab website (WebFetch primary, Playwright fallback)
   - Extract: description, members, contact info
   - Check last-modified header
   - Query Archive.org API for snapshot history using httpx
2. Analyze update frequency: monthly/yearly/stale
3. Save results: checkpoints/phase-3-labs-batch-N.jsonl

Output format (JSONL):
{"id": "lab-001", "pi_id": "prof-001", "description": "...",
 "last_updated": "2024-09-15", "wayback_history": [...],
 "update_frequency": "monthly", "members": [...]}

Flag missing websites in data_quality_flags.
""",
    tools=["WebFetch", "Bash", "Read", "Write", "Glob"],
    model="sonnet"
)
```

## Phase 3: Publication Retrieval Agent

```python
publication_agent = AgentDefinition(
    description="Retrieves publications via paper-search-mcp and analyzes relevance",
    prompt="""Phase 3B: Publication Retrieval & Analysis

Your task: Fetch publications and assess relevance

Steps:
1. For each filtered professor:
   - Query paper-search-mcp MCP server
   - Search format: "author:Professor Name affiliation:University"
   - Retrieve last 3 years of publications
2. For each publication:
   - Analyze abstract against user research interests
   - Assign relevance score (0-100)
   - Lookup journal SJR score from data/scimago-journal-rank.csv
3. Save results: checkpoints/phase-3-publications-batch-N.jsonl

Output format (JSONL):
{"id": "10.1234/example", "title": "...", "authors": [...],
 "journal": "...", "year": 2024, "relevance_score": 92.5,
 "journal_sjr_score": 1.85, "pi_author_position": "last"}

Use MCP tool: mcp__papers__search_papers
""",
    tools=["mcp__papers__search_papers", "Read", "Write", "Glob"],
    model="sonnet"
)
```

## Phase 3: Member Inference Agent

```python
member_inference = AgentDefinition(
    description="Infers lab members from co-authorship when website unavailable",
    prompt="""Phase 3C: Lab Member Inference

Your task: Infer members from publication co-authorship patterns

Steps:
1. For labs with missing member lists:
   - Load PI publications from Phase 3B checkpoint
   - Identify frequent co-authors (3+ papers in 3 years)
   - Use LLM to validate same university affiliation
2. Create inferred member records:
   - Mark is_inferred=true
   - Assign inference_confidence score
3. Save results: checkpoints/phase-3-inferred-members.jsonl

Output format (JSONL):
{"id": "member-001", "lab_id": "lab-001", "name": "Alice Cooper",
 "role": "PhD Student", "is_inferred": true,
 "inference_confidence": 85.0, "entry_year": null}

Flag in data_quality_flags: "members_inferred_from_coauthorship"
""",
    tools=["Read", "Write"],
    model="sonnet"
)
```

## Phase 4: LinkedIn Matcher Agent

```python
linkedin_matcher = AgentDefinition(
    description="Matches lab members to LinkedIn profiles via MCP",
    prompt="""Phase 4: LinkedIn Profile Matching & PhD Detection

Your task: Match members to LinkedIn and detect graduating PhDs

Steps:
1. For each lab member (from website or inferred):
   - Search LinkedIn via: mcp__linkedin__search_people
   - Query: member name + university + department
   - LLM-match best profile considering name variants, affiliation
2. Retrieve profile details: mcp__linkedin__get_profile
   - Extract education start dates
   - Calculate expected graduation: entry_year + graduation_duration
   - Flag if graduating within 1 year
3. Save results: checkpoints/phase-4-linkedin-batch-N.jsonl

Output format (JSONL):
{"id": "member-001", "linkedin_profile_url": "...",
 "linkedin_match_confidence": 95.0, "entry_year": 2020,
 "expected_graduation_year": 2025, "is_graduating_soon": true}

Use MCP tools: mcp__linkedin__search_people, mcp__linkedin__get_profile
MCP server handles rate limiting; parallel execution safe.
""",
    tools=["mcp__linkedin__search_people", "mcp__linkedin__get_profile", "Read", "Write"],
    model="sonnet"
)
```

## Phase 5: Authorship Analyzer

```python
authorship_analyzer = AgentDefinition(
    description="Analyzes publication authorship patterns and collaboration role",
    prompt="""Phase 5A: Authorship Analysis

Your task: Analyze authorship patterns and assess collaboration role

Steps:
1. For each lab with publications:
   - Calculate PI author position distribution (first/last/middle %)
   - Identify external collaborators (non-university co-authors)
   - Count collaboration frequency and recency
2. Use LLM to assess core vs. collaborator role:
   - Consider field norms (last author = PI in CS/bio)
   - Analyze author position patterns
   - Provide reasoning
3. Save results: checkpoints/phase-5-authorship.jsonl

Output format (JSONL):
{"lab_id": "lab-001", "pi_first_author_pct": 45.0,
 "pi_last_author_pct": 50.0, "pi_middle_author_pct": 5.0,
 "collaboration_role": "Core researcher with occasional collaborations",
 "collaborators": [...]}
""",
    tools=["Read", "Write"],
    model="sonnet"
)
```

## Phase 5: Fitness Scoring Engine

```python
fitness_scorer = AgentDefinition(
    description="LLM-driven multi-factor fitness scoring of labs",
    prompt="""Phase 5B: Fitness Scoring

Your task: Score labs using LLM-identified criteria

Steps:
1. Analyze user profile to identify scoring criteria and weights:
   - Research alignment (typically 40% weight)
   - Publication quality (typically 30%)
   - Position availability (typically 20%)
   - Website freshness (typically 10%)
   - Other user-specific criteria
2. For each lab:
   - Score each criterion (0-100)
   - Calculate weighted overall score
   - Provide scoring rationale and key highlights
   - Assign priority tier (1=top, 2=strong, 3=consider)
3. Sort labs by overall_score descending
4. Save results: checkpoints/phase-5-scores.jsonl

Output format (JSONL):
{"lab_id": "lab-001", "overall_score": 88.5,
 "criteria_scores": {...}, "criteria_weights": {...},
 "scoring_rationale": "...", "priority_recommendation": 1}
""",
    tools=["Read", "Write"],
    model="sonnet"
)
```

## Phase 6: Report Generator

```python
report_generator = AgentDefinition(
    description="Generates Overview.md and detailed lab reports",
    prompt="""Phase 6: Report Generation

Your task: Generate markdown reports

Steps:
1. Load all checkpoint data (labs, scores, publications, members)
2. Create Overview.md:
   - Ranked list of all labs with overall scores
   - Comparison matrix for top 10 labs
   - Data quality summary
3. For each lab, create detailed report labs/{lab-name}.md:
   - PI info and lab description
   - Research focus and recent publications
   - Lab members with LinkedIn profiles
   - Graduating PhD indicators
   - Contact information
   - Data quality flags (⚠️ markers)
4. Save to output/ directory

Use markdown tables, bullet lists, and headers for readability.
Flag all missing/inferred data with ⚠️ warnings.
""",
    tools=["Read", "Write", "Glob"],
    model="sonnet"
)
```
