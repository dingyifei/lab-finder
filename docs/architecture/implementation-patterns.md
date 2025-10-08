# Implementation Patterns

**⚠️ DEPRECATION NOTICE:** Most patterns in this file are DEPRECATED as of 2025-10-07. The Claude Agent SDK does NOT have `AgentDefinition` or sub-agent spawning capabilities.

**For correct implementation patterns, see:**
- **Story 3.1 v0.5** (`docs/stories/3.1.professor-discovery.md` lines 220-644) - Complete asyncio.gather() examples
- **docs/architecture/agent-definitions.md** (lines 1-75) - Correct SDK usage patterns

**Valid patterns: Pattern 0 (Mode Selection), Pattern 2 (Checkpoint-Based State Passing)**

---

This section provides SDK-specific implementation patterns for Lab Finder based on Claude Agent SDK capabilities.

## Pattern 0: Claude Agent SDK Mode Selection (CURRENT - Added 2025-10-07)

**Critical Decision:** Claude Agent SDK offers two operational modes. Choose based on **statefulness requirements**, NOT tool usage.

### Mode 1: `ClaudeSDKClient` with Isolated Context - One-off Stateless Tasks (PRIMARY MODE)

**Use when:**
- ✓ Single request-response operation (no conversation memory needed)
- ✓ Text analysis: Department filtering, abstract scoring, professor matching
- ✓ Web scraping: University structure discovery, professor directory scraping
- ✓ Any task that doesn't require context from previous interactions

**Configuration:**
```python
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

# Example 1: Text-only analysis (no tools) - ACTUAL LAB FINDER IMPLEMENTATION
async def analyze_text(prompt: str) -> str:
    options = ClaudeAgentOptions(
        max_turns=1,              # One-off operation
        allowed_tools=[],         # No tools needed for text analysis
        system_prompt="You are an expert text analyst. Respond directly to user prompts with the requested analysis.",
        setting_sources=None      # CRITICAL: Prevents codebase context injection
    )

    response_text = ""

    # Use ClaudeSDKClient class, NOT query() function
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        async for message in client.receive_response():
            if hasattr(message, "content") and message.content:
                for block in message.content:
                    if hasattr(block, "text"):
                        response_text += block.text

    return response_text

# Example 2: Web scraping with tools (still stateless)
async def scrape_webpage(url: str) -> str:
    options = ClaudeAgentOptions(
        max_turns=3,                              # Allow follow-up tool calls
        allowed_tools=["WebFetch", "WebSearch"],  # Enable tools
        system_prompt="You are a web scraping assistant."
    )

    prompt = f"Scrape {url} and extract department information as JSON."

    response_text = ""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    response_text += block.text

    return response_text
```

**Lab Finder Usage:**
- All `llm_helpers.py` functions use `ClaudeSDKClient` with isolated context: `call_llm_with_retry()`, `analyze_department_relevance()`, etc.
- Configuration: `allowed_tools=[]`, `system_prompt` override, `setting_sources=None`
- This prevents the standalone `query()` function's codebase context injection bug
- University discovery: Uses `ClaudeSDKClient` for web scraping with tools enabled
- Professor scraping: Uses `ClaudeSDKClient` with `allowed_tools=["WebFetch", "WebSearch"]`

### Mode 2: `ClaudeSDKClient()` - Multi-turn with Memory (NOT CURRENTLY USED)

**Use when:**
- ✓ Complex iterative workflows requiring conversation context
- ✓ Follow-up questions based on previous responses
- ✓ Multi-step problem solving with backtracking

**Configuration:**
```python
from claude_agent_sdk import ClaudeSDKClient

# Example: Iterative research with context
async def iterative_research(topic: str):
    client = ClaudeSDKClient()

    # First query
    response1 = await client.send_message(f"Find papers on {topic}")

    # Follow-up query (client remembers context from response1)
    response2 = await client.send_message("Which of these are most cited?")

    # Another follow-up (client remembers both previous exchanges)
    response3 = await client.send_message("Summarize the top 3 papers")

    return response3
```

**Lab Finder Status:** Not currently used. May be added for complex multi-step workflows in future phases.

### Critical Bug Fixed: Standalone query() Context Injection

**Issue Discovered (2025-10-07):** The standalone `query()` function was injecting unwanted codebase context (git status, file system info) into prompts, causing Claude to respond in "coding assistant" mode instead of analyzing provided data.

**Root Cause:** `query()` function adds codebase context even with `allowed_tools=[]` configuration.

**Solution:** Switch to `ClaudeSDKClient` class with proper isolation:
```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async def call_llm_with_retry(prompt: str) -> str:
    options = ClaudeAgentOptions(
        max_turns=1,              # Stateless one-shot
        allowed_tools=[],         # No file access
        system_prompt="You are an expert text analyst. Respond directly to user prompts with the requested analysis.",
        setting_sources=None      # No codebase context - CRITICAL
    )

    response_text = ""

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        async for message in client.receive_response():
            if hasattr(message, "content") and message.content:
                for block in message.content:
                    if hasattr(block, "text"):
                        response_text += block.text

    return response_text.strip()
```

**Verification:** Profile consolidation, department filtering, and all LLM helpers now work correctly with proper context isolation.

### Decision Tree

```
┌─ Task requires conversation memory across turns?
│  ├─ YES → Use ClaudeSDKClient() multi-turn mode (Mode 2)
│  └─ NO → Continue ↓
│
├─ Task needs tools (WebFetch, Bash, etc.)?
│  ├─ YES → Use ClaudeSDKClient with allowed_tools=["WebFetch", ...] (Mode 1)
│  └─ NO → Continue ↓
│
└─ Task is pure text analysis?
   └─ YES → Use ClaudeSDKClient with allowed_tools=[], setting_sources=None (Mode 1)
```

### Common Misconceptions

❌ **WRONG:** "Use Mode 2 for tools, Mode 1 for text-only"
✅ **CORRECT:** Both modes support tools AND text-only. Choose based on statefulness.

❌ **WRONG:** "Use paid Anthropic API for text analysis"
✅ **CORRECT:** Use Claude Agent SDK `ClaudeSDKClient` - it's FREE and handles text analysis.

❌ **WRONG:** "Complex tasks require Mode 2"
✅ **CORRECT:** Complexity doesn't determine mode. Only statefulness matters.

❌ **WRONG:** "Use standalone query() function"
✅ **CORRECT:** Use `ClaudeSDKClient` class with proper isolation (setting_sources=None).

### Cost Comparison

| Mode | Cost | Use Case |
|------|------|----------|
| `ClaudeSDKClient` (Mode 1) | FREE | All Lab Finder operations (text analysis + web scraping) |
| `ClaudeSDKClient` (Mode 2) | FREE | Multi-turn conversations (not used yet) |
| Anthropic API `messages.create()` | PAID | NOT USED in Lab Finder ❌ |

---

## Pattern 1: Coordinator Structure ~~with AgentDefinition~~ **[DEPRECATED]**

**⚠️ DEPRECATED:** This pattern uses non-existent `AgentDefinition`. Use `query()` function instead.

**See correct pattern:** `docs/architecture/agent-definitions.md` lines 7-48

<details>
<summary>❌ Old (Incorrect) Pattern - Kept for Historical Reference</summary>

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

</details>

---

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

## Pattern 3: Parallel Batch Processing ~~with SDK~~ **[DEPRECATED]**

**⚠️ DEPRECATED:** This pattern uses non-existent `AgentDefinition`. Use asyncio.gather() instead.

**See correct pattern:** Story 3.1 v0.5 lines 406-471 (asyncio.gather() with Semaphore)

<details>
<summary>❌ Old (Incorrect) Pattern - Kept for Historical Reference</summary>

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

# NOTE: This pattern is DEPRECATED - use asyncio.gather() instead (see Story 3.1 v0.5)
# Application-level parallel execution with asyncio.gather() provides better control
async for msg in query(
    "Scrape these 50 lab websites concurrently",
    options=options_parallel
):
    collect_batch_results(msg)
```

</details>

---

## Pattern 4: Graceful Degradation with WebFetch → Playwright Fallback **[DEPRECATED]**

**⚠️ DEPRECATED:** This pattern uses non-existent `AgentDefinition`. Use SDK query() with try-except instead.

**See correct pattern:** Story 2.1 (refactored) - SDK handles retry/fallback automatically via Playwright MCP

<details>
<summary>❌ Old (Incorrect) Pattern - Kept for Historical Reference</summary>

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

</details>

---

## Pattern 5: MCP Server Integration (No Queue Needed) **[PARTIALLY DEPRECATED]**

**⚠️ PARTIALLY DEPRECATED:** MCP integration is correct, but uses non-existent `AgentDefinition`.

**See correct pattern:** docs/architecture/agent-definitions.md lines 50-75 (asyncio.gather() with MCP)

<details>
<summary>❌ Old Pattern (uses AgentDefinition) - Kept for Historical Reference</summary>

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

</details>
