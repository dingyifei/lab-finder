# Source Tree

```
lab-finder/
├── config/                           # Configuration files (user-provided)
│   ├── config.schema.json           # JSON schema for main config
│   ├── user-profile.json            # User's research profile
│   ├── university.json              # Target university details
│   ├── system_params.json           # Batch sizes, rate limits, etc.
│   └── .env                         # Credentials (LinkedIn, etc.)
│
├── data/                            # Static data files
│   └── scimago-journal-rank.csv    # SJR journal reputation database
│
├── prompts/                         # Jinja2 LLM prompt templates (externalized)
│   ├── base/                        # Base templates and reusable components
│   ├── department/                  # Department-related prompts
│   │   └── relevance_filter.j2
│   ├── professor/                   # Professor-related prompts
│   │   ├── research_filter.j2
│   │   └── name_match.j2
│   ├── linkedin/                    # LinkedIn-related prompts
│   │   └── profile_match.j2
│   ├── publication/                 # Publication-related prompts
│   │   └── abstract_relevance.j2
│   └── README.md                    # Prompt template usage guide
│
├── src/                             # Source code
│   ├── main.py                      # CLI entry point
│   ├── coordinator.py               # CLI Coordinator component
│   │
│   ├── models/                      # Pydantic data models
│   │   ├── __init__.py
│   │   ├── config.py                # SystemParams, BatchConfig models
│   │   ├── profile.py               # ConsolidatedProfile model
│   │   ├── department.py            # Department model
│   │   ├── professor.py             # Professor model
│   │   ├── lab.py                  # Lab model
│   │   ├── lab_member.py           # LabMember model
│   │   ├── publication.py          # Publication model
│   │   ├── collaboration.py        # Collaboration model
│   │   └── fitness_score.py        # FitnessScore model
│   │
│   ├── agents/                      # Agent components (one per phase)
│   │   ├── __init__.py
│   │   ├── validator.py            # Configuration Validator
│   │   ├── university_discovery.py # University Structure Discovery Agent
│   │   ├── professor_discovery.py  # Professor Discovery Agent (Stories 3.1a-c)
│   │   ├── professor_filtering.py  # Professor Filtering Agent (Stories 3.2, 3.5)
│   │   ├── professor_reporting.py  # Professor Reporting Agent (Story 3.4)
│   │   ├── lab_intelligence.py     # Lab Website Intelligence Agent
│   │   ├── publication_retrieval.py # Publication Retrieval Agent
│   │   ├── member_inference.py     # Lab Member Inference Agent
│   │   ├── linkedin_matcher.py     # LinkedIn Matcher Agent
│   │   ├── authorship_analyzer.py  # Authorship Analyzer
│   │   ├── fitness_scorer.py       # Fitness Scoring Engine
│   │   └── report_generator.py     # Report Generator
│   │
│   ├── utils/                       # Shared utilities
│   │   ├── __init__.py
│   │   ├── checkpoint_manager.py   # Checkpoint save/load logic
│   │   ├── progress_tracker.py     # Progress bar wrapper (rich)
│   │   ├── web_scraping.py         # Multi-stage web scraping with Puppeteer MCP (replaces mcp_client.py)
│   │   ├── prompt_loader.py        # Jinja2 template loader with custom filters (Sprint Change 2025-10-10)
│   │   ├── llm_helpers.py          # LLM call wrappers (uses prompt_loader for templates)
│   │   ├── logger.py               # Structlog configuration
│   │   ├── rate_limiter.py         # Per-domain rate limiting (Story 3.1c)
│   │   ├── deduplication.py        # Professor deduplication logic (Story 3.1c)
│   │   ├── confidence.py           # Confidence scoring utilities (Story 3.3)
│   │   └── credential_manager.py   # Secure credential management
│
├── claude/                          # Claude SDK working directory (isolated)
│   ├── .mcp.json                   # MCP server configuration (Puppeteer, papers, linkedin)
│   └── .claude/
│       └── settings.json           # SDK settings (optional)
│   │
│   └── schemas/                     # JSON schemas for validation
│       ├── user-profile.schema.json
│       ├── university.schema.json
│       └── system_params.schema.json
│
├── tests/                           # Test suite
│   ├── unit/                        # Unit tests
│   │   ├── test_models.py
│   │   ├── test_checkpoint_manager.py
│   │   ├── test_validator.py
│   │   └── ...
│   ├── integration/                 # Integration tests
│   │   ├── test_university_discovery.py
│   │   ├── test_publication_retrieval.py
│   │   └── ...
│   └── fixtures/                    # Test data fixtures
│       ├── sample_config.json
│       ├── mock_professor_page.html
│       └── ...
│
├── checkpoints/                     # Checkpoint files (created at runtime)
│   └── .gitkeep                     # Keep directory in git
│
├── output/                          # Generated reports (created at runtime)
│   ├── Overview.md                  # Ranked lab overview
│   └── labs/                        # Individual lab reports
│       ├── jane-smith-vision-lab.md
│       └── ...
│
├── logs/                            # Structured logs (created at runtime)
│   └── lab-finder.log              # JSON-formatted logs
│
├── scripts/                         # Helper scripts
│   ├── download_sjr.py             # Download latest SJR database
│   └── validate_config.py          # Standalone config validator
│
├── .github/                         # GitHub-specific files
│   └── workflows/
│       └── tests.yml                # CI/CD workflow (optional)
│
├── requirements.in                  # High-level dependencies
├── requirements.txt                 # Pinned dependencies (generated by pip-tools)
├── pyproject.toml                   # Project metadata + tool configs
├── ruff.toml                        # Ruff linter configuration
├── mypy.ini                         # MyPy type checker configuration
├── pytest.ini                       # Pytest configuration
├── README.md                        # Project documentation
├── .gitignore                       # Git ignore rules
└── .env.example                     # Example credentials file
```

## Key Source Tree Decisions

**1. Flat Agent Structure:**
- All agents in `src/agents/` (not nested by phase) for simplicity
- One Python file per agent component for clear boundaries

**2. Pydantic Models in Separate Files:**
- Each model type gets its own file in `src/models/`
- Enables circular imports resolution and clear model definitions

**3. Utilities as Shared Module:**
- `checkpoint_manager.py` used by all agents
- `prompt_loader.py` loads Jinja2 templates from `prompts/` directory (Sprint Change 2025-10-10)
- `llm_helpers.py` provides LLM call wrappers (uses `prompt_loader` for templates)
- `web_scraping.py` implements multi-stage pattern (WebFetch → Sufficiency → Puppeteer MCP)
- MCP servers configured via `claude/.mcp.json` (Puppeteer, papers, linkedin)

**4. LLM Prompt Templates Externalized:**
- All LLM prompts stored as Jinja2 templates in `prompts/` directory (Sprint Change 2025-10-10)
- Organized by domain: `department/`, `professor/`, `linkedin/`, `publication/`
- Enables version-controlled prompt iteration without code changes
- Non-developers can edit prompts; templates support inheritance and custom filters
- Loaded via `src/utils/prompt_loader.py` with singleton pattern

**5. Configuration Schemas Separate from Code:**
- JSON schemas in `src/schemas/` directory
- Loaded by validator at runtime for user config validation

**6. Runtime Directories:**
- `checkpoints/`, `output/`, `logs/` created at runtime (gitignored except .gitkeep)
- Allows clean repository without generated files
