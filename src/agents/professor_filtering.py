"""Professor Filtering Agent.

Stories 3.2, 3.5: LLM-based professor filtering and batch processing.

Provides functions for:
- Loading user research profiles
- Filtering professors based on research alignment
- Parallel batch processing with rate limiting
- Complete filtering workflow orchestration
"""

import asyncio
import re
from pathlib import Path
from typing import Any

from src.models.config import SystemParams
from src.models.professor import Professor
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.confidence import (
    apply_manual_overrides,
    calculate_confidence_stats,
    save_confidence_stats_report,
    validate_confidence_score,
)
from src.utils.llm_helpers import filter_professor_research
from src.utils.logger import get_logger
from src.utils.progress_tracker import ProgressTracker


def load_user_profile() -> dict[str, str]:
    """Load consolidated user profile from Story 1.7 output.

    Story 3.2: Task 1 - Load User Research Profile

    Reads output/user_profile.md and extracts structured data for filtering.
    For filtering, we need research interests and degree.

    Returns:
        Dict with research_interests and current_degree fields

    Raises:
        FileNotFoundError: If user profile doesn't exist
        ValueError: If research interests are missing (required field)
    """
    logger = get_logger(
        correlation_id="profile-loading",
        phase="professor_filtering",
        component="professor_filtering",
    )

    profile_path = Path("output/user_profile.md")

    if not profile_path.exists():
        logger.error("User profile not found", path=str(profile_path))
        raise FileNotFoundError(
            "User profile must be generated via Story 1.7 first. "
            "Run profile consolidation before filtering."
        )

    content = profile_path.read_text(encoding="utf-8")

    # Extract research interests from "Streamlined Research Focus" section
    interests_match = re.search(
        r"### Streamlined Research Focus\s+(.+?)(?=\n#|\n---|\Z)", content, re.DOTALL
    )
    interests = interests_match.group(1).strip() if interests_match else ""

    # Extract current position/degree
    degree_match = re.search(r"\*\*Current Position:\*\* (.+)", content)
    degree = degree_match.group(1).strip() if degree_match else ""

    # Critical field validation
    if not interests:
        logger.error("Research interests missing from user profile")
        raise ValueError(
            "Cannot filter professors without research interests. "
            "User profile is incomplete."
        )

    # Optional field fallback
    if not degree:
        logger.warning("Current degree missing, using 'General' as fallback")
        degree = "General"

    logger.info(
        "User profile loaded successfully",
        interests_length=len(interests),
        degree=degree,
    )

    return {"research_interests": interests, "current_degree": degree}


def format_profile_for_llm(profile_dict: dict[str, str]) -> str:
    """Format profile dict as string for llm_helpers.filter_professor_research().

    Story 3.2: Task 3.1 - Prepare profile for LLM

    Args:
        profile_dict: Dict with research_interests and current_degree

    Returns:
        Formatted profile string for LLM prompt
    """
    return f"""Research Interests: {profile_dict["research_interests"]}
Degree Program: {profile_dict["current_degree"]}"""


async def filter_professor_single(
    professor: Professor, profile_dict: dict[str, str], correlation_id: str
) -> dict[str, Any]:
    """Filter single professor using LLM-based research alignment analysis.

    Story 3.2: Task 3 - Core LLM Filtering Function

    Calls llm_helpers.filter_professor_research() and maps confidence score
    to include/exclude decision using threshold from system_params.json.

    Decision Logic:
    - confidence >= 70 → "include"
    - confidence < 70 → "exclude"

    Edge Cases Handled:
    - Interdisciplinary researchers: ANY research overlap → include
    - Emerging fields: Conceptually related → include
    - Missing research areas: Include by default (investigate later)
    - LLM failures: Inclusive fallback with data quality flag

    Args:
        professor: Professor model to filter
        profile_dict: User profile dict from load_user_profile()
        correlation_id: Correlation ID for logging

    Returns:
        Dict with decision ("include"/"exclude"), confidence (0-100), and reasoning (str)
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_filtering",
        component="professor_filtering",
    )

    # Load configuration
    system_params = SystemParams.load()
    threshold = system_params.confidence_thresholds.professor_filter

    # Format inputs for LLM helper
    research_areas_str = (
        ", ".join(professor.research_areas)
        if professor.research_areas
        else "Not specified"
    )
    user_profile_str = format_profile_for_llm(profile_dict)

    logger.debug(
        "Filtering professor",
        professor=professor.name,
        research_areas=research_areas_str,
    )

    try:
        # Call existing LLM helper (returns {"confidence": 0-100, "reasoning": "..."})
        llm_result = await filter_professor_research(
            professor_name=professor.name,
            research_areas=research_areas_str,
            user_profile=user_profile_str,
            bio="",  # Bio not available at this phase
            correlation_id=correlation_id,
        )

        # Story 3.3 Task 4: Validate confidence score
        raw_confidence = llm_result.get("confidence")

        # Handle missing confidence field
        if raw_confidence is None:
            logger.warning(
                "Missing confidence field in LLM response",
                professor=professor.name,
            )
            confidence = 50
            confidence_flags = ["llm_response_error"]
        else:
            # Validate and normalize confidence
            confidence, confidence_flags = validate_confidence_score(
                raw_confidence, professor.name, correlation_id
            )

        reasoning = llm_result.get("reasoning", "")

        # Map confidence to decision using threshold
        decision = "include" if confidence >= threshold else "exclude"

        # Story 3.3 Task 5: Identify low-confidence decisions
        system_params = SystemParams.load()
        low_threshold = system_params.filtering_config.low_confidence_threshold

        if confidence < low_threshold:
            confidence_flags.append("low_confidence_filter")
            logger.warning(
                "Low confidence decision flagged for review",
                professor=professor.name,
                confidence=confidence,
                decision=decision,
                reasoning=reasoning[:100],
            )

        # Log interdisciplinary cases (high confidence, multiple research areas)
        if decision == "include" and len(professor.research_areas) >= 3:
            logger.info(
                "Interdisciplinary professor included",
                professor=professor.name,
                research_areas=professor.research_areas,
                confidence=confidence,
            )

        # Log edge cases (missing research areas but included)
        if decision == "include" and not professor.research_areas:
            logger.warning(
                "Professor with missing research areas included by default",
                professor=professor.name,
                confidence=confidence,
            )

        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": reasoning,
            "flags": confidence_flags,
        }

    except Exception as e:
        logger.error(
            "LLM filtering failed, using inclusive fallback",
            professor=professor.name,
            error=str(e),
        )
        # Inclusive fallback: include by default when LLM fails
        return {
            "decision": "include",
            "confidence": 0,
            "reasoning": f"LLM call failed ({str(e)[:50]}...) - included by default for human review",
            "flags": [],
        }


async def filter_professor_batch_parallel(
    batch: list[Professor],
    profile_dict: dict[str, str],
    correlation_id: str,
    max_concurrent: int = 5,
) -> list[Professor]:
    """Filter batch of professors in parallel with semaphore rate limiting.

    Story 3.5: Task 7 - Parallel LLM calls within batch

    Uses asyncio.Semaphore to limit concurrent LLM calls and prevent API throttling.
    All professors in batch are processed simultaneously (up to semaphore limit).

    Args:
        batch: List of Professor models to filter
        profile_dict: User profile dict from load_user_profile()
        correlation_id: Correlation ID for logging
        max_concurrent: Maximum concurrent LLM calls (default: 5)

    Returns:
        List of Professor models with filter results applied
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_filtering",
        component="professor_filtering",
    )

    # Create semaphore for rate limiting (Story 3.5 Task 7)
    semaphore = asyncio.Semaphore(max_concurrent)

    logger.debug(
        f"Processing batch with {len(batch)} professors (max {max_concurrent} concurrent)"
    )

    async def filter_with_limit(professor: Professor) -> Professor:
        """Filter single professor with semaphore rate limiting."""
        async with semaphore:
            # Generate unique correlation ID for this professor
            prof_correlation_id = f"{correlation_id}-{professor.id}"

            try:
                # Call filtering function (Story 3.2)
                filter_result = await filter_professor_single(
                    professor, profile_dict, prof_correlation_id
                )

                # Update professor model fields
                professor.is_relevant = filter_result["decision"] == "include"
                professor.relevance_confidence = filter_result["confidence"]
                professor.relevance_reasoning = filter_result["reasoning"]

                # Add confidence validation flags (Story 3.3)
                for flag in filter_result.get("flags", []):
                    professor.add_quality_flag(flag)

                # Add data quality flags
                if filter_result["confidence"] == 0:
                    professor.add_quality_flag("llm_filtering_failed")

                return professor

            except Exception as e:
                # Story 3.5 Task 8: Individual professor failure handling
                logger.error(
                    "Failed to filter professor in batch",
                    professor=professor.name,
                    error=str(e),
                )
                # Inclusive fallback
                professor.is_relevant = True
                professor.relevance_confidence = 0
                professor.relevance_reasoning = f"Filter error: {str(e)[:100]}"
                professor.add_quality_flag("llm_filtering_failed")
                return professor

    # Launch all LLM filter calls in parallel (Story 3.5 Task 7)
    tasks = [filter_with_limit(p) for p in batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results (handle any exceptions that weren't caught)
    filtered_batch: list[Professor] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # Unexpected exception from gather - apply inclusive fallback
            logger.error(
                "Unexpected exception in batch processing",
                professor=batch[i].name,
                error=str(result),
            )
            batch[i].is_relevant = True
            batch[i].relevance_confidence = 0
            batch[i].relevance_reasoning = f"Unexpected error: {str(result)[:100]}"
            batch[i].add_quality_flag("llm_filtering_failed")
            filtered_batch.append(batch[i])
        elif isinstance(result, Professor):
            # Normal case: result is a Professor
            filtered_batch.append(result)

    return filtered_batch


async def filter_professors(correlation_id: str) -> list[Professor]:
    """Main orchestration function for professor filtering workflow.

    Story 3.2: Task 4 - Batch Orchestration

    Complete filtering workflow:
    1. Load user profile from output/user_profile.md
    2. Load system params for batch size and confidence threshold
    3. Load professors from Story 3.1b checkpoints (phase-2-professors-batch-*.jsonl)
    4. Filter each professor using LLM
    5. Save ALL professors (relevant + filtered) to new checkpoints
    6. Update progress tracking
    7. Return complete list

    Resumability: Uses checkpoint_manager.get_resume_point() to resume from last completed batch.

    Args:
        correlation_id: Correlation ID for logging

    Returns:
        List of ALL professors with is_relevant field updated
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_filtering",
        component="professor_filtering",
    )
    logger.info("Starting professor filtering workflow")

    # Task 1: Load user profile
    logger.info("Step 1: Loading user profile")
    profile_dict = load_user_profile()

    # Load system parameters
    logger.info("Step 2: Loading system parameters")
    system_params = SystemParams.load()
    batch_size = system_params.batch_config.professor_filtering_batch_size

    # Log loaded batch configuration (Story 3.5 Task 1)
    logger.info(
        "Loaded batch configuration",
        professor_filtering_batch_size=batch_size,
        max_concurrent_llm_calls=system_params.rate_limiting.max_concurrent_llm_calls,
    )

    # Load checkpoint manager
    checkpoint_manager = CheckpointManager()

    # Load all professors from Story 3.1b checkpoints
    logger.info("Step 3: Loading professors from checkpoints")
    professor_batches = checkpoint_manager.load_batches("phase-2-professors")

    # Flatten batches into single list
    all_professors: list[Professor] = []
    for batch_data in professor_batches:
        # Convert dict to Professor model
        if isinstance(batch_data, dict):
            all_professors.append(Professor(**batch_data))
        else:
            all_professors.append(batch_data)

    logger.info("Professors loaded", total_count=len(all_professors))

    # Initialize progress tracker (Task 5)
    tracker = ProgressTracker()
    tracker.start_phase("Phase 2: Professor Filtering", total_items=len(all_professors))

    # Process professors in batches
    processed_count = 0
    included_count = 0
    excluded_count = 0
    failed_count = 0

    # Determine resume point
    resume_batch = checkpoint_manager.get_resume_point("phase-2-filter")
    total_batches = (len(all_professors) + batch_size - 1) // batch_size

    logger.info(
        "Starting batch processing",
        total_batches=total_batches,
        batch_size=batch_size,
        resume_from_batch=resume_batch,
    )

    # Get max concurrent LLM calls from config (Story 3.5 Task 7)
    max_concurrent = system_params.rate_limiting.max_concurrent_llm_calls

    for batch_num in range(resume_batch, total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(all_professors))
        batch_professors = all_professors[start_idx:end_idx]

        logger.info(
            f"Processing batch {batch_num + 1}/{total_batches} with {len(batch_professors)} parallel LLM calls (max {max_concurrent} concurrent)",
            batch_size=len(batch_professors),
        )

        # Update batch progress (Story 3.5 Task 6)
        tracker.update_batch(
            batch_num=batch_num + 1,
            total_batches=total_batches,
            batch_desc=f"Professors {start_idx + 1}-{end_idx}",
        )

        # Story 3.5 Task 7: Filter batch in parallel with semaphore
        try:
            filtered_batch = await filter_professor_batch_parallel(
                batch=batch_professors,
                profile_dict=profile_dict,
                correlation_id=f"{correlation_id}-batch-{batch_num + 1}",
                max_concurrent=max_concurrent,
            )

            # Count results
            for professor in filtered_batch:
                if professor.is_relevant:
                    included_count += 1
                else:
                    excluded_count += 1

                # Count failures
                if "llm_filtering_failed" in professor.data_quality_flags:
                    failed_count += 1

            processed_count += len(filtered_batch)
            tracker.update(completed=processed_count)

            # Story 3.5 Task 5: Save batch checkpoint
            logger.info(
                f"Saving batch {batch_num + 1} checkpoint",
                batch_size=len(filtered_batch),
                included=sum(1 for p in filtered_batch if p.is_relevant),
                excluded=sum(1 for p in filtered_batch if not p.is_relevant),
            )
            checkpoint_manager.save_batch(
                phase="phase-2-filter",
                batch_id=batch_num + 1,
                data=filtered_batch,
            )

        except Exception as e:
            # Story 3.5 Task 8: Batch infrastructure failure handling
            logger.error(
                f"Batch {batch_num + 1} processing infrastructure failed",
                error=str(e),
                correlation_id=correlation_id,
            )
            # Re-raise to prevent data consistency issues
            raise

    # Complete progress tracking
    tracker.complete_phase()

    # Story 3.3 Task 9: Apply manual overrides (after LLM filtering)
    override_count = apply_manual_overrides(all_professors)

    # Recalculate included/excluded counts after overrides
    if override_count > 0:
        included_count = sum(1 for p in all_professors if p.is_relevant)
        excluded_count = len(all_professors) - included_count

    # Calculate match rate
    match_rate = (included_count / len(all_professors) * 100) if all_professors else 0

    # Story 3.3 Task 7: Calculate confidence statistics
    confidence_stats = calculate_confidence_stats(all_professors)

    # Story 3.3 Task 8: Save confidence stats to JSON
    save_confidence_stats_report(confidence_stats)

    # Display confidence distribution summary
    included_stats = confidence_stats["included"]
    logger.info(
        "Filtering complete with confidence breakdown",
        total_professors=len(all_professors),
        included=included_count,
        excluded=excluded_count,
        failed=failed_count,
        match_rate=f"{match_rate:.1f}%",
        high_conf=included_stats["high"],
        med_conf=included_stats["medium"],
        low_conf=included_stats["low"],
        quality=confidence_stats["distribution_analysis"]["quality_assessment"],
    )

    return all_professors
