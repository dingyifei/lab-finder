# Implementation Patterns

This section provides SDK-specific implementation patterns for Lab Finder based on Claude Agent SDK capabilities.

## Pattern 1: Coordinator Structure with AgentDefinition

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition

class LabFinderCoordinator:
    def __init__(self):
        # Define all phase agents (see Agent Definitions section for complete prompts)
        self.agents = {
            'config-validator': self._create_config_validator(),
            'university-discovery': self._create_university_discovery(),
            'professor-discovery': self._create_professor_discovery(),
            'professor-filter': self._create_professor_filter(),
            'lab-scraper': self._create_lab_scraper(),
            'publication-agent': self._create_publication_agent(),
            'member-inference': self._create_member_inference(),
            'linkedin-matcher': self._create_linkedin_matcher(),
            'authorship-analyzer': self._create_authorship_analyzer(),
            'fitness-scorer': self._create_fitness_scorer(),
            'report-generator': self._create_report_generator(),
        }

        # Configure SDK options with MCP servers
        self.options = ClaudeAgentOptions(
            agents=self.agents,
            mcp_servers={
                "papers": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-paper-search"]
                },
                "linkedin": {
                    "type": "stdio",
                    "command": "mcp-linkedin"
                }
            },
            allowed_tools=[
                "Read", "Write", "WebFetch", "Bash", "Glob",
                "mcp__papers__search_papers",
                "mcp__linkedin__search_people",
                "mcp__linkedin__get_profile"
            ]
        )

    async def run_pipeline(self, config_path: str):
        """Execute complete Lab Finder pipeline"""

        # Phase 0: Validation
        print("Phase 0: Validating configuration...")
        async for msg in query(
            f"Validate configuration files at {config_path}",
            options=self.options
        ):
            user_profile = self._extract_user_profile(msg)

        # Phase 1: University Discovery
        print("Phase 1: Discovering university structure...")
        checkpoint_0 = self._load_checkpoint("phase-0-validation.json")
        async for msg in query(
            f"""Discover department structure at {user_profile['target_university']}.
            Context: {json.dumps(checkpoint_0)}""",
            options=self.options
        ):
            departments = self._extract_departments(msg)

        # Continue for remaining phases...
```

## Pattern 2: Checkpoint-Based State Passing (Essential for Agent Context Isolation)

**Critical Insight:** SDK agents have isolated contexts with no shared memory. All state must be passed via checkpoints.

```python
import jsonlines
from pathlib import Path

class CheckpointManager:
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)

    def save_checkpoint(self, phase: str, data: list[dict]):
        """Save phase checkpoint as JSONL"""
        checkpoint_path = self.checkpoint_dir / f"{phase}.jsonl"
        with jsonlines.open(checkpoint_path, mode='w') as writer:
            writer.write_all(data)

    def load_checkpoint(self, phase: str) -> list[dict]:
        """Load phase checkpoint"""
        checkpoint_path = self.checkpoint_dir / f"{phase}.jsonl"
        if not checkpoint_path.exists():
            return []

        with jsonlines.open(checkpoint_path) as reader:
            return list(reader)

# Usage in coordinator
checkpoint_mgr = CheckpointManager()

# After Phase 1
departments = extract_departments_from_response(msg)
checkpoint_mgr.save_checkpoint("phase-1-departments", departments)

# Before Phase 2 - Load and pass complete context
phase1_data = checkpoint_mgr.load_checkpoint("phase-1-departments")
prompt = f"""Process these departments: {json.dumps(phase1_data)}
User Profile: {json.dumps(user_profile)}"""
```

## Pattern 3: Parallel Batch Processing with SDK

```python
# For large datasets, create multiple agent instances
def create_parallel_agents(base_agent: AgentDefinition, count: int) -> dict:
    """Create multiple instances of an agent for parallel processing"""
    return {
        f'{base_agent.description.lower().replace(" ", "-")}-{i}': AgentDefinition(
            description=f"{base_agent.description} (Worker {i})",
            prompt=base_agent.prompt,
            tools=base_agent.tools,
            model=base_agent.model
        )
        for i in range(count)
    }

# Use for parallel lab scraping
parallel_lab_scrapers = create_parallel_agents(lab_scraper_agent, count=5)

options_parallel = ClaudeAgentOptions(
    agents=parallel_lab_scrapers,
    mcp_servers=base_mcp_servers
)

# SDK automatically distributes work across 5 agents
async for msg in query(
    "Scrape these 50 lab websites concurrently",
    options=options_parallel
):
    collect_batch_results(msg)
```

## Pattern 4: Graceful Degradation with WebFetch → Playwright Fallback

```python
async def scrape_with_fallback(url: str) -> str:
    """Tiered scraping: WebFetch → Playwright → Skip"""

    # Try primary scraper (WebFetch)
    primary_agent = AgentDefinition(
        description="Primary web scraper",
        prompt=f"""Scrape {url} using WebFetch.
        If you encounter JavaScript or authentication requirements,
        respond with: 'WEBFETCH_FAILED: [reason]'""",
        tools=["WebFetch", "Read", "Write"],
        model="sonnet"
    )

    options_primary = ClaudeAgentOptions(agents={'primary-scraper': primary_agent})

    async for msg in query(f"Scrape {url}", options=options_primary):
        if "WEBFETCH_FAILED" not in msg.content:
            return msg.content  # Success with WebFetch

        # Fallback to Playwright
        fallback_agent = AgentDefinition(
            description="Playwright fallback scraper",
            prompt=f"""Scrape {url} using Playwright.
            Use Bash to invoke: python scripts/playwright_scrape.py {url}""",
            tools=["Bash", "Read", "Write"],
            model="sonnet"
        )

        options_fallback = ClaudeAgentOptions(agents={'fallback-scraper': fallback_agent})

        async for fallback_msg in query(f"Scrape {url} with Playwright", options=options_fallback):
            if "ERROR" in fallback_msg.content:
                # Both failed, flag and skip
                return {"error": "scraping_failed", "url": url, "flagged": True}
            return fallback_msg.content
```

## Pattern 5: MCP Server Integration (No Queue Needed)

```python
# LinkedIn matching with parallel MCP access
linkedin_matcher = AgentDefinition(
    description="Matches lab members to LinkedIn profiles",
    prompt="""Match lab member to LinkedIn profile.

    Steps:
    1. Search LinkedIn: mcp__linkedin__search_people
    2. LLM-match best profile considering name variants
    3. Get profile details: mcp__linkedin__get_profile
    4. Extract education start date and calculate graduation
    """,
    tools=["mcp__linkedin__search_people", "mcp__linkedin__get_profile", "Read", "Write"],
    model="sonnet"
)

# Multiple agents can call MCP tools concurrently
# MCP server handles rate limiting internally - no application queue needed
options = ClaudeAgentOptions(
    agents={'linkedin-matcher': linkedin_matcher},
    mcp_servers={
        "linkedin": {
            "type": "stdio",
            "command": "mcp-linkedin"
        }
    }
)

# Parallel execution is safe
async for msg in query("Match these 20 lab members to LinkedIn", options=options):
    process_linkedin_matches(msg)
```
