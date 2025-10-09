# SPRINT CHANGE PROPOSAL
## Professor Filter Module Refactoring

**Date:** 2025-10-09
**Change Type:** Proactive Technical Debt Reduction (Refactoring)
**Scope:** Structural improvement with zero functional changes
**Status:** ✅ **APPROVED**
**Approved By:** User
**Approval Date:** 2025-10-09

---

## EXECUTIVE SUMMARY

**Problem:** The `professor_filter.py` module has grown to 2,419 lines containing implementations from 6 user stories (Stories 3.1a, 3.1b, 3.1c, 3.2, 3.3, 3.4), violating separation of concerns and making maintenance difficult.

**Solution:** Split into 6 logically organized modules with clear responsibilities.

**Impact:** Zero functional changes, improved maintainability, clearer organization.

**Effort:** 2-3 hours

**Risk:** Low (comprehensive test coverage validates behavior preservation)

**Status:** Approved for implementation

---

## 1. IDENTIFIED ISSUE SUMMARY

### Triggering Event
User requested course correction to split `src/agents/professor_filter.py` into multiple files.

### Core Problem
The `professor_filter.py` module has grown to **2,419 lines** containing implementations from **6 user stories** (Stories 3.1a, 3.1b, 3.1c, 3.2, 3.3, 3.4). This monolithic structure:
- ❌ Violates separation of concerns principle
- ❌ Makes navigation and maintenance difficult
- ❌ Combines unrelated responsibilities (discovery, filtering, reporting, utilities)
- ❌ Increases cognitive load for developers

### Issue Classification
- **Type:** Proactive architectural improvement
- **Severity:** Medium (technical debt, not blocking)
- **Functional Impact:** None (purely structural refactoring)

### Evidence
- File size: 2,419 lines
- Function count: 32 functions across 6 story implementations
- Current structure: Single file with 5 distinct functional areas
- Import usage: 10 files import from this module
- Test coverage: 445 tests passing (validates behavior preservation)

---

## 2. EPIC IMPACT ASSESSMENT

### Current Epic: Epic 4 (Lab Intelligence)
- **Status:** In Progress
- **Completed Stories:** 4.1 (Lab Discovery), 4.2 (Archive.org Integration)
- **Impact:** ✅ No epic modification needed
- **Reasoning:** This is technical debt work, not a user-facing story

### Future Epics (5-8)
- **Impact:** Import statements need updating in future stories
- **Mitigation:** Clear migration guide prevents confusion

### Story Dependencies
| Story | Impact | Action Required |
|-------|--------|----------------|
| 4.2 (Archive.org) | ✅ Complete | None - already using `DomainRateLimiter` |
| 4.3-4.4 (Pending) | ⚠️ May import | Update imports if needed |
| Epic 5-8 | ⚠️ May import | Follow new structure |

---

## 3. ARTIFACT CONFLICT & IMPACT ANALYSIS

### PRD (Product Requirements Document)
- **Conflicts:** ✅ None
- **Reasoning:** Refactoring doesn't change functionality or requirements

### Architecture Documentation
- **Conflicts:** ⚠️ Requires updates
- **Files Affected:**
  - `docs/architecture/source-tree.md` - **MUST UPDATE** with new module structure
  - `docs/architecture/components.md` - **SHOULD UPDATE** to reflect new organization
  - `CLAUDE.md` - **SHOULD UPDATE** with new import patterns

### Test Files
- **Conflicts:** ⚠️ Import statements need updating
- **Files Affected:**
  1. `tests/unit/test_professor_filter.py` (4 imports)
  2. `tests/unit/test_confidence_scoring.py` (6 imports)
  3. `tests/unit/test_filter_logging.py` (5 imports)
  4. `tests/integration/test_professor_discovery.py` (4 imports)
  5. `tests/integration/test_professor_batch_processing.py` (3 imports)
  6. (Estimated ~30-40 import statement updates total)

### Source Code Files
- **Conflicts:** ⚠️ Import statement needs updating
- **Files Affected:**
  1. `src/agents/lab_research.py` (imports `DomainRateLimiter`)

### Story Documentation
- **Conflicts:** ⚠️ Low priority (documentation only)
- **Files Affected:**
  - `docs/stories/3.2.professor-filtering.md`
  - `docs/stories/3.4.filtered-professor-logging.md`
  - `docs/stories/3.5.batch-processing-professors.md`
  - `docs/stories/4.2.archive-org-integration.md`

---

## 4. PROPOSED FILE STRUCTURE & SPLITS

### New Module Organization

```
src/agents/
├── professor_discovery.py        (~800 lines) - Stories 3.1a, 3.1b, 3.1c (discovery)
├── professor_filtering.py        (~700 lines) - Stories 3.2, 3.5 (filtering)
└── professor_reporting.py        (~600 lines) - Story 3.4 (reporting/transparency)

src/utils/
├── rate_limiter.py                (~90 lines) - Story 3.1c (rate limiting utility)
├── deduplication.py              (~200 lines) - Story 3.1c (deduplication logic)
└── confidence.py                 (~300 lines) - Story 3.3 (confidence scoring)
```

### Module 1: `src/agents/professor_discovery.py`
**Responsibility:** Professor discovery and parallel processing (Stories 3.1a, 3.1b, 3.1c)

**Exports:**
```python
# Discovery functions
def discover_professors_for_department(department, correlation_id) -> list[Professor]
def discover_with_playwright_fallback(department, correlation_id) -> list[Professor]
def discover_professors_parallel(departments, max_concurrent=5) -> list[Professor]
def discover_and_save_professors(...) -> list[Professor]  # Orchestrator

# Helper functions
def load_relevant_departments(correlation_id) -> list[Department]
def generate_professor_id(name, department_id) -> str
def parse_professor_data(text) -> list[dict]
def parse_professor_elements(elements, department) -> list[dict]

# Constants
SELECTOR_PATTERNS: list[str]
```

**Imports:**
```python
from src.utils.rate_limiter import DomainRateLimiter
from src.utils.deduplication import deduplicate_professors
```

---

### Module 2: `src/agents/professor_filtering.py`
**Responsibility:** Professor filtering logic and batch orchestration (Stories 3.2, 3.5)

**Exports:**
```python
# Main filtering functions
async def filter_professor_single(professor, profile_dict, correlation_id) -> dict
async def filter_professor_batch_parallel(batch, profile_dict, correlation_id, max_concurrent=5) -> list[Professor]
async def filter_professors(correlation_id) -> list[Professor]  # Main orchestrator

# Profile loading
def load_user_profile() -> dict[str, str]
def format_profile_for_llm(profile_dict) -> str
```

**Imports:**
```python
from src.utils.confidence import validate_confidence_score
from src.agents.professor_reporting import apply_manual_additions
```

---

### Module 3: `src/agents/professor_reporting.py`
**Responsibility:** Report generation, logging, manual overrides (Story 3.4)

**Exports:**
```python
# Report generation
async def generate_filter_report(professors, output_dir, correlation_id) -> None

# Logging and statistics
def log_filter_decision(professor, correlation_id) -> None
def calculate_filter_statistics(professors) -> dict[str, Any]

# Manual overrides
async def load_manual_additions(config_path="...") -> dict[str, Any]
async def apply_manual_additions(professors, additions, correlation_id) -> list[Professor]
```

**Imports:**
```python
from src.utils.confidence import calculate_confidence_stats
```

---

### Module 4: `src/utils/confidence.py`
**Responsibility:** Confidence scoring, validation, and borderline analysis (Story 3.3)

**Exports:**
```python
# Confidence validation
def validate_confidence_score(raw_confidence, professor_name, correlation_id) -> tuple[int, list[str]]

# Statistics and reporting
def calculate_confidence_stats(professors) -> dict[str, Any]
def save_confidence_stats_report(stats) -> None

# Borderline cases
def generate_borderline_report(professors) -> None
def _get_override_recommendation(reasoning, is_relevant) -> str

# Manual overrides
def apply_manual_overrides(professors) -> int
```

---

### Module 5: `src/utils/deduplication.py`
**Responsibility:** Professor deduplication logic (Story 3.1c)

**Exports:**
```python
async def deduplicate_professors(professors) -> list[Professor]
def merge_professor_records(existing, new) -> Professor
```

---

### Module 6: `src/utils/rate_limiter.py`
**Responsibility:** Per-domain rate limiting utility (Story 3.1c)

**Exports:**
```python
class DomainRateLimiter:
    def __init__(self, default_rate=1.0, time_period=1.0)
    async def acquire(self, url) -> None
```

---

## 5. SPECIFIC IMPORT UPDATES REQUIRED

### Source Code Files (1 file)

**File: `src/agents/lab_research.py`**
```python
# OLD:
from src.agents.professor_filter import DomainRateLimiter

# NEW:
from src.utils.rate_limiter import DomainRateLimiter
```

---

### Test Files (5 files)

**File: `tests/unit/test_professor_filter.py`**
```python
# OLD:
from src.agents.professor_filter import (
    load_user_profile,
    format_profile_for_llm,
    filter_professor_single,
    filter_professors,
)

# NEW:
from src.agents.professor_filtering import (
    load_user_profile,
    format_profile_for_llm,
    filter_professor_single,
    filter_professors,
)
```

**File: `tests/unit/test_confidence_scoring.py`**
```python
# OLD:
from src.agents.professor_filter import (
    validate_confidence_score,
    calculate_confidence_stats,
    generate_borderline_report,
    save_confidence_stats_report,
    apply_manual_overrides,
    _get_override_recommendation,
)

# NEW:
from src.utils.confidence import (
    validate_confidence_score,
    calculate_confidence_stats,
    generate_borderline_report,
    save_confidence_stats_report,
    apply_manual_overrides,
    _get_override_recommendation,
)
```

**File: `tests/unit/test_filter_logging.py`**
```python
# OLD:
from src.agents.professor_filter import (
    log_filter_decision,
    calculate_filter_statistics,
    generate_filter_report,
    load_manual_additions,
    apply_manual_additions,
)

# NEW:
from src.agents.professor_reporting import (
    log_filter_decision,
    calculate_filter_statistics,
    generate_filter_report,
    load_manual_additions,
    apply_manual_additions,
)
```

**File: `tests/integration/test_professor_discovery.py`**
```python
# OLD:
from src.agents.professor_filter import (
    discover_professors_for_department,
    discover_professors_parallel,
    deduplicate_professors,
    discover_and_save_professors,
)

# NEW:
from src.agents.professor_discovery import (
    discover_professors_for_department,
    discover_professors_parallel,
    discover_and_save_professors,
)
from src.utils.deduplication import deduplicate_professors
```

**File: `tests/integration/test_professor_batch_processing.py`**
```python
# OLD:
from src.agents.professor_filter import (
    filter_professors,
    filter_professor_batch_parallel,
    load_user_profile,
)

# NEW:
from src.agents.professor_filtering import (
    filter_professors,
    filter_professor_batch_parallel,
    load_user_profile,
)
```

---

## 6. DOCUMENTATION UPDATES REQUIRED

### Architecture Documentation (MUST UPDATE)

**File: `docs/architecture/source-tree.md`**

**Section to Update:** Professor-related modules listing

**OLD:**
```
src/agents/
└── professor_filter.py        # Stories 3.1a-3.4
```

**NEW:**
```
src/agents/
├── professor_discovery.py     # Stories 3.1a, 3.1b, 3.1c (discovery)
├── professor_filtering.py     # Stories 3.2, 3.5 (filtering)
└── professor_reporting.py     # Story 3.4 (reporting)

src/utils/
├── rate_limiter.py            # Story 3.1c (DomainRateLimiter)
├── deduplication.py           # Story 3.1c (deduplication)
└── confidence.py              # Story 3.3 (confidence scoring)
```

---

### CLAUDE.md (SHOULD UPDATE)

**Add Import Pattern Examples Section:**

```markdown
## Professor Module Import Patterns

After refactoring (2025-10-09), professor-related functionality is organized across multiple modules:

### Discovery & Parallel Processing
```python
from src.agents.professor_discovery import (
    discover_professors_for_department,
    discover_professors_parallel,
    discover_and_save_professors,
)
```

### Filtering & Batch Processing
```python
from src.agents.professor_filtering import (
    filter_professor_single,
    filter_professors,
    load_user_profile,
)
```

### Reporting & Transparency
```python
from src.agents.professor_reporting import (
    generate_filter_report,
    log_filter_decision,
    calculate_filter_statistics,
)
```

### Utilities
```python
from src.utils.rate_limiter import DomainRateLimiter
from src.utils.deduplication import deduplicate_professors
from src.utils.confidence import (
    validate_confidence_score,
    calculate_confidence_stats,
    generate_borderline_report,
)
```
```

---

## 7. IMPLEMENTATION PLAN

### Phase 1: Preparation (5 minutes)
1. Create feature branch: `git checkout -b refactor/split-professor-filter`
2. Verify all tests pass on current code: `pytest tests/ -v`
3. Record baseline: 445 tests passing, ruff ✅, mypy ✅

### Phase 2: Module Creation (30 minutes)
1. Create `src/agents/professor_discovery.py` with discovery functions
2. Create `src/agents/professor_filtering.py` with filtering functions
3. Create `src/agents/professor_reporting.py` with reporting functions
4. Create `src/utils/rate_limiter.py` with DomainRateLimiter class
5. Create `src/utils/deduplication.py` with deduplication logic
6. Create `src/utils/confidence.py` with confidence scoring logic
7. Add appropriate docstrings to each new module

### Phase 3: Import Updates (45 minutes)
1. Update `src/agents/lab_research.py` import (1 file)
2. Update test file imports (5 files)
3. Run `ruff check --fix src/ tests/` to catch import errors
4. Run `mypy src/` to validate type consistency

### Phase 4: Testing & Validation (15 minutes)
1. Run full test suite: `pytest tests/ -v`
2. Verify all 445 tests still pass
3. Check coverage remains ≥70%: `pytest tests/ --cov=src`
4. Run linting: `ruff check src/ tests/`
5. Run type checking: `mypy src/`

### Phase 5: Documentation Updates (30 minutes)
1. Update `docs/architecture/source-tree.md`
2. Update `docs/architecture/components.md` (if needed)
3. Update `CLAUDE.md` with new import patterns
4. Update story documentation (lower priority)

### Phase 6: Cleanup & Final Validation (10 minutes)
1. Delete `src/agents/professor_filter.py`
2. Search for any remaining references: `grep -r "professor_filter" src/ tests/ docs/`
3. Final validation suite:
   - `ruff check src/ tests/`
   - `mypy src/`
   - `pytest tests/ -v`

### Phase 7: Commit & Review (30 minutes)
1. Review git diff (should show primarily file moves)
2. Create descriptive commit message
3. Push branch: `git push origin refactor/split-professor-filter`
4. Create PR (if using PR workflow) or merge to main

**Total Estimated Time:** 2.5-3 hours

---

## 8. VALIDATION CHECKLIST

Before considering this refactoring complete, verify:

- [ ] All 445 tests pass without modification
- [ ] `ruff check src/ tests/` passes with zero errors
- [ ] `mypy src/` passes with zero errors
- [ ] No references to `professor_filter.py` remain in codebase
- [ ] `docs/architecture/source-tree.md` updated
- [ ] `CLAUDE.md` updated with new import patterns
- [ ] Git diff shows only code moves (no functional changes)
- [ ] New modules follow coding standards (docstrings, type hints)
- [ ] Coverage remains ≥70%
- [ ] All imports use absolute paths
- [ ] Each new module has clear, single responsibility

---

## 9. RISK ASSESSMENT & MITIGATION

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Import errors after refactoring | Low | Medium | Use ruff/mypy; comprehensive test suite catches errors immediately |
| Test failures | Very Low | High | All 445 tests validate behavior; run before/after comparison |
| Merge conflicts | Medium | Low | Complete quickly; communicate with team; small surface area |
| Missing references | Low | Medium | Grep validation step; code review; IDE search |
| Documentation drift | Medium | Low | Update docs as mandatory part of refactoring checklist |
| Circular imports | Very Low | High | Clear dependency hierarchy prevents cycles |

**Overall Risk Level:** ✅ **Low** (well-tested, non-functional change with comprehensive validation)

---

## 10. SUCCESS CRITERIA

✅ **This refactoring is considered successful when:**

1. ✅ All 445 tests pass without test code modification
2. ✅ `ruff check` and `mypy` pass with zero errors
3. ✅ No references to `professor_filter.py` remain in codebase
4. ✅ Architecture documentation reflects new structure
5. ✅ Git diff shows only code moves (no functional changes)
6. ✅ New module structure follows coding standards
7. ✅ Future developers can easily find functions in logical locations
8. ✅ Test coverage remains ≥70%
9. ✅ Each new module has clear, documented responsibility

---

## 11. ROLLBACK PLAN

If issues arise during implementation:

### Scenario 1: Tests Fail After Refactoring
**Action:**
1. Identify failing tests
2. Check if issue is import-related (fix imports) or functional (investigate)
3. If functional changes detected, revert entire refactoring
4. Re-analyze and re-plan

### Scenario 2: Performance Degradation
**Action:**
1. Unlikely (no functional changes), but if detected:
2. Profile code to identify issue
3. Optimize if possible, otherwise revert

### Scenario 3: Import Errors Not Caught by Tools
**Action:**
1. Search for runtime import errors
2. Fix remaining imports
3. Add to validation checklist

### Scenario 4: Need to Abort Mid-Refactoring
**Action:**
1. Discard feature branch: `git checkout main && git branch -D refactor/split-professor-filter`
2. No impact on main branch
3. Re-approach with different strategy if needed

---

## 12. LESSONS LEARNED (Post-Implementation)

_To be filled after implementation completion_

### What Went Well
-

### What Could Be Improved
-

### Unexpected Issues
-

### Time Actual vs. Estimated
-

---

## 13. APPROVAL & SIGN-OFF

**Proposed By:** Sarah (Product Owner Agent)
**Proposal Date:** 2025-10-09
**Approved By:** User
**Approval Date:** 2025-10-09
**Status:** ✅ **APPROVED FOR IMPLEMENTATION**

**Next Action:** Developer to execute 7-phase implementation plan outlined above.

---

## 14. REFERENCES

- **Original File:** `src/agents/professor_filter.py` (2,419 lines)
- **Related Stories:** 3.1a, 3.1b, 3.1c, 3.2, 3.3, 3.4, 3.5
- **Test Coverage:** 445 tests (138 from Epic 3)
- **Coding Standards:** `docs/architecture/coding-standards.md`
- **Change Checklist:** `.bmad-core/checklists/change-checklist.md`

---

**End of Sprint Change Proposal**
