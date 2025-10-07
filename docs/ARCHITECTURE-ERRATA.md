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

## Change Log

| Date | Action | Description |
|------|--------|-------------|
| 2025-10-06 | Reported | Bob (SM) discovered during Epic 5 story validation |
| 2025-10-06 | Workaround | Stories 5.1-5.3 updated with correct dependencies and paths |
