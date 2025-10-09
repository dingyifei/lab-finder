# Core Workflows

## Workflow 1: End-to-End Lab Discovery Pipeline

```mermaid
sequenceDiagram
    actor User
    participant CLI as CLI Coordinator
    participant Validator as Config Validator
    participant UnivAgent as University Discovery
    participant ProfAgent as Professor Filter
    participant LabAgent as Lab Intelligence
    participant PubAgent as Publication Retrieval
    participant LinkedInAgent as LinkedIn Matcher
    participant Scorer as Fitness Scorer
    participant Reporter as Report Generator

    User->>CLI: Run with config files
    CLI->>Validator: Validate configs
    Validator->>Validator: Check JSON schemas
    Validator->>User: Prompt for missing credentials
    User-->>Validator: Provide LinkedIn credentials
    Validator->>Validator: Consolidate user profile (LLM)
    Validator-->>CLI: ConsolidatedProfile + configs valid

    CLI->>UnivAgent: Discover + filter departments
    UnivAgent->>UnivAgent: Scrape university structure
    UnivAgent->>UnivAgent: LLM filter by relevance
    UnivAgent-->>CLI: List of relevant departments (checkpoint)

    CLI->>ProfAgent: Discover + filter professors
    loop For each department batch
        ProfAgent->>ProfAgent: Scrape professor directories
        ProfAgent->>ProfAgent: LLM filter by research field
        ProfAgent-->>CLI: Batch checkpoint saved
    end
    ProfAgent-->>CLI: Filtered professor list

    par Lab Website Scraping
        CLI->>LabAgent: Scrape lab websites
        loop For each lab batch
            LabAgent->>LabAgent: Fetch website + Archive.org
            LabAgent-->>CLI: Batch checkpoint
        end
    and Publication Retrieval
        CLI->>PubAgent: Fetch publications (paper-search-mcp)
        loop For each professor batch
            PubAgent->>PubAgent: Query MCP + analyze abstracts
            PubAgent-->>CLI: Batch checkpoint
        end
    end

    CLI->>LinkedInAgent: Match members + detect PhDs
    loop For each lab batch (parallel)
        LinkedInAgent->>LinkedInAgent: Call mcp-linkedin MCP tools
        LinkedInAgent->>LinkedInAgent: LLM match profiles
        LinkedInAgent-->>CLI: Batch checkpoint
    end

    CLI->>Scorer: Calculate fitness scores
    Scorer->>Scorer: LLM identify criteria + score labs
    Scorer-->>CLI: Ranked labs (checkpoint)

    CLI->>Reporter: Generate reports
    Reporter->>Reporter: Create Overview.md + lab reports
    Reporter-->>CLI: Reports written to output/

    CLI-->>User: Analysis complete! Check output/
```

---

## Workflow 2: Checkpoint Resume After Failure

```mermaid
sequenceDiagram
    actor User
    participant CLI as CLI Coordinator
    participant CheckpointMgr as Checkpoint Manager
    participant ProfAgent as Professor Filter (example)

    User->>CLI: Re-run after crash/interrupt
    CLI->>CheckpointMgr: Check phase completion status
    CheckpointMgr-->>CLI: Phase 0-1 complete, Phase 2 partial
    CLI->>CheckpointMgr: Get resume point for Phase 2
    CheckpointMgr->>CheckpointMgr: Load completed batches
    CheckpointMgr->>CheckpointMgr: Identify first incomplete batch
    CheckpointMgr-->>CLI: Resume from batch 3 of 8

    CLI->>ProfAgent: Resume professor filtering (batch 3-8)
    loop For each remaining batch
        ProfAgent->>ProfAgent: Process batch
        ProfAgent->>CheckpointMgr: Save batch checkpoint
    end
    ProfAgent-->>CLI: Phase 2 complete

    CLI->>CLI: Continue to Phase 3
    Note over CLI: Normal execution continues
```

---

## Workflow 3: Parallel LinkedIn MCP Access Pattern

```mermaid
sequenceDiagram
    participant Agent1 as LinkedIn Matcher<br/>Agent (Lab 1)
    participant Agent2 as LinkedIn Matcher<br/>Agent (Lab 2)
    participant Agent3 as LinkedIn Matcher<br/>Agent (Lab 3)
    participant MCP as mcp-linkedin<br/>MCP Server

    Note over MCP: MCP server handles auth and rate limiting

    par Parallel LinkedIn Access
        Agent1->>MCP: search_people(lab_member_1)
        MCP-->>Agent1: Search results
        Agent1->>Agent1: LLM match profile
        Agent1->>MCP: get_profile(matched_url)
        MCP-->>Agent1: Profile data
    and
        Agent2->>MCP: search_people(lab_member_2)
        MCP-->>Agent2: Search results
        Agent2->>Agent2: LLM match profile
        Agent2->>MCP: get_profile(matched_url)
        MCP-->>Agent2: Profile data
    and
        Agent3->>MCP: search_people(lab_member_3)
        MCP-->>Agent3: Search results
        Agent3->>Agent3: LLM match profile
        Agent3->>MCP: get_profile(matched_url)
        MCP-->>Agent3: Profile data
    end

    Note over MCP: MCP server manages rate limiting<br/>No queue coordination needed
```

---

## Workflow 4: Graceful Degradation for Missing Data

```mermaid
sequenceDiagram
    participant LabAgent as Lab Intelligence Agent
    participant LabWebsite as Lab Website (unavailable)
    participant InferAgent as Member Inference Agent
    participant PubAgent as Publication Agent
    participant Reporter as Report Generator

    LabAgent->>LabWebsite: Scrape lab website
    LabWebsite-->>LabAgent: 404 Not Found
    LabAgent->>LabAgent: Flag: website_unavailable
    LabAgent->>LabAgent: Continue processing
    LabAgent-->>InferAgent: Lab with no member list

    InferAgent->>PubAgent: Get PI publications
    PubAgent-->>InferAgent: PI's recent papers
    InferAgent->>InferAgent: LLM: Identify frequent co-authors
    InferAgent->>InferAgent: LLM: Validate same university
    InferAgent->>InferAgent: Flag: members_inferred_from_coauthorship
    InferAgent-->>Reporter: Lab with inferred members + quality flags

    Reporter->>Reporter: Generate lab report
    Note over Reporter: ⚠️ Lab members inferred from publications<br/>⚠️ Lab website unavailable
    Reporter-->>Reporter: Report includes data quality warnings
```
