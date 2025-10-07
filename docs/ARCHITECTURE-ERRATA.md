# Architecture Documentation Errata

**Created:** 2025-10-06
**Reported By:** Bob (Scrum Master) during Epic 5 story validation
**Severity:** Low (documentation only, functional description is correct)

---

## Issue #1: Outdated Phase Numbering in Agent Definitions

### Summary

The Agent Definitions section of `docs/architecture.md` uses outdated phase numbering that predates the Epic 5A/5B parallel execution optimization. This creates confusion when cross-referencing between PRD epic structure and architecture implementation.

### Location

**File:** `docs/architecture.md`
**Sections Affected:**
- Lines 827-856: "Phase 3: Publication Retrieval Agent"
- Lines 859-888: "Phase 3: Member Inference Agent"
- Lines 1740-1741: Checkpoint file paths reference "phase-3-publications"

### Inconsistency Details

| Documentation Section | Phase Reference | Correct Reference (per PRD) |
|----------------------|----------------|----------------------------|
| Mermaid Diagram (lines 107-116) | Phase 5A: PI Publications | ✅ Correct |
| Convergence Validation (line 258) | `phase-5a-pi-publications` | ✅ Correct |
| Agent Definition (line 832) | "Phase 3B: Publication Retrieval" | ❌ Should be "Phase 5A" |
| Checkpoint Path (line 845) | `phase-3-publications-batch-N.jsonl` | ❌ Should be `phase-5a-pi-publications-batch-N.jsonl` |
| File Structure (lines 1740-1741) | `phase-3-publications-batch-*.jsonl` | ❌ Should be `phase-5a-pi-publications-batch-*.jsonl` |

### Root Cause

The Agent Definitions section was written before the PRD revision that split Epic 5 into:
- **Epic 5A** (PI Publications) - runs parallel with Epic 4
- **Epic 5B** (Lab Member Publications) - runs after Epic 4 & 5A converge

The original architecture draft likely used sequential phase numbering (Phase 3 = Publications) before the parallel execution optimization was introduced.

### Impact

**User Impact:** Low
- Developers reading architecture may be confused by phase numbering mismatch
- Could waste time searching for "phase-3" checkpoints when they should look for "phase-5a"
- No functional impact - the actual implementation steps are correctly described

**Story Impact:**
- Contributed to confusion in Stories 5.2 and 5.3 about dependencies and execution model
- Fixed by adding explicit Dependencies sections referencing correct architecture lines

### Recommended Fix

**Option A: Update Architecture (High Priority)**

1. Update Agent Definition section:
   ```diff
   - ### Phase 3: Publication Retrieval Agent
   + ### Phase 5A: Publication Retrieval Agent

   - prompt="""Phase 3B: Publication Retrieval & Analysis
   + prompt="""Phase 5A: PI Publication Retrieval & Analysis

   - 3. Save results: checkpoints/phase-3-publications-batch-N.jsonl
   + 3. Save results: checkpoints/phase-5a-pi-publications-batch-N.jsonl
   ```

2. Update checkpoint file structure section:
   ```diff
   - **Phase 3: Publications (JSONL batches)**
   + **Phase 5A: PI Publications (JSONL batches)**

   - ├── phase-3-publications-batch-1.jsonl
   - ├── phase-3-publications-batch-N.jsonl
   + ├── phase-5a-pi-publications-batch-1.jsonl
   + ├── phase-5a-pi-publications-batch-N.jsonl
   ```

3. Update Member Inference agent:
   ```diff
   - ### Phase 3: Member Inference Agent
   + ### Phase 5B: Lab Member Inference Agent
   ```

**Option B: Add Errata Note (Quick Fix)**

Add a note at the top of Agent Definitions section:

```markdown
## Agent Definitions

**NOTE:** This section uses internal phase numbering for implementation organization.
For alignment with PRD epics:
- "Phase 3B: Publication Retrieval" → Epic 5A (Stories 5.1-5.3)
- "Phase 3C: Member Inference" → Epic 5B (Story 5.5)
- Checkpoint paths shown as "phase-3-*" should be "phase-5a-*" in actual implementation

Refer to PRD (`docs/prd.md`) for canonical epic numbering.
```

### Recommended Action

**Fix via Option A** during next architecture review cycle. The phase numbering should match PRD epic structure for consistency.

**Workaround:** Stories 5.1-5.3 now include correct checkpoint paths in Dependencies sections, mitigating immediate developer confusion.

---

## Validation

- ✅ Functional correctness: Agent definition steps are accurate
- ✅ Technology stack: Correct (pandas, paper-search-mcp, etc.)
- ✅ Data flow: Correctly describes Story 5.1 → 5.2 → 5.3 pipeline
- ❌ Phase numbering: Inconsistent with PRD
- ❌ Checkpoint paths: Use outdated "phase-3" prefix

---

## Related Documentation

- **PRD Epic Structure:** `docs/prd.md` (lines 225-227, Epic 5A/5B definitions)
- **PRD Epic Details:** `docs/prd/epic-details.md` (lines 298-352, Epic 5A execution model)
- **Architecture Convergence:** `docs/architecture.md` (lines 250-288, convergence validation)
- **Story Updates:** `docs/stories/5.1-5.3.md` (Dependencies sections now reference correct paths)

---

## Status

- **Reported:** 2025-10-06
- **Acknowledged:** Pending
- **Assigned To:** Architect (Winston)
- **Target Fix:** Next architecture review
- **Workaround Applied:** ✅ Stories updated with correct checkpoint paths

---

## Issue #2: Incorrect MCP Server Installation & Configuration

### Summary

The original architecture documentation specified incorrect installation methods and STDIO configuration for both MCP servers (paper-search-mcp and mcp-linkedin). This was discovered during Story 1.5 implementation when attempting to install the servers.

### Location

**Files Affected:**
- `docs/architecture/implementation-patterns.md` (lines 28-47, Pattern 5)
- `docs/architecture/tech-stack.md` (MCP server entries)
- `docs/architecture/components.md` (Publication and LinkedIn agent sections)
- `docs/architecture/external-apis.md` (MCP server sections)

### Inconsistency Details

| Component | Documented (INCORRECT) | Actual (CORRECT) |
|-----------|----------------------|------------------|
| **paper-search-mcp installation** | `npm install -g @modelcontextprotocol/server-paper-search` | `pip install paper-search-mcp` |
| **paper-search-mcp command** | `npx -y @modelcontextprotocol/server-paper-search` | `python -m paper_search_mcp.server` |
| **mcp-linkedin installation** | `npm install -g mcp-linkedin` | `uvx --from git+https://github.com/adhikasp/mcp-linkedin mcp-linkedin` |
| **mcp-linkedin command** | `mcp-linkedin` | `uvx --from git+https://github.com/adhikasp/mcp-linkedin mcp-linkedin` |

### Root Cause

The architecture was documented based on assumed npm package names without verifying actual MCP server implementations:

1. **paper-search-mcp**: Actual package is Python-based on PyPI, not npm
   - Source: https://github.com/openags/paper-search-mcp
   - Install: `pip install paper-search-mcp`
   - Version: 0.1.3+

2. **mcp-linkedin**: Git-based Python server, run via uvx (no npm package)
   - Source: https://github.com/adhikasp/mcp-linkedin
   - Install: On-demand via uvx (no pre-installation needed)
   - Credentials: Environment variables (LINKEDIN_EMAIL, LINKEDIN_PASSWORD)

### Impact

**User Impact:** High (blocked Story 1.5 implementation)
- Developer could not install MCP servers using documented commands
- Required research and verification of correct installation methods
- Story 1.5 tasks needed re-interpretation for correct STDIO configuration

**Story Impact:**
- Story 1.5: Required architecture review before proceeding
- Stories 5.1, 6.1: Will need updated guidance on MCP tool usage patterns

### Applied Fix

**Status: ✅ RESOLVED (2025-10-06)**

All architecture documents have been updated with correct MCP server configurations:

**1. implementation-patterns.md:**
```python
# CORRECTED STDIO Configuration
mcp_servers = {
    "papers": {
        "type": "stdio",
        "command": "python",
        "args": ["-m", "paper_search_mcp.server"]
    },
    "linkedin": {
        "type": "stdio",
        "command": "uvx",
        "args": ["--from", "git+https://github.com/adhikasp/mcp-linkedin", "mcp-linkedin"],
        "env": {
            "LINKEDIN_EMAIL": os.getenv("LINKEDIN_EMAIL"),
            "LINKEDIN_PASSWORD": os.getenv("LINKEDIN_PASSWORD")
        }
    }
}
```

**2. tech-stack.md:**
- Added correct installation instructions for both servers
- Added environment variable configuration examples
- Added MCP server entries to technology stack table
- Corrected MCP version from 1.0.0 to 1.16.0

**3. components.md:**
- Added STDIO transport clarification to Publication Retrieval Agent
- Added STDIO transport clarification to LinkedIn Matcher Agent
- Updated technology stack sections with correct package names

**4. external-apis.md:**
- Updated paper-search-mcp with correct installation and configuration
- Updated mcp-linkedin with correct installation and configuration
- Added supported platforms list for paper-search-mcp
- Added warning about unofficial LinkedIn API

### Implications for Story 1.5

**Original Task 3:** "Create MCP Client Wrapper Utility (src/utils/mcp_client.py)"

**Updated Approach:**
- Claude Agent SDK handles MCP server communication natively via STDIO
- No manual MCP client wrapper needed
- `src/utils/mcp_client.py` should be a **configuration helper** that returns MCP server config dict
- Agents use tools directly: `mcp__papers__search_papers`, `mcp__linkedin__search_people`, etc.

**Updated Story 1.5 Guidance:**

```python
# src/utils/mcp_client.py - Configuration Helper (not a client wrapper)
import os

def get_mcp_server_config() -> dict:
    """Return MCP server configuration for Claude Agent SDK"""
    return {
        "papers": {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "paper_search_mcp.server"]
        },
        "linkedin": {
            "type": "stdio",
            "command": "uvx",
            "args": ["--from", "git+https://github.com/adhikasp/mcp-linkedin", "mcp-linkedin"],
            "env": {
                "LINKEDIN_EMAIL": os.getenv("LINKEDIN_EMAIL"),
                "LINKEDIN_PASSWORD": os.getenv("LINKEDIN_PASSWORD")
            }
        }
    }
```

**Testing Approach:**
- Test MCP server configuration generation (unit test)
- Test that servers can be launched via configured commands (integration test)
- Do NOT test direct MCP protocol communication (SDK handles that)

### Validation

- ✅ paper-search-mcp installation verified: `pip install paper-search-mcp` (v0.1.3 installed successfully)
- ✅ mcp-linkedin repository verified: https://github.com/adhikasp/mcp-linkedin exists
- ✅ uvx command verified: `uvx` available after `pip install uv`
- ✅ All architecture documents updated with correct configuration
- ✅ STDIO transport pattern matches Claude Agent SDK documentation

### Related Documentation

- **Claude Agent SDK MCP Docs:** https://docs.claude.com/en/api/agent-sdk/python
- **paper-search-mcp Repository:** https://github.com/openags/paper-search-mcp
- **mcp-linkedin Repository:** https://github.com/adhikasp/mcp-linkedin
- **Story 1.5:** `docs/stories/1.5.mcp-server-setup.md`

### Status

- **Reported:** 2025-10-06 (during Story 1.5 implementation)
- **Discovered By:** James (Developer)
- **Acknowledged:** 2025-10-06
- **Fixed By:** Winston (Architect)
- **Fixed Date:** 2025-10-06
- **Status:** ✅ RESOLVED

---

## Issue #3: Story Reorganization - Epic 6 Reduction (Stories 6.2, 6.5 Removed)

### Summary

Based on the architecture corrections in Issue #2, analysis revealed that Stories 6.2 (Parallel LinkedIn Profile Matching) and 6.5 (LinkedIn Error Handling & Logging) were redundant with capabilities provided automatically by the Claude Agent SDK. Epic 6 was reorganized from 5 stories to 3 stories, with remaining stories renumbered for continuity.

### Location

**Files Affected (8 documentation files updated):**
- `docs/stories/6.1.mcp-linkedin-integration.md` (updated to v0.5)
- `docs/stories/6.2.linkedin-parallel-access.md` (DELETED)
- `docs/stories/6.3.linkedin-profile-matching.md` (RENAMED → 6.2)
- `docs/stories/6.4.phd-graduation-detection.md` (RENAMED → 6.3)
- `docs/stories/6.5.linkedin-error-handling.md` (DELETED, content merged into 6.1)
- `docs/stories/STORY-INDEX.md` (Epic 6 section updated)
- `docs/prd/index.md` (Epic 6 TOC updated)
- `docs/prd/epic-details.md` (Epic 6 section updated with strikethrough)
- `docs/prd.md` (Epic 6 section updated)
- `docs/DEVELOPMENT-HANDOFF.md` (Week 8 sprint timeline updated)

### Story Changes

| Original Story | Action | New Story | Rationale |
|---------------|--------|-----------|-----------|
| **Story 6.2: Parallel LinkedIn Access** | ❌ REMOVED | N/A | Claude Agent SDK handles parallel sub-agent execution and automatic retry logic via `AgentDefinition`. No manual `asyncio.gather` or `@retry` decorators needed. |
| **Story 6.5: LinkedIn Error Handling** | ⚠️ MERGED INTO 6.1 | N/A | SDK handles low-level MCP errors (connection, timeout, protocol). Application only needs data quality flags and summary reporting (Tasks 6-8 added to Story 6.1). |
| **Story 6.3: LinkedIn Profile Matching** | 🔄 RENUMBERED | **Story 6.2** | Maintained all acceptance criteria and tasks. Only story number changed. |
| **Story 6.4: PhD Graduation Detection** | 🔄 RENUMBERED | **Story 6.3** | Maintained all acceptance criteria and tasks. Only story number changed. |

### Content Preservation from Story 6.5

**Tasks Added to Story 6.1 (formerly in 6.5):**

**Task 6:** Handle missing LinkedIn profiles gracefully
- Catch `LinkedInProfileNotFound` exceptions
- Log warning with member name and search query
- Add `data_quality_flags.append("no_linkedin_profile")`

**Task 7:** Define data quality flags for LinkedIn operations
- `no_linkedin_profile`: LinkedIn profile not found for member
- `linkedin_parse_error`: Error parsing LinkedIn data
- `mcp_server_unavailable`: LinkedIn MCP server not accessible

**Task 8:** Generate error summary at batch completion
- Count errors by category
- Log summary: `logger.info("LinkedIn batch complete", total=N, matched=X, not_found=Y, errors=Z)`

**Acceptance Criteria Updated (Story 6.1):**
- AC 8: Missing profiles logged with member name, no pipeline block
- AC 9: Data quality flags added to lab data for all error conditions
- AC 10: Parse errors logged with member name and field
- AC 11: Error summary generated at batch completion

### Root Cause

During architecture review for Issue #2 (MCP Server Configuration), it was discovered that:

1. **Claude Agent SDK automatically handles:**
   - Parallel sub-agent execution via `AgentDefinition` instances
   - Automatic retry logic for MCP tool failures
   - Low-level error handling for STDIO transport failures
   - Connection pooling and rate limiting

2. **Original Story 6.2 Tasks (now unnecessary):**
   - Task 1: Implement parallel LinkedIn profile matching ❌ SDK handles via parallel sub-agents
   - Task 2: Add retry logic with exponential backoff ❌ SDK provides automatic retry
   - Task 3: Implement rate limiting and connection pooling ❌ SDK manages connections

3. **Original Story 6.5 Tasks (partially preserved):**
   - Task 1-3: Low-level error handling ❌ SDK handles MCP protocol errors
   - Task 4-6: Data quality flags and summary ✅ MOVED TO STORY 6.1 (application-level concern)

### Impact

**User Impact:** Low (improved efficiency)
- Reduces Epic 6 development time by ~3 days (Story 6.2 + 6.5 effort)
- Simplifies implementation by leveraging SDK capabilities
- Reduces maintenance burden (less custom error handling code)

**Story Impact:**
- **Story 6.1 (v0.5):** Added 3 tasks and 4 acceptance criteria for data quality management
- **Story 6.2 (formerly 6.3):** Renumbered, no content changes
- **Story 6.3 (formerly 6.4):** Renumbered, no content changes
- **Epic 6 Total Stories:** 5 → 3 (40% reduction)

**Sprint Timeline Impact (DEVELOPMENT-HANDOFF.md):**
- Week 8 Epic 6: Original "5 days (Stories 6.1-6.5)" → Updated "5 days (Stories 6.1-6.3)"
- Story 6.4 → Story 6.3 (Day 1-2)
- Story 6.5 removed, replaced with "Testing (Day 4-5)"

### Applied Fix

**Status: ✅ RESOLVED (2025-10-06)**

All documentation has been updated to reflect the Epic 6 reorganization:

**1. Story Files Updated:**
- `6.1.mcp-linkedin-integration.md` (v0.5):
  - Added Tasks 6-8 (error handling from 6.5)
  - Updated AC 8-11 (data quality flags)
  - Added code examples for graceful degradation

**2. Story Files Deleted:**
- `6.2.linkedin-parallel-access.md` (REMOVED - SDK handles parallelization)
- `6.5.linkedin-error-handling.md` (MERGED INTO 6.1 - SDK handles low-level errors)

**3. Story Files Renamed:**
- `6.3.linkedin-profile-matching.md` → `6.2.linkedin-profile-matching.md`
  - Updated title: "Story 6.3" → "Story 6.2"
- `6.4.phd-graduation-detection.md` → `6.3.phd-graduation-detection.md`
  - Updated title: "Story 6.4" → "Story 6.3"

**4. Documentation Index Files Updated:**

- **STORY-INDEX.md:**
  ```
  Epic 6: LinkedIn Integration (PARALLEL with Epic 5)
  ├── 6.1 (depends on 4.1, 1.5) [includes error handling from removed 6.5]
  ├── 6.2 (depends on 6.1, 1.7) [formerly 6.3]
  └── 6.3 (depends on 6.2) [formerly 6.4]
  ```

- **prd/index.md:** Updated Epic 6 TOC with strikethrough for removed stories and "formerly X.Y" annotations

- **prd/epic-details.md:** Updated Epic 6 section:
  - Story 6.2: Marked with strikethrough, rationale: "removed - Claude Agent SDK handles this"
  - Story 6.3 → Story 6.2 (header updated, marked "formerly 6.3")
  - Story 6.4 → Story 6.3 (header updated, marked "formerly 6.4")
  - Story 6.5: Marked with strikethrough, rationale: "removed - merged into 6.1"

- **prd.md:** Updated consolidated PRD with same changes as epic-details.md

- **DEVELOPMENT-HANDOFF.md:** Updated Week 8 sprint timeline:
  - Epic 6 story count: 5 → 3 stories
  - Day breakdown: Updated with new story numbers and testing allocation

### Validation

- ✅ Story 6.1 updated with error handling tasks from 6.5
- ✅ Stories 6.2 and 6.5 deleted
- ✅ Stories 6.3 → 6.2 renamed (file and content)
- ✅ Stories 6.4 → 6.3 renamed (file and content)
- ✅ STORY-INDEX.md updated with new Epic 6 structure
- ✅ prd/index.md updated with strikethrough and annotations
- ✅ prd/epic-details.md updated with removal rationale
- ✅ prd.md consolidated file updated
- ✅ DEVELOPMENT-HANDOFF.md sprint timeline updated
- ✅ All cross-references to old story numbers updated
- ✅ Story numbering is continuous (6.1, 6.2, 6.3)
- ✅ No broken references remain in documentation

### Implications for Development

**Simplified Implementation Pattern:**

```python
# INCORRECT (Old Story 6.2 approach - manual parallelization):
async def process_linkedin_batch_old(members: List[LabMember]):
    tasks = [match_linkedin_profile(member) for member in members]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Manual retry logic, error handling, etc.

# CORRECT (SDK-based approach - automatic parallelization):
from claude_agent_sdk import AgentDefinition

linkedin_agent = AgentDefinition(
    name="linkedin-matcher",
    prompt="Match lab members to LinkedIn profiles...",
    tools=["mcp__linkedin__search_people"],
    # SDK handles parallel execution, retry, and error handling automatically
)
```

**Data Quality Flag Pattern (preserved from Story 6.5):**

```python
# Application-level error handling (Task 6-8 in Story 6.1)
try:
    profile = await linkedin_agent.run(member_name)
except LinkedInProfileNotFound:
    logger.warning("LinkedIn profile not found", member=member_name)
    lab_data.data_quality_flags.append("no_linkedin_profile")
    # Continue processing - don't block pipeline
```

### Related Documentation

- **Architecture:** `docs/architecture/implementation-patterns.md` (Pattern 5: MCP Server Integration)
- **Story 1.5:** `docs/stories/1.5.mcp-server-setup.md` (MCP configuration foundation)
- **Story 6.1 (updated):** `docs/stories/6.1.mcp-linkedin-integration.md` (v0.5)
- **Story 6.2 (renumbered):** `docs/stories/6.2.linkedin-profile-matching.md` (formerly 6.3)
- **Story 6.3 (renumbered):** `docs/stories/6.3.phd-graduation-detection.md` (formerly 6.4)
- **Claude Agent SDK Docs:** https://docs.claude.com/en/api/agent-sdk/python (parallelization, retry logic)

### Status

- **Reported:** 2025-10-06 (during Story 6.2/6.5 review)
- **Reviewed By:** Sarah (Product Owner)
- **Acknowledged:** 2025-10-06
- **Fixed By:** Sarah (Product Owner)
- **Fixed Date:** 2025-10-06
- **Status:** ✅ RESOLVED

---

## Change Log

| Date | Action | Description |
|------|--------|-------------|
| 2025-10-06 | Reported | Bob (SM) discovered during Epic 5 story validation |
| 2025-10-06 | Workaround | Stories 5.1-5.3 updated with correct dependencies and paths |
| 2025-10-06 | Reported | James discovered incorrect MCP server configuration during Story 1.5 |
| 2025-10-06 | Resolved | Winston updated all architecture docs with correct STDIO configuration |
| 2025-10-06 | Reported | Sarah discovered Story 6.2 and 6.5 redundant with SDK capabilities |
| 2025-10-06 | Resolved | Sarah reorganized Epic 6 from 5 to 3 stories, updated all documentation |
