# Professor Filter Flow Analysis

**File:** `src/agents/professor_filter.py` (2,419 lines)
**Stories:** 3.1a, 3.1b, 3.1c, 3.2, 3.3, 3.4, 3.5
**Analysis Date:** 2025-10-08

---

## Overview

The `professor_filter.py` module implements **three sequential pipelines** that handle professor discovery, filtering, and reporting for the Lab Finder system. This document provides a complete flow analysis.

---

## Pipeline 1: Discovery & Deduplication
**Stories:** 3.1a (Discovery), 3.1b (Parallel Processing), 3.1c (Deduplication & Rate Limiting)

### Entry Point: `discover_and_save_professors(departments, max_concurrent=5, batch_id=1)`

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: LOAD DEPARTMENTS                                       │
└─────────────────────────────────────────────────────────────────┘

load_relevant_departments(correlation_id)
    │
    ├─> Reads: checkpoints/phase-1-relevant-departments.jsonl
    ├─> Filters: is_relevant == True only
    ├─> Converts: dict → Department models
    └─> Returns: list[Department]

┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: PARALLEL DISCOVERY WITH RATE LIMITING                  │
└─────────────────────────────────────────────────────────────────┘

discover_professors_parallel(departments, max_concurrent=5)
    │
    ├─> Initialize:
    │   ├─> ProgressTracker (Phase 2: Professor Discovery)
    │   ├─> asyncio.Semaphore(max_concurrent=5)
    │   └─> DomainRateLimiter(default_rate=1.0, time_period=1.0)
    │
    ├─> For each department (parallel execution):
    │   │
    │   └─> process_with_semaphore(dept, index):
    │       │
    │       ├─> async with semaphore:  # Acquire concurrency slot
    │       │
    │       ├─> Rate limit: await rate_limiter.acquire(dept.url)
    │       │   └─> Extracts domain from URL
    │       │   └─> Creates per-domain AsyncLimiter if new
    │       │   └─> Throttles: 1 request per second per domain
    │       │
    │       ├─> discover_professors_for_department(dept, correlation_id):
    │       │   │
    │       │   ├─> PRIMARY METHOD: Claude Agent SDK
    │       │   │   ├─> ClaudeAgentOptions:
    │       │   │   │   ├─> allowed_tools=["WebFetch", "WebSearch"]
    │       │   │   │   ├─> max_turns=3
    │       │   │   │   └─> setting_sources=None (prevents context injection)
    │       │   │   │
    │       │   │   ├─> Send prompt:
    │       │   │   │   └─> "Scrape professor directory at {dept.url}"
    │       │   │   │   └─> "Extract: name, title, research areas, lab, email, profile URL"
    │       │   │   │   └─> "Return as JSON array"
    │       │   │   │
    │       │   │   ├─> Receive response:
    │       │   │   │   └─> Parse JSON via parse_professor_data()
    │       │   │   │   └─> Convert to Professor Pydantic models
    │       │   │   │
    │       │   │   └─> Add data quality flags:
    │       │   │       ├─> missing_email (if no email)
    │       │   │       ├─> missing_research_areas (if empty list)
    │       │   │       └─> missing_lab_affiliation (if no lab_name)
    │       │   │
    │       │   └─> FALLBACK METHOD: Playwright (on exception)
    │       │       ├─> @retry(stop=3, wait=exponential(min=2, max=10))
    │       │       ├─> async with async_playwright():
    │       │       │   └─> browser.chromium.launch(headless=True)
    │       │       │   └─> page.goto(dept.url, timeout=30000)
    │       │       │   └─> content = page.content()
    │       │       │
    │       │       ├─> BeautifulSoup(content, "html.parser")
    │       │       │   └─> Try SELECTOR_PATTERNS in order:
    │       │       │       [".faculty-member", ".professor-card",
    │       │       │        ".people-item", "article.faculty",
    │       │       │        "section.people", "div.directory-entry",
    │       │       │        "table.faculty tr", "table.directory tr",
    │       │       │        'a[href*="/faculty/"]', 'a[href*="/people/"]']
    │       │       │
    │       │       ├─> parse_professor_elements(elements, department)
    │       │       │   └─> Extract: name, title, email, profile_url
    │       │       │   └─> Simple keyword extraction for research areas
    │       │       │
    │       │       └─> Add flag: "scraped_with_playwright_fallback"
    │       │
    │       ├─> Returns: list[Professor] or [] on failure
    │       │
    │       └─> finally:
    │           └─> tracker.update(completed=completed_count)
    │
    └─> asyncio.gather(*tasks, return_exceptions=True)
        │
        ├─> Parallel execution: All departments simultaneously
        │   └─> Up to semaphore limit (5 concurrent)
        │
        ├─> Flatten results: all_professors = []
        │   └─> Filter out Exception instances
        │   └─> Extend with successful list[Professor] results
        │
        └─> Returns: list[Professor] (aggregated from all departments)

┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: DEDUPLICATION                                          │
└─────────────────────────────────────────────────────────────────┘

deduplicate_professors(all_professors)
    │
    ├─> Initialize:
    │   ├─> unique_professors: list[Professor] = []
    │   └─> seen_combinations: set[str] = set()
    │
    ├─> For each professor in all_professors:
    │   │
    │   ├─> STAGE 1: EXACT MATCH (fast, O(1))
    │   │   ├─> key = f"{prof.name.lower()}:{prof.department_id}"
    │   │   ├─> if key in seen_combinations:
    │   │   │   └─> Skip professor (exact duplicate found)
    │   │   └─> Performance: Reduces LLM calls by ~70%
    │   │
    │   ├─> STAGE 2: FUZZY MATCH (LLM-based, O(n) per professor)
    │   │   ├─> Only if exact match failed
    │   │   ├─> For each existing in unique_professors:
    │   │   │   └─> if existing.department_id == prof.department_id:
    │   │   │       │
    │   │   │       ├─> match_result = await match_names(existing.name, prof.name)
    │   │   │       │   └─> LLM-based name similarity (from llm_helpers)
    │   │   │       │   └─> Returns: {decision: "yes"/"no", confidence: 0-100, reasoning: "..."}
    │   │   │       │
    │   │   │       └─> DUAL THRESHOLD CHECK:
    │   │   │           └─> if (decision == "yes" AND confidence >= 90):
    │   │   │               │
    │   │   │               ├─> Duplicate confirmed!
    │   │   │               │
    │   │   │               ├─> merge_professor_records(existing, prof):
    │   │   │               │   ├─> merged_data = existing.model_dump()
    │   │   │               │   ├─> For each field in new:
    │   │   │               │   │   └─> If existing field empty, use new value
    │   │   │               │   ├─> Special handling for data_quality_flags:
    │   │   │               │   │   └─> Merge + deduplicate: list(set(old + new))
    │   │   │               │   └─> Return: Professor(**merged_data)
    │   │   │               │
    │   │   │               ├─> Remove existing from unique_professors
    │   │   │               ├─> Append merged record
    │   │   │               └─> is_duplicate = True
    │   │   │
    │   │   └─> Break inner loop if duplicate found
    │   │
    │   └─> if not is_duplicate:
    │       ├─> seen_combinations.add(key)
    │       └─> unique_professors.append(prof)
    │
    └─> Returns: unique_professors (duplicates merged)

┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: SAVE CHECKPOINT                                        │
└─────────────────────────────────────────────────────────────────┘

checkpoint_manager.save_batch(
    phase="phase-2-professors",
    batch_id=1,
    data=unique_professors
)
    │
    └─> Writes: checkpoints/phase-2-professors-batch-1.jsonl
        └─> JSONL format: one Professor model per line
        └─> Atomic write pattern for data integrity
```

### Key Optimizations

- **Rate Limiting:** 1 request/second per domain (prevents blocking)
- **Exact Match Pre-Filter:** O(1) lookup eliminates ~70% of LLM calls
- **Graceful Degradation:** Failed departments don't block others
- **Progress Tracking:** Real-time updates via ProgressTracker
- **Retry Logic:** 3 attempts with exponential backoff for Playwright
- **Concurrency Control:** Semaphore limits parallel operations

---

## Pipeline 2: Filtering & Confidence Scoring
**Stories:** 3.2 (Filtering), 3.3 (Confidence Scoring), 3.5 (Batch Processing)

### Entry Point: `filter_professors(correlation_id)`

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: LOAD USER PROFILE                                      │
└─────────────────────────────────────────────────────────────────┘

load_user_profile()
    │
    ├─> Reads: output/user_profile.md (Story 1.7 output)
    │
    ├─> Extract "Streamlined Research Focus" section:
    │   └─> Regex: r"### Streamlined Research Focus\s+(.+?)(?=\n#|\n---|\Z)"
    │
    ├─> Extract "Current Position":
    │   └─> Regex: r"\*\*Current Position:\*\* (.+)"
    │
    ├─> Validate:
    │   ├─> if not interests: raise ValueError (REQUIRED field)
    │   └─> if not degree: fallback to "General"
    │
    └─> Returns: {research_interests: str, current_degree: str}

┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: LOAD CONFIGURATION                                     │
└─────────────────────────────────────────────────────────────────┘

SystemParams.load()
    │
    ├─> Reads: config/system_params.json
    ├─> Validates: Pydantic schema
    │
    └─> Extracts:
        ├─> batch_size = batch_config.professor_filtering_batch_size
        ├─> max_concurrent = rate_limiting.max_concurrent_llm_calls
        ├─> threshold = confidence_thresholds.professor_filter (default: 70)
        ├─> low_threshold = filtering_config.low_confidence_threshold
        └─> high_threshold = filtering_config.high_confidence_threshold

┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: LOAD PROFESSORS FROM DISCOVERY CHECKPOINTS             │
└─────────────────────────────────────────────────────────────────┘

checkpoint_manager.load_batches("phase-2-professors")
    │
    ├─> Reads: checkpoints/phase-2-professors-batch-*.jsonl
    ├─> Parses: JSONL → list[dict]
    ├─> Converts: dict → Professor Pydantic models
    └─> Returns: all_professors: list[Professor]

┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: INITIALIZE PROGRESS TRACKING                           │
└─────────────────────────────────────────────────────────────────┘

tracker = ProgressTracker()
tracker.start_phase("Phase 2: Professor Filtering", total_items=len(all_professors))

┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: BATCH PROCESSING LOOP (RESUMABLE)                      │
└─────────────────────────────────────────────────────────────────┘

resume_batch = checkpoint_manager.get_resume_point("phase-2-filter")
total_batches = (len(all_professors) + batch_size - 1) // batch_size

For batch_num in range(resume_batch, total_batches):
    │
    ├─> Slice batch:
    │   ├─> start_idx = batch_num * batch_size
    │   ├─> end_idx = min(start_idx + batch_size, len(all_professors))
    │   └─> batch_professors = all_professors[start_idx:end_idx]
    │
    ├─> Update progress:
    │   └─> tracker.update_batch(batch_num + 1, total_batches, f"Professors {start_idx+1}-{end_idx}")
    │
    ├─> filter_professor_batch_parallel(batch, profile_dict, correlation_id, max_concurrent=5):
    │   │
    │   ├─> Create semaphore for rate limiting:
    │   │   └─> semaphore = asyncio.Semaphore(max_concurrent)
    │   │
    │   ├─> For each professor in batch (parallel):
    │   │   │
    │   │   └─> filter_with_limit(professor):
    │   │       │
    │   │       ├─> async with semaphore:  # Acquire rate limit slot
    │   │       │
    │   │       ├─> filter_professor_single(professor, profile_dict, prof_correlation_id):
    │   │       │   │
    │   │       │   ├─> Load threshold:
    │   │       │   │   └─> system_params.confidence_thresholds.professor_filter (default: 70)
    │   │       │   │
    │   │       │   ├─> Format inputs:
    │   │       │   │   ├─> research_areas_str = ", ".join(professor.research_areas) or "Not specified"
    │   │       │   │   └─> user_profile_str = format_profile_for_llm(profile_dict)
    │   │       │   │       └─> "Research Interests: {interests}\nDegree Program: {degree}"
    │   │       │   │
    │   │       │   ├─> Call LLM helper:
    │   │       │   │   └─> llm_result = await filter_professor_research(
    │   │       │   │           professor_name=professor.name,
    │   │       │   │           research_areas=research_areas_str,
    │   │       │   │           user_profile=user_profile_str,
    │   │       │   │           bio="",  # Not available at this phase
    │   │       │   │           correlation_id=correlation_id
    │   │       │   │       )
    │   │       │   │   └─> Returns: {confidence: Any, reasoning: str}
    │   │       │   │
    │   │       │   ├─> Validate confidence (Story 3.3):
    │   │       │   │   └─> validate_confidence_score(raw_confidence, professor.name, correlation_id):
    │   │       │   │       │
    │   │       │   │       ├─> Type conversion:
    │   │       │   │       │   ├─> Handle bool (explicit check, raises ValueError)
    │   │       │   │       │   ├─> Handle int/float (convert to int via round)
    │   │       │   │       │   ├─> Handle string (parse to float, then int)
    │   │       │   │       │   └─> Handle None/invalid (fallback to 50, add "llm_response_error" flag)
    │   │       │   │       │
    │   │       │   │       ├─> Range validation:
    │   │       │   │       │   ├─> if confidence < 0: clamp to 0, add "confidence_out_of_range" flag
    │   │       │   │       │   └─> if confidence > 100: clamp to 100, add "confidence_out_of_range" flag
    │   │       │   │       │
    │   │       │   │       └─> Returns: (validated_confidence: int, flags: list[str])
    │   │       │   │
    │   │       │   ├─> Make decision:
    │   │       │   │   └─> decision = "include" if confidence >= threshold else "exclude"
    │   │       │   │
    │   │       │   ├─> Check for low confidence (Story 3.3):
    │   │       │   │   └─> if confidence < low_threshold:
    │   │       │   │       ├─> Add flag: "low_confidence_filter"
    │   │       │   │       └─> Log warning for manual review
    │   │       │   │
    │   │       │   ├─> Log edge cases:
    │   │       │   │   ├─> Interdisciplinary (include + len(research_areas) >= 3)
    │   │       │   │   └─> Missing research areas (include + empty research_areas)
    │   │       │   │
    │   │       │   └─> Returns: {decision, confidence, reasoning, flags}
    │   │       │
    │   │       ├─> Exception handling:
    │   │       │   └─> On LLM failure: Inclusive fallback
    │   │       │       └─> {decision: "include", confidence: 0, reasoning: "LLM failed - human review"}
    │   │       │
    │   │       ├─> Update professor model:
    │   │       │   ├─> professor.is_relevant = (decision == "include")
    │   │       │   ├─> professor.relevance_confidence = confidence
    │   │       │   ├─> professor.relevance_reasoning = reasoning
    │   │       │   └─> Add data quality flags from filter_result["flags"]
    │   │       │
    │   │       └─> Returns: updated Professor model
    │   │
    │   └─> asyncio.gather(*tasks, return_exceptions=True)
    │       └─> Returns: filtered_batch: list[Professor]
    │
    ├─> Count results:
    │   ├─> included_count += sum(1 for p in filtered_batch if p.is_relevant)
    │   ├─> excluded_count += sum(1 for p in filtered_batch if not p.is_relevant)
    │   └─> failed_count += sum(1 for p in filtered_batch if "llm_filtering_failed" in p.data_quality_flags)
    │
    ├─> Update progress:
    │   └─> tracker.update(completed=processed_count)
    │
    └─> Save batch checkpoint:
        └─> checkpoint_manager.save_batch(
                phase="phase-2-filter",
                batch_id=batch_num + 1,
                data=filtered_batch
            )
        └─> Writes: checkpoints/phase-2-filter-batch-{batch_num+1}.jsonl

┌─────────────────────────────────────────────────────────────────┐
│  STEP 6: APPLY MANUAL OVERRIDES (Story 3.3)                     │
└─────────────────────────────────────────────────────────────────┘

apply_manual_overrides(all_professors)
    │
    ├─> Reads: config/manual-overrides.json (optional)
    │   └─> Format: {"professor_overrides": [{professor_id, decision, reason, timestamp, ...}]}
    │
    ├─> For each override:
    │   ├─> Find professor by ID in professors_by_id lookup
    │   ├─> Override is_relevant field: new_decision == "include"
    │   ├─> Add flag: "manual_override"
    │   └─> Update reasoning with audit trail:
    │       └─> "MANUAL OVERRIDE ({timestamp}): {reason} | Original: {orig_decision} (confidence: {orig_conf}) | LLM: {orig_reasoning}"
    │
    └─> Returns: override_count (number of overrides applied)

┌─────────────────────────────────────────────────────────────────┐
│  STEP 7: CALCULATE CONFIDENCE STATISTICS (Story 3.3)            │
└─────────────────────────────────────────────────────────────────┘

calculate_confidence_stats(all_professors)
    │
    ├─> Split by decision:
    │   ├─> included = [p for p in professors if p.is_relevant]
    │   └─> excluded = [p for p in professors if not p.is_relevant]
    │
    ├─> Categorize by confidence level:
    │   └─> For included and excluded:
    │       ├─> high = count(confidence >= high_threshold)  # ≥90
    │       ├─> medium = count(low_threshold <= confidence < high_threshold)  # 70-89
    │       └─> low = count(confidence < low_threshold)  # <70
    │
    ├─> Calculate overall low-confidence percentage:
    │   └─> low_percentage = (included_low + excluded_low) / total * 100
    │
    ├─> Quality validation:
    │   ├─> if low_percentage > 30%:
    │   │   └─> quality_assessment = "Warning - High low-confidence rate suggests prompt issues"
    │   ├─> elif low_percentage < 10%:
    │   │   └─> quality_assessment = "Good - Low ambiguity in filtering decisions"
    │   └─> else:
    │       └─> quality_assessment = "Good - Distribution matches expectations"
    │
    └─> Returns: {
            total_professors,
            included: {high, medium, low, total},
            excluded: {high, medium, low, total},
            distribution_analysis: {
                low_confidence_percentage,
                expected_range: "10-20%",
                deviation_from_expected,
                quality_assessment
            }
        }

┌─────────────────────────────────────────────────────────────────┐
│  STEP 8: SAVE CONFIDENCE STATISTICS REPORT                      │
└─────────────────────────────────────────────────────────────────┘

save_confidence_stats_report(confidence_stats)
    │
    ├─> Creates: output/ directory (if needed)
    └─> Writes: output/filter-confidence-stats.json
        └─> JSON format: Pretty-printed (indent=2)

┌─────────────────────────────────────────────────────────────────┐
│  STEP 9: RETURN FILTERED PROFESSORS                             │
└─────────────────────────────────────────────────────────────────┘

Returns: all_professors (with filtering results)
    ├─> is_relevant: bool (True = include, False = exclude)
    ├─> relevance_confidence: int (0-100)
    ├─> relevance_reasoning: str (LLM explanation)
    └─> data_quality_flags: list[str] (transparency flags)
```

### Key Features

- **Inclusive Fallback:** LLM failures → include with confidence=0 (enables human review)
- **Batch Resumability:** Uses checkpoint resume points for interrupted runs
- **Parallel LLM Calls:** Up to 5 concurrent per batch (configurable)
- **Confidence Validation:** Handles 7+ edge cases (floats, strings, negatives, out-of-range, null, bool, malformed)
- **Quality Validation:** Warns if >30% low-confidence decisions
- **Manual Overrides:** Audit trail with timestamp, original confidence, original decision

---

## Pipeline 3: Reporting & Transparency
**Story:** 3.4 (Filtered Professor Logging & Transparency)

### Entry Point 1: `generate_filter_report(professors, output_dir, correlation_id)`

```
┌─────────────────────────────────────────────────────────────────┐
│  FILTERED PROFESSORS REPORT (317 lines of code)                 │
└─────────────────────────────────────────────────────────────────┘

1. Calculate Statistics
   │
   └─> calculate_filter_statistics(professors):
       │
       ├─> Edge case handling:
       │   └─> if len(professors) == 0: return zero stats
       │
       ├─> Split by decision:
       │   ├─> included = [p for p in professors if p.is_relevant]
       │   └─> excluded = [p for p in professors if not p.is_relevant]
       │
       └─> Returns: {
               total,
               included: {count, percentage, high_confidence, medium_confidence, low_confidence},
               excluded: {count, percentage, high_confidence, medium_confidence, low_confidence}
           }

2. Log All Filter Decisions
   │
   └─> For each professor:
       └─> log_filter_decision(professor, correlation_id):
           └─> Structured log with:
               ├─> professor_id, professor_name
               ├─> department, school
               ├─> research_areas
               ├─> decision ("include"/"exclude")
               ├─> is_relevant (bool)
               ├─> relevance_confidence (0-100)
               └─> relevance_reasoning (full text)

3. Calculate Department-Level Statistics
   │
   └─> Group professors by department_name:
       │
       ├─> For each department:
       │   ├─> total = count(professors in dept)
       │   ├─> included = count(is_relevant=True)
       │   └─> excluded = count(is_relevant=False)
       │
       └─> Sort by inclusion rate (descending)

4. Generate Markdown Report
   │
   ├─> SECTION 1: Executive Summary
   │   ├─> Total Professors Evaluated
   │   ├─> Included for Analysis (count + percentage)
   │   ├─> Excluded (count + percentage)
   │   └─> Low-Confidence Decisions (with link to borderline-professors.md)
   │
   ├─> SECTION 2: Department Statistics Table
   │   └─> Columns: Department | Total | Included | Excluded | Inclusion Rate
   │       └─> Sorted by inclusion rate (highest first)
   │
   ├─> SECTION 3: Excluded Professors
   │   │
   │   ├─> High Confidence Exclusions (≥90)
   │   │   └─> Table: Name | Department | Research | Confidence | Reason
   │   │       └─> Shows first 50, indicates if more exist
   │   │
   │   ├─> Medium Confidence Exclusions (70-89)
   │   │   └─> Table: Name | Department | Research | Confidence | Reason
   │   │       └─> Shows first 20, indicates if more exist
   │   │
   │   └─> Low Confidence Exclusions (<70) ⚠️ REVIEW RECOMMENDED
   │       └─> Table: Name | Department | Research | Confidence | Reason
   │           └─> Shows first 20, cross-reference to borderline report
   │
   ├─> SECTION 4: Included Professors Summary
   │   └─> High Confidence Inclusions (≥90)
   │       └─> Table: Name | Department | Research | Confidence | Matching Reason
   │           └─> Shows first 20, indicates total count
   │
   ├─> SECTION 5: Detailed Exclusion Reasoning
   │   └─> Top 10 excluded professors with FULL reasoning text
   │       └─> Per professor: Name, Department, School, Research Areas, Confidence, Full Reasoning, Profile URL
   │
   └─> SECTION 6: How to Override Filter Decisions
       └─> Instructions for creating config/manual-professor-additions.json
           └─> JSON example format with professor_id and reason

5. Write to File
   │
   └─> output/filtered-professors.md (UTF-8 encoding)
```

### Entry Point 2: `generate_borderline_report(professors)`

```
┌─────────────────────────────────────────────────────────────────┐
│  BORDERLINE PROFESSORS REPORT (167 lines of code)               │
└─────────────────────────────────────────────────────────────────┘

1. Filter Borderline Cases
   │
   └─> borderline_professors = [p for p in professors if p.relevance_confidence < low_threshold]
       └─> Default low_threshold = 70

2. Split by Decision
   │
   ├─> included_borderline = [p for p in borderline if p.is_relevant]
   └─> excluded_borderline = [p for p in borderline if not p.is_relevant]

3. Calculate Statistics
   │
   ├─> total_borderline = len(borderline_professors)
   └─> borderline_percentage = (total_borderline / total_professors * 100)

4. Generate Markdown Report
   │
   ├─> HEADER: Summary Statistics
   │   ├─> Low Confidence Threshold: {threshold}
   │   ├─> Total Borderline Cases: {count} ({percentage}%)
   │   └─> Breakdown: {included} included, {excluded} excluded
   │
   ├─> SECTION 1: Included Professors (Low Confidence)
   │   └─> Table: Name | Department | Research | Confidence | Reasoning | Profile | Recommend Override?
   │       │
   │       └─> Override Recommendation Logic (_get_override_recommendation):
   │           ├─> if "interdisciplinary" or "cross-field" in reasoning:
   │           │   └─> "Review - interdisciplinary"
   │           ├─> elif "emerging", "new field", "cutting-edge" in reasoning:
   │           │   └─> "Consider - emerging field"
   │           ├─> elif "tangential", "weak", "minimal", "indirect" in reasoning:
   │           │   └─> "Review - tangential match" (if included) or "Likely correct" (if excluded)
   │           └─> else:
   │               └─> "Review manually"
   │
   ├─> SECTION 2: Excluded Professors (Low Confidence)
   │   └─> Table: Name | Department | Research | Confidence | Reasoning | Profile | Recommend Override?
   │       └─> Same override recommendation logic
   │
   └─> SECTION 3: Action Instructions
       └─> Manual override instructions with JSON example
           └─> Format: config/manual-overrides.json
               └─> Fields: professor_id, decision, reason, timestamp, original_confidence, original_decision

5. Write to File
   │
   └─> output/borderline-professors.md (UTF-8 encoding)
```

### Supplemental: Manual Additions (Story 3.4)

```
┌─────────────────────────────────────────────────────────────────┐
│  MANUAL ADDITIONS WORKFLOW                                      │
└─────────────────────────────────────────────────────────────────┘

1. Load Manual Additions
   │
   └─> load_manual_additions(config_path="config/manual-professor-additions.json"):
       │
       ├─> If file not found: returns {"additions": []}
       ├─> Parse JSON
       └─> Returns: {"additions": [{professor_id, reason}, ...]}

2. Apply Manual Additions
   │
   └─> apply_manual_additions(professors, additions, correlation_id):
       │
       ├─> Create lookup: professors_by_id = {p.id: p for p in professors}
       │
       ├─> For each addition:
       │   ├─> Find professor by ID
       │   ├─> Override: professor.is_relevant = True
       │   ├─> Add flag: "manual_addition"
       │   └─> Update reasoning with audit trail:
       │       └─> "MANUAL ADDITION: {reason} | Original: {old_decision} (confidence: {conf}) | Original: {old_reasoning}"
       │
       ├─> If addition_count > 0:
       │   └─> Save checkpoint:
       │       └─> phase-2-professors-with-manual-additions-batch-1.jsonl
       │
       └─> Returns: professors (updated list)

EXECUTION TIMING:
└─> Must execute BEFORE report generation to include overridden professors in reports
```

---

## Critical Data Quality Flags

Throughout all pipelines, the system adds transparency flags:

### Discovery Flags (Pipeline 1)
- `scraped_with_playwright_fallback` - WebFetch failed, used Playwright
- `missing_email` - No email address found
- `missing_research_areas` - No research areas extracted
- `missing_lab_affiliation` - No lab name found

### Filtering Flags (Pipeline 2)
- `llm_filtering_failed` - LLM call failed, inclusive fallback applied
- `low_confidence_filter` - Confidence < low_threshold (70), needs review
- `llm_response_error` - Invalid confidence type or missing field
- `confidence_out_of_range` - Confidence clamped (negative or >100)
- `manual_override` - User manually overrode filter decision
- `manual_addition` - User manually added despite exclusion

---

## Execution Order in Practice

Typical usage in main pipeline (`coordinator.py`):

```python
# ============================================================
# PHASE 2a: DISCOVERY & DEDUPLICATION
# ============================================================

professors = await discover_and_save_professors(
    departments=None,  # Auto-loads from phase-1-relevant-departments.jsonl
    max_concurrent=5,   # 5 departments processed simultaneously
    batch_id=1          # Single consolidated batch
)

# Output:
#   checkpoints/phase-2-professors-batch-1.jsonl

# ============================================================
# PHASE 2b: FILTERING & CONFIDENCE SCORING
# ============================================================

filtered_professors = await filter_professors(
    correlation_id="phase-2-filtering"
)

# Output:
#   checkpoints/phase-2-filter-batch-1.jsonl
#   checkpoints/phase-2-filter-batch-2.jsonl
#   ...
#   output/filter-confidence-stats.json

# ============================================================
# PHASE 2c: REPORTING & TRANSPARENCY (manual trigger)
# ============================================================

# Generate comprehensive filtering report
await generate_filter_report(
    professors=filtered_professors,
    output_dir="output",
    correlation_id="phase-2-reporting"
)

# Generate borderline cases review report
generate_borderline_report(filtered_professors)

# Output:
#   output/filtered-professors.md
#   output/borderline-professors.md
```

---

## Performance Characteristics

| Operation | Concurrency | Rate Limiting | LLM Calls | Resumable | Complexity |
|-----------|-------------|---------------|-----------|-----------|------------|
| **Discovery per dept** | 5 parallel | 1 req/sec/domain | 0-1 (dedup only) | ✅ Batch | O(n) per dept |
| **Deduplication** | Sequential | N/A | O(n²) fuzzy matches | ❌ All-or-nothing | O(n²) worst case |
| **Filtering per batch** | 5 parallel LLM | Semaphore | 1 per professor | ✅ Batch | O(n) |
| **Reporting** | Sequential | N/A | 0 | ❌ Generation | O(n) |

### Scaling Thresholds

From Story 3.1c documentation:

- **50 professors:** Current implementation optimal
- **200 professors:** Consider increasing max_concurrent to 10
- **500+ professors:**
  - Increase max_concurrent to 15-20
  - Consider caching LLM deduplication results
  - Consider multi-stage deduplication (phonetic → LLM)

---

## Checkpoint Files Generated

```
checkpoints/
├── phase-1-relevant-departments.jsonl      # INPUT (from Epic 2)
├── phase-2-professors-batch-1.jsonl        # Discovery output
├── phase-2-filter-batch-1.jsonl            # Filtering output (batch 1)
├── phase-2-filter-batch-2.jsonl            # Filtering output (batch 2)
├── phase-2-filter-batch-N.jsonl            # Filtering output (batch N)
└── phase-2-professors-with-manual-additions-batch-1.jsonl  # After manual additions

output/
├── user_profile.md                         # INPUT (from Story 1.7)
├── filter-confidence-stats.json            # Statistics report
├── filtered-professors.md                  # Main filtering report
└── borderline-professors.md                # Low-confidence review report

config/
├── system_params.json                      # INPUT (configuration)
├── manual-overrides.json                   # OPTIONAL (user overrides)
└── manual-professor-additions.json         # OPTIONAL (user additions)
```

---

## Refactoring Recommendation

**Current State:** 2,419 lines in single file
**Issues:** Violates Single Responsibility Principle, hard to test individual concerns

**Proposed Module Structure:**

```
src/agents/professor/
├── __init__.py
├── discovery.py          # ~550 lines: Story 3.1a + 3.1b
├── deduplication.py      # ~250 lines: Story 3.1c
├── filtering.py          # ~450 lines: Story 3.2 + 3.3 + 3.5
├── statistics.py         # ~200 lines: Story 3.3
├── reporting.py          # ~650 lines: Story 3.4 (BIGGEST WIN)
├── manual_overrides.py   # ~200 lines: Story 3.3/3.4
└── pipeline.py           # ~150 lines: Orchestration
```

**Immediate Quick Win:** Extract `reporting.py` (512 lines reduction in 30 minutes)

---

## Architecture Strengths

1. **Excellent separation of concerns** (conceptually)
2. **Comprehensive error handling** with graceful degradation
3. **Resumability** via checkpoint system
4. **Transparency** via data quality flags
5. **Rate limiting** prevents server blocking
6. **Inclusive fallbacks** ensure no data loss
7. **Manual override support** for user control

## Architecture Weaknesses

1. **Single 2,419-line file** (should be 7 modules)
2. **No class-based encapsulation** (all functions)
3. **Deduplication O(n²) complexity** (doesn't scale beyond 500 professors)
4. **Hard-to-test** (must mock entire file)
5. **Large reporting functions** (317 lines, 167 lines)

---

**End of Flow Analysis**
