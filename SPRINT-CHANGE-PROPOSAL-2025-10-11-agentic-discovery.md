# Sprint Change Proposal: Agentic Discovery Architecture

**Date:** 2025-10-11
**Proposal ID:** SCP-2025-10-11-agentic-discovery
**Status:** APPROVED
**Priority:** HIGH
**Estimated Duration:** 5-7 weeks (27-35 days)

---

## Executive Summary

**Issue Identified:** Fundamental architectural misalignment between intended agentic discovery pattern and current zero-shot implementation.

**Current Reality:**
- Discovery agents (Epics 2, 3, 4) use single query→response→parse pattern
- Multi-turn capability (`max_turns=3-5`) configured but NOT leveraged
- Python-orchestrated tool selection (WebFetch → Puppeteer MCP)
- No sub-agent spawning mechanism
- No format reinforcement via follow-up queries
- Effectively zero-shot despite SDK configuration

**Intended Architecture:**
- Agentic multi-turn discovery with autonomous tool exploration
- Agent-driven tool selection (not Python-orchestrated)
- Sub-agent spawning via Task tool for specialized operations
- Format template reinforcement during conversation
- Iterative refinement with explicit thinking/reasoning

**Impact:** Epics 2 (University Discovery), 3 (Professor Discovery), 4 (Lab Intelligence) - All functional but architecturally misaligned

**Recommended Path:** Phased refactor (Option 1) - Validate pattern via POC, then systematically migrate all 3 discovery agents

**Timeline:** 27-35 days across 4 phases

---

## 1. Analysis Summary

### 1.1 Trigger Context

**Trigger Type:** Fundamental architectural misunderstanding discovered during code review

**Affected Components:**
- `src/agents/university_discovery.py` - Epic 2 (QA: 100/100)
- `src/agents/professor_discovery.py` - Epic 3 (QA: 90-100/100)
- `src/agents/lab_research.py` - Epic 4 (QA: 95/100, IN PROGRESS)
- `src/utils/web_scraping.py` - Shared utilities
- `docs/architecture/agent-definitions.md` - Architecture documentation
- `docs/architecture/implementation-patterns.md` - Pattern documentation

**Discovery Date:** 2025-10-11

**Impact Assessment:**
- Code works and passes QA ✅
- Architectural pattern misaligned ❌
- Lower accuracy than agentic approach would provide ⚠️
- Technical debt accumulating 🔴

### 1.2 Gap Analysis

**Configured vs. Used:**

| Feature | Configured | Actually Used | Gap |
|---------|-----------|---------------|-----|
| max_turns | 3-5 turns | Single query→response | **HIGH** |
| Tool autonomy | WebFetch, WebSearch, Puppeteer | Python-orchestrated pipeline | **CRITICAL** |
| Sub-agents | Task tool available | Never spawned | **HIGH** |
| Format reinforcement | Multi-turn conversation | Template only in initial prompt | **MEDIUM** |
| Thinking/reasoning | Implicit in max_turns | Zero-shot response expected | **HIGH** |
| Agentic score | Target: 8-10/10 | Current: 2-4/10 | **CRITICAL** |

**Evidence by Component:**

**A) University Discovery (university_discovery.py)**
- Lines 268-319: Uses standalone `query()` function (not even ClaudeSDKClient)
- `max_turns=3` but single-shot usage
- Zero-shot JSON parsing with regex fallback
- Agentic score: 2/10

**B) Professor Discovery (professor_discovery.py)**
- Lines 196-250: Uses ClaudeSDKClient correctly ✅
- `max_turns=3`, `allowed_tools=["WebFetch", "WebSearch"]` ✅
- BUT: Single `query()` → Parse pattern ❌
- Fallback to `scrape_with_sufficiency()` is Python-scripted, not agent decision ❌
- Agentic score: 3/10

**C) Lab Research (lab_research.py)**
- Lines 103-236: Uses `scrape_with_sufficiency()` multi-stage pattern
- Multi-stage logic Python-controlled:
  - Python: "Try WebFetch first"
  - Python: "Now evaluate sufficiency"
  - Python: "Now try Puppeteer MCP"
- Agent doesn't autonomously choose tools ❌
- Agentic score: 4/10

**D) LLM Helpers (llm_helpers.py)**
- Lines 72-142: `max_turns=1` explicitly! ❌
- `allowed_tools=[]` - No tool access ❌
- Zero-shot text analysis pattern
- Appropriate for filtering/analysis operations ✅

### 1.3 Root Cause Analysis

**Primary Issue:** Architecture documentation explicitly describes Python-orchestrated async execution, NOT agentic pattern

**Contributing Factors:**
1. `agent-definitions.md` lines 1-6 state: "SDK does NOT have sub-agent spawning"
2. `implementation-patterns.md` Pattern 0: "Primary mode is stateless one-shot"
3. `implementation-patterns.md` Pattern 0 Mode 2: "Not currently used"
4. Stories describe WHAT tools but not HOW (zero-shot vs. agentic execution pattern)
5. Code reviews focused on functionality, not architectural alignment

**Why This Happened:**
- PRD specified tool usage but not execution philosophy
- Architecture docs written for current SDK understanding (2025-10-07)
- Development proceeded based on documented patterns
- No prior agentic pattern examples in codebase

---

## 2. Epic Impact Analysis

### 2.1 Affected Epics Summary

| Epic | Status | Discovery Pattern? | Refactor Required | Priority |
|------|--------|-------------------|------------------|----------|
| Epic 2 | ✅ Complete (QA: 100/100) | YES (University/Dept) | **YES** | **HIGH** |
| Epic 3 | ✅ Complete (QA: 90-100/100) | YES (Professor) | **YES** | **HIGH** |
| Epic 4 | 🟡 In Progress (QA: 95/100) | YES (Lab websites) | **YES** | **HIGH** |
| Epic 5A | 📋 Planned | Partial (analysis) | Maybe (defer) | MEDIUM |
| Epic 5B | 📋 Planned | Partial (inference) | Maybe (defer) | MEDIUM |
| Epic 6 | 📋 Planned | Partial (matching) | Maybe (defer) | LOW |
| Epic 7 | 📋 Planned | NO (scoring) | Maybe (defer) | LOW |
| Epic 8 | 📋 Planned | NO (reporting) | NO | NONE |

**Scope Decision:** Refactor Epics 2-4 now, apply learnings to inform Epics 5-7 hybrid approach

### 2.2 Epic 2: University Structure Discovery

**Current Implementation:**
- Story 2.1: University website structure discovery via WebFetch
- Python orchestrates discovery logic
- Single prompt with all instructions
- Zero-shot JSON parsing

**Required Changes:**
- Agentic exploration of university structure
- Agent autonomously uses WebFetch/WebSearch to navigate site
- Multi-turn conversation builds up department list
- Format reinforcement after initial discovery
- Sub-agent for department validation (optional)

**Story Impact:**
- Story 2.1: Needs pattern update in implementation notes
- Story 2.2: No change (JSON output format unchanged)
- Story 2.3: Filtering stays zero-shot (appropriate for LLM analysis)
- Story 2.4: No change (error handling preserved)
- Story 2.5: No change (batch processing preserved)

**QA Score Preservation:** Create new story "2.6: Agentic Discovery Refactor" to preserve 100/100 score

### 2.3 Epic 3: Professor Discovery & Filtering

**Current Implementation:**
- Story 3.1a/b/c: Professor discovery via WebFetch with Puppeteer fallback
- Python `asyncio.gather()` for parallel execution
- Single prompt per department
- Zero-shot JSON parsing

**Required Changes:**
- Agentic exploration of department directories
- Agent autonomously navigates faculty listings
- Multi-turn conversation extracts professor details
- Sub-agent for individual professor profile scraping
- Format reinforcement ensures complete JSON

**Story Impact:**
- Story 3.1a: Needs agentic pattern in implementation
- Story 3.1b: Parallel execution preserved (asyncio.gather unchanged)
- Story 3.1c: Deduplication/rate limiting unchanged
- Story 3.2-3.5: Filtering/confidence/reporting unchanged (zero-shot appropriate)

**QA Score Preservation:** Create stories "3.6a/b/c: Agentic Discovery Refactor"

### 2.4 Epic 4: Lab Intelligence & Contact Extraction

**Current Status:** IN PROGRESS - Stories 4.1-4.5 complete, additional work in progress

**Current Implementation:**
- Story 4.1-4.5: Lab website scraping via multi-stage pattern
- Python controls WebFetch → Sufficiency → Puppeteer MCP flow
- Zero-shot extraction per stage

**Required Changes:**
- Agentic lab website exploration
- Agent decides when to escalate to Puppeteer MCP (not Python)
- Multi-turn conversation extracts 5 data categories
- Sub-agent for contact extraction
- Agent evaluates own sufficiency

**Story Impact:**
- Story 4.1: Agentic lab discovery and scraping
- Story 4.2: Archive.org integration unchanged (API call)
- Story 4.3: Contact extraction via sub-agent
- Story 4.4: Website status detection unchanged
- Story 4.5: Error handling pattern updated for agentic approach

**QA Score Preservation:** Create stories "4.6a/b/c: Agentic Discovery Refactor"

**DECISION:** ✅ **PAUSE Epic 4 now, include in refactor**

### 2.5 Future Epics (5-8)

**Strategy:** Hybrid approach informed by Epic 2-4 refactor learnings

**Epic 5A (PI Publications):**
- Publication retrieval: MCP tool call (not agentic) ✅
- Abstract analysis: Zero-shot appropriate ✅
- Consider: Multi-turn for complex abstract synthesis (defer decision)

**Epic 5B (Lab Member Publications):**
- Member discovery: Agentic if complex inference required
- Co-authorship analysis: Consider multi-turn reasoning
- Decision after Epic 2-4 refactor complete

**Epic 6 (LinkedIn):**
- Profile matching: Zero-shot appropriate ✅
- PhD detection: Zero-shot calculation ✅
- No agentic pattern needed

**Epic 7 (Fitness Scoring):**
- Criteria identification: Consider multi-turn reasoning
- Scoring execution: Zero-shot per lab appropriate
- Decision after Epic 2-4 refactor complete

**Epic 8 (Reports):**
- No agentic pattern needed ✅

---

## 3. Artifact Adjustment Needs

### 3.1 Architecture Documentation

**File: `docs/architecture/agent-definitions.md`**

**Current State (Lines 1-6):**
```
"IMPORTANT CLARIFICATION: The Claude Agent SDK does NOT have an `AgentDefinition`
class or sub-agent spawning mechanism. All agents are application-level Python
modules that use query() with appropriate prompts. Parallel execution is achieved
using Python's asyncio.gather(), NOT SDK-provided sub-agent spawning."
```

**Required Changes:**
- ✅ Update: SDK DOES support sub-agent spawning via Task tool
- ✅ Rewrite: Discovery agents should use agentic multi-turn pattern
- ✅ Add: Sub-agent architecture examples
- ✅ Update: All 3 discovery agent examples (Phase 0, 1, 2)
- ✅ Clarify: When to use agentic vs. zero-shot

**Scope:** Complete rewrite of discovery sections (lines 1-250)

---

**File: `docs/architecture/implementation-patterns.md`**

**Current State (Pattern 0 - Mode 1):**
```
"Use when: Single request-response operation (no conversation memory needed)
Lab Finder Usage: All discovery operations use ClaudeSDKClient with isolated context"
```

**Required Changes:**
- ✅ Update Pattern 0: Add Mode 3 (Agentic Multi-Turn)
- ✅ Decision tree: Add agentic pattern branch
- ✅ Update Pattern 7: Multi-stage scraping becomes agent-driven
- ✅ Add: Sub-agent spawning pattern (Task tool usage)
- ✅ Add: Format reinforcement pattern examples

**Scope:** Major updates to Pattern 0, Pattern 7, new Pattern 8 (Sub-agents)

---

**File: `docs/architecture/core-workflows.md`**

**Changes Required:** Review and update discovery workflows to reflect agentic pattern

---

### 3.2 PRD Documentation

**Files: `docs/prd/epic-details.md`**

**Changes Required:**

**Epic 2 - Story 2.1:**
- ✅ Add section: "Discovery Execution Pattern"
- ✅ Clarify: Agentic multi-turn exploration vs. zero-shot
- ✅ Specify: Agent autonomy in tool selection

**Epic 3 - Story 3.1:**
- ✅ Update note: "Story 3.1 v0.5 provides detailed implementation patterns including asyncio.gather() parallel execution" → Add agentic pattern reference
- ✅ Clarify: Professor discovery uses agentic exploration within each department

**Epic 4 - Story 4.1:**
- ✅ Update: Lab scraping uses agentic pattern
- ✅ Clarify: Agent decides when to escalate to Puppeteer MCP

**Scope:** Clarification sections, not full rewrites

---

### 3.3 Story Documentation

**Create New Refactor Stories:**

**Epic 2:**
- Story 2.6: Agentic University Discovery Refactor

**Epic 3:**
- Story 3.6a: Agentic Professor Discovery Refactor
- Story 3.6b: Sub-Agent Architecture Implementation
- Story 3.6c: Format Reinforcement Pattern

**Epic 4:**
- Story 4.6a: Agentic Lab Discovery Refactor
- Story 4.6b: Agent-Driven Tool Selection
- Story 4.6c: Multi-Turn Conversation Pattern

**Scope:** 7 new story files

---

### 3.4 Source Code

**Files Requiring Refactor:**

**Core Agents:**
- `src/agents/university_discovery.py` - Complete rewrite
- `src/agents/professor_discovery.py` - Major refactor (lines 160-432)
- `src/agents/lab_research.py` - Major refactor (lines 103-300)

**Utilities:**
- `src/utils/web_scraping.py` - Update for agent-driven tool selection
- `src/utils/llm_helpers.py` - Add agentic pattern helpers (keep zero-shot functions)

**New Files:**
- `src/utils/agentic_patterns.py` - Reusable agentic discovery patterns
- `src/utils/sub_agent_manager.py` - Task tool wrapper for sub-agent spawning

**Test Files:**
- `tests/unit/test_university_discovery.py` - Update for agentic pattern
- `tests/unit/test_professor_discovery.py` - Update for agentic pattern
- `tests/unit/test_lab_research.py` - Update for agentic pattern
- `tests/integration/test_agentic_discovery.py` - New integration tests

**Scope:** ~2000-3000 lines of code changes

---

### 3.5 Test Suite

**Changes Required:**

**Unit Tests:**
- Mock multi-turn conversation responses
- Test sub-agent spawning logic
- Test format reinforcement patterns
- Test agent-driven tool selection

**Integration Tests:**
- End-to-end agentic discovery workflows
- Compare old vs. new pattern results
- Performance benchmarks

**Coverage Target:** Maintain 70% minimum (currently 88%)

---

## 4. Recommended Path Forward

### 4.1 Selected Approach: Option 1 - Phased Direct Adjustment

**Why This Path:**
- ✅ Achieves architectural vision efficiently
- ✅ Validates pattern before full commitment via POC
- ✅ Limits blast radius with phased rollout
- ✅ Preserves QA investment (create new refactor stories)
- ✅ Sets foundation for Epics 5-7 hybrid approach
- ✅ Can course-correct mid-refactor if issues arise

**Alternatives Considered:**
- ❌ Option 2 (Rollback): Too much wasted work (38-47 days)
- ❌ Option 3 (Defer to V2): Technical debt accumulates, refactor harder later

---

### 4.2 Phased Implementation Plan

#### **Phase 1: Proof of Concept (5 days)**

**Goal:** Validate agentic pattern with single agent before full commitment

**Scope:**
- Create experimental branch: `feature/agentic-discovery-poc`
- Implement agentic pattern for professor_discovery.py (pilot agent)
- Create agentic_patterns.py utility with reusable patterns
- Compare results: Old zero-shot vs. New agentic
- Document pattern for replication

**Success Criteria:**
- ✅ Agentic pattern successfully extracts professor data
- ✅ Multi-turn conversation logs show autonomous tool usage
- ✅ Sub-agent spawning works via Task tool
- ✅ Format reinforcement improves JSON accuracy
- ✅ Pattern documented in implementation guide

**Deliverables:**
- Working agentic professor_discovery.py
- `src/utils/agentic_patterns.py` with reusable helpers
- POC validation report comparing old vs. new
- Pattern documentation for team review

**Risk Mitigation:**
- If POC fails: Investigate SDK limitations, adjust approach
- If performance poor: Optimize multi-turn logic
- If accuracy not improved: Re-evaluate pattern benefits

---

#### **Phase 2: Core Discovery Refactor (12-15 days)**

**Goal:** Apply validated pattern to all 3 discovery agents

**Scope:**
- Refactor university_discovery.py (Epic 2)
- Refactor professor_discovery.py (Epic 3) - apply POC learnings
- Refactor lab_research.py (Epic 4)
- Update web_scraping.py for agent-driven tool selection
- Create sub_agent_manager.py utility
- Remove Python orchestration logic

**Implementation Order:**
1. **University Discovery** (3-4 days)
   - Agentic structure exploration
   - Department validation sub-agent
   - Format reinforcement for JSON output

2. **Professor Discovery** (4-5 days)
   - Apply POC pattern (already validated)
   - Parallel execution preserved (asyncio.gather)
   - Profile scraping sub-agents

3. **Lab Research** (5-6 days)
   - Agentic lab website exploration
   - Agent decides Puppeteer MCP escalation
   - Contact extraction sub-agent
   - 5-category data extraction with format reinforcement

**Success Criteria:**
- ✅ All 3 agents use consistent agentic pattern
- ✅ Sub-agent spawning works across all agents
- ✅ Python orchestration removed (agents autonomous)
- ✅ Format reinforcement improves data completeness

**Deliverables:**
- Refactored discovery agents (3 files)
- Updated utilities (2 files)
- New utilities (2 files)
- Migration guide for future agents

---

#### **Phase 3: Testing & Validation (7-10 days)**

**Goal:** Ensure refactored agents meet quality standards

**Scope:**
- Update unit tests for agentic patterns
- Create integration tests for multi-turn workflows
- Performance benchmarking (old vs. new)
- QA validation against AC from original stories
- Accuracy comparison study

**Testing Strategy:**

**Unit Tests (3-4 days):**
- Mock multi-turn conversation responses
- Test sub-agent spawning logic
- Test format reinforcement
- Test agent-driven tool selection
- Edge case handling (timeouts, failures)

**Integration Tests (2-3 days):**
- End-to-end discovery workflows
- Cross-agent sub-agent communication
- Real website scraping tests
- Performance benchmarks

**QA Validation (2-3 days):**
- Run against original Epic 2, 3, 4 acceptance criteria
- Verify data quality flags still work
- Checkpoint resumability verification
- Error handling and graceful degradation

**Success Criteria:**
- ✅ 70% test coverage maintained (target: 85%+)
- ✅ All original AC still met
- ✅ No regressions in data quality
- ✅ Performance within 20% of old implementation

**Deliverables:**
- Updated test suite (100+ tests)
- Test coverage report
- Performance benchmark report
- QA validation sign-off

---

#### **Phase 4: Documentation & Handoff (3-5 days)**

**Goal:** Update all documentation to reflect agentic architecture

**Scope:**
- Rewrite agent-definitions.md (discovery sections)
- Update implementation-patterns.md (add agentic patterns)
- Update PRD epic-details.md (clarify execution patterns)
- Create 7 new refactor story files
- Update CLAUDE.md with agentic pattern guidance
- Create agentic pattern guide for Epics 5-7

**Documentation Updates:**

**Architecture Docs (2 days):**
- `agent-definitions.md` - Complete rewrite of Phases 0-3
- `implementation-patterns.md` - Add Pattern 8 (Sub-Agents), update Pattern 0
- `core-workflows.md` - Update discovery workflows

**PRD Docs (1 day):**
- `epic-details.md` - Clarify Epic 2, 3, 4 execution patterns

**Story Files (1 day):**
- Create Stories 2.6, 3.6a/b/c, 4.6a/b/c with implementation details

**Guides (1 day):**
- `AGENTIC-PATTERN-GUIDE.md` - Comprehensive guide for future development
- Update `CLAUDE.md` with agentic examples

**Success Criteria:**
- ✅ All architecture docs reflect agentic pattern
- ✅ PRD clarifications complete
- ✅ New stories preserve QA scores
- ✅ Pattern guide ready for Epics 5-7

**Deliverables:**
- Updated architecture documentation
- 7 new story files
- Agentic pattern guide
- Updated CLAUDE.md

---

### 4.3 Timeline Summary

| Phase | Duration | Start After | Deliverables |
|-------|----------|-------------|--------------|
| Phase 1: POC | 5 days | Immediate | Validated pattern, POC report |
| Phase 2: Core Refactor | 12-15 days | Phase 1 complete | 3 refactored agents, utilities |
| Phase 3: Testing | 7-10 days | Phase 2 complete | Test suite, QA validation |
| Phase 4: Documentation | 3-5 days | Phase 3 complete | Updated docs, guides |
| **Total** | **27-35 days** | **(5-7 weeks)** | **Production-ready agentic architecture** |

**Parallelization Opportunities:**
- Phase 2: University and professor discovery can be refactored in parallel (save 2-3 days)
- Phase 3: Unit and integration testing can overlap (save 1-2 days)
- Phase 4: Documentation can start during Phase 3 QA (save 1 day)

**Optimistic Timeline:** 23-27 days (4.5-5.5 weeks) with parallelization

---

### 4.4 Resource Requirements

**Development:**
- 1 developer (primary) for core refactor
- Claude Code for implementation assistance
- Access to test universities for validation

**Testing:**
- QA validation against original AC
- Real-world scraping tests (requires live websites)
- Performance benchmarking infrastructure

**Documentation:**
- Technical writer time (or developer time for docs)
- Review by product owner and architect

---

### 4.5 Risk Assessment & Mitigation

**Risk Level: MEDIUM**

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| SDK limitations discovered | MEDIUM | HIGH | POC phase validates SDK capabilities early |
| Performance degradation | LOW | MEDIUM | Benchmark early, optimize multi-turn logic |
| Pattern too complex | LOW | HIGH | Start with simplest agent (professor), iterate |
| Timeline overrun | MEDIUM | MEDIUM | Phased approach allows re-scoping |
| Test coverage drops | LOW | MEDIUM | Maintain coverage checks in CI |
| Breaking changes in Epic 5+ | LOW | LOW | Epic 4 paused, learnings applied to 5-7 |

**Mitigation Strategies:**
1. **POC Phase:** Validates all assumptions before committing 27 days
2. **Phased Rollout:** Can stop after any phase if blockers arise
3. **Old Code Preserved:** Can rollback via git if catastrophic failure
4. **Parallel Development:** Some phase overlap reduces timeline risk

---

## 5. PRD MVP Impact

**Question:** Does this change affect MVP scope or core goals?

**Answer:** ✅ **NO** - MVP scope unchanged, implementation pattern improved

**Core MVP Goals (Unchanged):**
- ✅ Discover universities, departments, professors
- ✅ Filter by research alignment
- ✅ Scrape lab websites and publications
- ✅ Score and rank labs
- ✅ Generate actionable reports

**What Changes:**
- 🔄 HOW discovery is implemented (zero-shot → agentic)
- 🔄 Discovery accuracy likely improves
- 🔄 Code maintainability improves
- 🔄 Architecture aligns with vision

**MVP Timeline Impact:**
- Epic 4 was in progress (now paused)
- Epics 5-8 not yet started
- Refactor timeline: 5-7 weeks
- **Net Impact:** +2-4 weeks to overall MVP timeline

**Acceptable Trade-Off:** Better architecture foundation worth modest timeline extension

---

## 6. High-Level Action Plan

### 6.1 Immediate Next Steps (Next 24 Hours)

1. ✅ **Commit Current State** - Preserve Epic 2-4 work before refactor
   - Create commit: "chore: Pause Epic 4 before agentic discovery refactor (SCP-2025-10-11)"
   - Tag: `pre-agentic-refactor`

2. ✅ **Create POC Branch** - Set up experimental environment
   - Branch: `feature/agentic-discovery-poc`
   - Copy professor_discovery.py to poc_professor_discovery.py

3. ✅ **Kickoff Phase 1** - Begin POC implementation
   - Create `src/utils/agentic_patterns.py` skeleton
   - Update professor_discovery POC with multi-turn pattern
   - Document approach in POC branch README

### 6.2 Phase 1 Milestones (Days 1-5)

**Day 1:**
- ✅ POC branch setup
- ✅ Agentic pattern skeleton created
- ✅ First multi-turn conversation implemented

**Day 2-3:**
- ✅ Sub-agent spawning via Task tool working
- ✅ Format reinforcement pattern implemented
- ✅ POC professor discovery working end-to-end

**Day 4:**
- ✅ Compare POC vs. old implementation
- ✅ Document pattern differences
- ✅ Identify reusable components

**Day 5:**
- ✅ POC validation report complete
- ✅ Pattern documentation ready
- ✅ Go/no-go decision for Phase 2

### 6.3 Success Metrics

**Phase 1 (POC):**
- ✅ Pattern validated with working code
- ✅ Multi-turn logs show autonomous behavior
- ✅ Sub-agents successfully spawned
- ✅ Accuracy equal or better than zero-shot

**Phase 2 (Core Refactor):**
- ✅ All 3 agents refactored
- ✅ Consistent pattern across agents
- ✅ Python orchestration removed
- ✅ Code review approval

**Phase 3 (Testing):**
- ✅ 70%+ test coverage maintained
- ✅ All original AC met
- ✅ No regressions
- ✅ QA approval

**Phase 4 (Documentation):**
- ✅ Architecture docs updated
- ✅ 7 refactor stories created
- ✅ Pattern guide complete
- ✅ Ready for Epics 5-7

---

## 7. Agent Handoff Plan

### 7.1 Roles & Responsibilities

**Product Owner (PO) - Current Agent:**
- ✅ Change proposal approval - **COMPLETE**
- ⏳ Monitor Phase 1 POC progress
- ⏳ Review POC validation report
- ⏳ Approve Phase 2 initiation
- ⏳ Final QA validation sign-off

**Developer (Dev):**
- ⏳ Implement Phase 1 POC
- ⏳ Implement Phase 2 core refactor
- ⏳ Create agentic_patterns.py utility
- ⏳ Update test suite

**Architect:**
- ⏳ Review POC pattern design
- ⏳ Validate architectural alignment
- ⏳ Update architecture documentation

**QA Agent:**
- ⏳ Validate Phase 3 testing
- ⏳ Compare old vs. new accuracy
- ⏳ Performance benchmark analysis
- ⏳ Final QA approval

**Scrum Master (SM):**
- ⏳ Track phase progress
- ⏳ Manage sprint planning for 5-7 week effort
- ⏳ Risk monitoring and escalation

### 7.2 Handoff Points

**After This Proposal Approval:**
- ✅ Hand off to Dev: "Begin Phase 1 POC implementation"
- ✅ Hand off to SM: "Track sprint planning for 27-35 day effort"

**After Phase 1 Complete:**
- ⏳ Hand off to Architect: "Review POC pattern for architectural approval"
- ⏳ Hand off to PO: "Review POC validation report for Phase 2 approval"

**After Phase 2 Complete:**
- ⏳ Hand off to QA: "Begin Phase 3 testing and validation"

**After Phase 3 Complete:**
- ⏳ Hand off to Architect: "Update architecture documentation"
- ⏳ Hand off to PO: "Create 7 refactor stories"

**After Phase 4 Complete:**
- ⏳ Hand off to Dev: "Ready to begin Epic 5 with hybrid pattern"

---

## 8. Appendices

### Appendix A: Detailed Code Change List

**Discovery Agents (Core Refactor):**

```
src/agents/university_discovery.py
├─ discover_structure() - Rewrite for agentic exploration
├─ filter_departments() - Keep zero-shot (appropriate)
└─ New: spawn_department_validator_agent() - Sub-agent

src/agents/professor_discovery.py
├─ discover_professors_for_department() - Agentic pattern
├─ discover_professors_parallel() - Keep asyncio.gather
├─ discover_with_puppeteer_fallback() - Agent-driven escalation
└─ New: spawn_profile_scraper_agent() - Sub-agent

src/agents/lab_research.py
├─ process_single_lab() - Agentic exploration
├─ scrape_lab_website() - Agent-driven tool selection
└─ New: spawn_contact_extraction_agent() - Sub-agent
```

**Utilities (New & Updated):**

```
src/utils/agentic_patterns.py (NEW)
├─ async def agentic_discovery_with_tools()
├─ async def spawn_sub_agent()
├─ async def multi_turn_with_format_reinforcement()
└─ async def agent_driven_tool_selection()

src/utils/sub_agent_manager.py (NEW)
├─ class SubAgentManager
├─ async def spawn_agent(task_description, allowed_tools)
├─ async def collect_results()
└─ async def parallel_sub_agents()

src/utils/web_scraping.py (UPDATE)
├─ scrape_with_sufficiency() - Agent decides escalation
├─ evaluate_sufficiency() - Agent self-evaluates
└─ Remove: Python-controlled stage logic
```

**Test Files (Updated & New):**

```
tests/unit/test_agentic_patterns.py (NEW)
tests/unit/test_sub_agent_manager.py (NEW)
tests/unit/test_university_discovery.py (UPDATE)
tests/unit/test_professor_discovery.py (UPDATE)
tests/unit/test_lab_research.py (UPDATE)
tests/integration/test_agentic_discovery.py (NEW)
```

---

### Appendix B: Architecture Pattern Comparison

**Zero-Shot Pattern (Current):**

```python
# Single prompt with all instructions
prompt = f"""
Scrape {url} and extract:
- Field 1
- Field 2
- Field 3

Return as JSON: [{...}]
"""

# One query, one response
async with ClaudeSDKClient(options) as client:
    await client.query(prompt)
    async for message in client.receive_response():
        data = parse_json(message.text)  # Hope it's valid
        return data
```

**Agentic Pattern (Proposed):**

```python
# Initial task description
prompt = "Discover professors at {url}. Extract comprehensive data."

async with ClaudeSDKClient(options) as client:
    await client.query(prompt)

    # Agent explores autonomously
    turn_count = 0
    async for message in client.receive_response():
        turn_count += 1

        # Agent uses tools (WebFetch, WebSearch)
        # Agent thinks about what data is missing
        # Agent decides if more exploration needed

        if turn_count == max_turns - 1:
            # Format reinforcement
            await client.query(
                "Ensure output is JSON array: [{name, title, ...}]"
            )

        if is_complete(message):
            data = parse_json(message.text)  # More likely valid
            return data
```

---

### Appendix C: Sub-Agent Spawning Pattern

**Proposed Pattern (Using Task Tool):**

```python
from claude_agent_sdk import Task

async def discover_professors_with_sub_agents(department: Department):
    """Main agent spawns specialized sub-agents for scraping."""

    # Spawn profile scraper sub-agents
    profile_tasks = []
    for professor_url in discovered_urls:
        task = Task(
            description="Extract professor profile details",
            prompt=f"Scrape {professor_url} for research areas, lab, email",
            subagent_type="general-purpose",  # Or custom specialized agent
        )
        profile_tasks.append(task)

    # Collect results from sub-agents
    profiles = await asyncio.gather(*profile_tasks)

    return combine_results(profiles)
```

**Benefits:**
- ✅ Each sub-agent has isolated context
- ✅ Parallel execution maintained
- ✅ Specialized prompts per task
- ✅ Better error isolation

---

### Appendix D: Format Reinforcement Example

**Without Reinforcement (Current):**

```python
prompt = """
Extract professors. Return JSON: [{"name": "...", "title": "..."}]
"""

# Agent responds with mixed format:
# "Here are the professors I found:
# 1. Dr. Smith - Professor
# 2. Dr. Jones - Associate Professor"
# No JSON!
```

**With Reinforcement (Proposed):**

```python
# Turn 1: Initial request
await client.query("Extract professors from {url}")

# Agent explores, gathers data...

# Turn 3: Format reinforcement
await client.query("""
Please output the professor data as a JSON array.
Format: [{"name": "...", "title": "...", "research_areas": [...]}]
""")

# Agent now knows to format as JSON
# More likely to get valid JSON output
```

---

### Appendix E: Success Criteria Checklist

**Phase 1 POC:**
- [ ] Multi-turn conversation logs show autonomous tool usage
- [ ] Sub-agent successfully spawned via Task tool
- [ ] Format reinforcement improves JSON validity
- [ ] Accuracy equal or better than zero-shot baseline
- [ ] Pattern documented and reusable

**Phase 2 Core Refactor:**
- [ ] university_discovery.py refactored with agentic pattern
- [ ] professor_discovery.py refactored with agentic pattern
- [ ] lab_research.py refactored with agentic pattern
- [ ] agentic_patterns.py utility created
- [ ] sub_agent_manager.py utility created
- [ ] Python orchestration logic removed
- [ ] Code review approved

**Phase 3 Testing:**
- [ ] Unit test coverage ≥70% (target: 85%)
- [ ] Integration tests pass
- [ ] All Epic 2 AC met
- [ ] All Epic 3 AC met
- [ ] All Epic 4 AC met
- [ ] Performance within 20% of baseline
- [ ] No data quality regressions
- [ ] QA validation approved

**Phase 4 Documentation:**
- [ ] agent-definitions.md rewritten
- [ ] implementation-patterns.md updated
- [ ] epic-details.md clarified
- [ ] Stories 2.6, 3.6a/b/c, 4.6a/b/c created
- [ ] AGENTIC-PATTERN-GUIDE.md created
- [ ] CLAUDE.md updated
- [ ] Architecture review approved

---

## 9. Approval & Sign-Off

**Proposal Author:** Sarah (Product Owner Agent)
**Date Submitted:** 2025-10-11
**Reviewed By:** User (Product Owner)
**Status:** ✅ **APPROVED**

**Approved Decisions:**
1. ✅ Refactor Scope: Epics 2-4 now, revisit 5-7 later based on learnings
2. ✅ Epic 4 Status: PAUSE now, include in refactor
3. ✅ Future Epic Strategy: Hybrid approach - agentic for complex, zero-shot for simple
4. ✅ Story Management: Create new refactor stories to preserve QA scores
5. ✅ Path Forward: Option 1 (Phased Direct Adjustment)
6. ✅ Timeline: 27-35 days (5-7 weeks) acceptable

**Next Actions:**
1. ✅ Commit current state with tag `pre-agentic-refactor`
2. ✅ Create POC branch: `feature/agentic-discovery-poc`
3. ✅ Begin Phase 1: POC implementation

**Go/No-Go Decision Points:**
- After Phase 1: Review POC validation report before Phase 2
- After Phase 2: Review refactored code before Phase 3 testing
- After Phase 3: Review test results before Phase 4 documentation

---

**END OF SPRINT CHANGE PROPOSAL**
