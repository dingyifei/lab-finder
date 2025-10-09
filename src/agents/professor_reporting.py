"""Professor Reporting Agent.

Story 3.4: Filtered professor logging and transparency reporting.

Provides functions for:
- Logging filter decisions with structured logging
- Calculating filtering statistics
- Generating comprehensive filter reports
- Loading and applying manual professor additions
"""

import json
from pathlib import Path
from typing import Any

from src.models.professor import Professor
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.logger import get_logger


def log_filter_decision(professor: Professor, correlation_id: str) -> None:
    """Log single filter decision to structured logger.

    Story 3.4: Task 1 - Log All Filter Decisions

    Logs professor filtering decision with all relevant context for transparency.
    Uses professor.is_relevant, relevance_confidence, relevance_reasoning fields.

    Args:
        professor: Professor model with filter decision fields populated
        correlation_id: Correlation ID for logging
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_filtering",
        component="professor_reporting",
    )

    # Determine decision string
    decision = "exclude" if not professor.is_relevant else "include"

    logger.info(
        "Filter decision logged",
        component="professor_reporting",
        professor_id=professor.id,
        professor_name=professor.name,
        department=professor.department_name,
        school=professor.school or "N/A",
        research_areas=professor.research_areas,
        decision=decision,
        is_relevant=professor.is_relevant,
        relevance_confidence=professor.relevance_confidence,
        relevance_reasoning=professor.relevance_reasoning,
    )


def calculate_filter_statistics(professors: list[Professor]) -> dict[str, Any]:
    """Calculate filtering statistics with edge case handling.

    Story 3.4: Task 4 - Add Filtering Statistics

    Handles edge cases:
    - Empty professor list (total=0)
    - All professors included
    - All professors excluded

    Args:
        professors: List of Professor models with filter decisions

    Returns:
        Dict with total, included, and excluded statistics
    """
    total = len(professors)

    # Edge case: no professors
    if total == 0:
        return {
            "total": 0,
            "included": {
                "count": 0,
                "percentage": 0.0,
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
            },
            "excluded": {
                "count": 0,
                "percentage": 0.0,
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
            },
        }

    included = [p for p in professors if p.is_relevant]
    excluded = [p for p in professors if not p.is_relevant]

    return {
        "total": total,
        "included": {
            "count": len(included),
            "percentage": len(included) / total * 100,
            "high_confidence": len(
                [p for p in included if p.relevance_confidence >= 90]
            ),
            "medium_confidence": len(
                [p for p in included if 70 <= p.relevance_confidence < 90]
            ),
            "low_confidence": len([p for p in included if p.relevance_confidence < 70]),
        },
        "excluded": {
            "count": len(excluded),
            "percentage": len(excluded) / total * 100,
            "high_confidence": len(
                [p for p in excluded if p.relevance_confidence >= 90]
            ),
            "medium_confidence": len(
                [p for p in excluded if 70 <= p.relevance_confidence < 90]
            ),
            "low_confidence": len([p for p in excluded if p.relevance_confidence < 70]),
        },
    }


async def generate_filter_report(
    professors: list[Professor], output_dir: str, correlation_id: str
) -> None:
    """Generate filtered-professors.md report from filtered professor list.

    Story 3.4: Tasks 2, 3, 4, 6, 7 - Complete Transparency Report

    Creates comprehensive markdown report with:
    - Executive summary with statistics
    - Department-level statistics
    - Excluded professors (high/medium/low confidence)
    - Included professors summary
    - Cross-reference to borderline-professors.md
    - Manual override instructions

    Args:
        professors: List of Professor models with filter decisions
        output_dir: Output directory path
        correlation_id: Correlation ID for logging
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_filtering",
        component="professor_reporting",
    )

    logger.info("Generating filtered professors report", total_professors=len(professors))

    # Calculate statistics
    stats = calculate_filter_statistics(professors)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Log all filter decisions
    for prof in professors:
        log_filter_decision(prof, correlation_id)

    # Calculate department-level stats
    dept_stats: dict[str, dict[str, int]] = {}
    for prof in professors:
        dept_name = prof.department_name
        if dept_name not in dept_stats:
            dept_stats[dept_name] = {"total": 0, "included": 0, "excluded": 0}
        dept_stats[dept_name]["total"] += 1
        if prof.is_relevant:
            dept_stats[dept_name]["included"] += 1
        else:
            dept_stats[dept_name]["excluded"] += 1

    # Sort departments by inclusion rate
    sorted_depts = sorted(
        dept_stats.items(),
        key=lambda x: (
            (x[1]["included"] / x[1]["total"] * 100) if x[1]["total"] > 0 else 0
        ),
        reverse=True,
    )

    # Check for borderline report
    borderline_report_exists = (Path(output_dir) / "borderline-professors.md").exists()

    # Split professors by decision and confidence
    included = [p for p in professors if p.is_relevant]
    excluded = [p for p in professors if not p.is_relevant]

    # Categorize by confidence
    high_conf_excluded = [p for p in excluded if p.relevance_confidence >= 90]
    med_conf_excluded = [
        p for p in excluded if 70 <= p.relevance_confidence < 90
    ]
    low_conf_excluded = [p for p in excluded if p.relevance_confidence < 70]

    high_conf_included = [p for p in included if p.relevance_confidence >= 90]

    # Generate report
    report_path = output_path / "filtered-professors.md"

    with open(report_path, "w", encoding="utf-8") as f:
        # Header
        f.write("# Filtered Professors Report\n\n")

        # Executive Summary
        f.write("## Executive Summary\n\n")
        f.write(f"- **Total Professors Evaluated:** {stats['total']}\n")
        f.write(
            f"- **Included for Analysis:** {stats['included']['count']} "
            f"({stats['included']['percentage']:.1f}%)\n"
        )
        f.write(
            f"- **Excluded:** {stats['excluded']['count']} "
            f"({stats['excluded']['percentage']:.1f}%)\n"
        )

        # Cross-reference to borderline report if exists
        if borderline_report_exists:
            low_conf_total = (
                stats["included"]["low_confidence"]
                + stats["excluded"]["low_confidence"]
            )
            f.write(
                f"- **Low-Confidence Decisions:** {low_conf_total} "
                f"(see [borderline-professors.md](borderline-professors.md))\n"
            )

        f.write("\n---\n\n")

        # Department-level statistics
        f.write("## Filtering Statistics by Department\n\n")

        if sorted_depts:
            f.write(
                "| Department | Total | Included | Excluded | Inclusion Rate |\n"
            )
            f.write("|------------|-------|----------|----------|----------------|\n")

            for dept_name, dept_data in sorted_depts:
                inclusion_rate = (
                    (dept_data["included"] / dept_data["total"] * 100)
                    if dept_data["total"] > 0
                    else 0
                )
                f.write(
                    f"| {dept_name} | {dept_data['total']} | {dept_data['included']} | "
                    f"{dept_data['excluded']} | {inclusion_rate:.0f}% |\n"
                )
        else:
            f.write("*No department data available.*\n")

        f.write("\n---\n\n")

        # Excluded Professors
        f.write("## Excluded Professors\n\n")

        # High Confidence Exclusions
        f.write(f"### High Confidence Exclusions (≥90) - {len(high_conf_excluded)} professors\n\n")

        if high_conf_excluded:
            f.write(
                "| Professor | Department | Research Areas | Confidence | Reason |\n"
            )
            f.write("|-----------|------------|----------------|------------|--------|\n")

            for prof in high_conf_excluded[:50]:  # Limit to 50 for readability
                research_str = ", ".join(prof.research_areas[:3])
                if len(prof.research_areas) > 3:
                    research_str += "..."
                reason_short = (
                    prof.relevance_reasoning[:100] + "..."
                    if len(prof.relevance_reasoning) > 100
                    else prof.relevance_reasoning
                )
                f.write(
                    f"| [{prof.name}]({prof.profile_url}) | {prof.department_name} | "
                    f"{research_str} | {prof.relevance_confidence} | {reason_short} |\n"
                )

            if len(high_conf_excluded) > 50:
                f.write(f"\n*...and {len(high_conf_excluded) - 50} more.*\n")
        else:
            f.write("*No high-confidence exclusions.*\n")

        f.write("\n")

        # Medium Confidence Exclusions
        f.write(f"### Medium Confidence Exclusions (70-89) - {len(med_conf_excluded)} professors\n\n")

        if med_conf_excluded:
            f.write(
                "| Professor | Department | Research Areas | Confidence | Reason |\n"
            )
            f.write("|-----------|------------|----------------|------------|--------|\n")

            for prof in med_conf_excluded[:20]:
                research_str = ", ".join(prof.research_areas[:3])
                if len(prof.research_areas) > 3:
                    research_str += "..."
                reason_short = (
                    prof.relevance_reasoning[:100] + "..."
                    if len(prof.relevance_reasoning) > 100
                    else prof.relevance_reasoning
                )
                f.write(
                    f"| [{prof.name}]({prof.profile_url}) | {prof.department_name} | "
                    f"{research_str} | {prof.relevance_confidence} | {reason_short} |\n"
                )

            if len(med_conf_excluded) > 20:
                f.write(f"\n*...and {len(med_conf_excluded) - 20} more.*\n")
        else:
            f.write("*No medium-confidence exclusions.*\n")

        f.write("\n")

        # Low Confidence Exclusions
        f.write(f"### Low Confidence Exclusions (<70) - {len(low_conf_excluded)} professors\n\n")
        f.write("**⚠️ Review Recommended**")

        if borderline_report_exists:
            f.write(" - See [borderline-professors.md](borderline-professors.md)\n\n")
        else:
            f.write("\n\n")

        if low_conf_excluded:
            f.write(
                "| Professor | Department | Research Areas | Confidence | Reason |\n"
            )
            f.write("|-----------|------------|----------------|------------|--------|\n")

            for prof in low_conf_excluded[:20]:
                research_str = ", ".join(prof.research_areas[:3])
                if len(prof.research_areas) > 3:
                    research_str += "..."
                reason_short = (
                    prof.relevance_reasoning[:100] + "..."
                    if len(prof.relevance_reasoning) > 100
                    else prof.relevance_reasoning
                )
                f.write(
                    f"| [{prof.name}]({prof.profile_url}) | {prof.department_name} | "
                    f"{research_str} | {prof.relevance_confidence} | {reason_short} |\n"
                )

            if len(low_conf_excluded) > 20:
                f.write(f"\n*...and {len(low_conf_excluded) - 20} more.*\n")
        else:
            f.write("*No low-confidence exclusions.*\n")

        f.write("\n---\n\n")

        # Included Professors Summary (Task 3)
        f.write("## Included Professors Summary\n\n")
        f.write(f"### High Confidence Inclusions (≥90) - {len(high_conf_included)} professors\n\n")

        if high_conf_included:
            f.write(
                "| Professor | Department | Research Areas | Confidence | Matching Reason |\n"
            )
            f.write(
                "|-----------|------------|----------------|------------|------------------|\n"
            )

            for prof in high_conf_included[:20]:
                research_str = ", ".join(prof.research_areas[:3])
                if len(prof.research_areas) > 3:
                    research_str += "..."
                reason_short = (
                    prof.relevance_reasoning[:100] + "..."
                    if len(prof.relevance_reasoning) > 100
                    else prof.relevance_reasoning
                )
                f.write(
                    f"| [{prof.name}]({prof.profile_url}) | {prof.department_name} | "
                    f"{research_str} | {prof.relevance_confidence} | {reason_short} |\n"
                )

            if len(high_conf_included) > 20:
                f.write(
                    f"\n*Top 20 shown. Total high-confidence inclusions: {len(high_conf_included)}*\n"
                )
        else:
            f.write("*No high-confidence inclusions.*\n")

        f.write("\n---\n\n")

        # Detailed Exclusion Reasoning section
        f.write("## Detailed Exclusion Reasoning\n\n")

        # Show top 10 excluded with full reasoning
        for i, prof in enumerate(excluded[:10], 1):
            f.write(f"### {i}. {prof.name} (Excluded)\n\n")
            f.write(f"- **Department:** {prof.department_name}\n")
            if prof.school:
                f.write(f"- **School:** {prof.school}\n")
            f.write(f"- **Research Areas:** {', '.join(prof.research_areas) if prof.research_areas else 'Not specified'}\n")
            f.write(f"- **Confidence:** {prof.relevance_confidence}\n")
            f.write(f"- **Reasoning:** {prof.relevance_reasoning}\n")
            f.write(f"- **Profile:** [{prof.profile_url}]({prof.profile_url})\n\n")

        if len(excluded) > 10:
            f.write(f"*...and {len(excluded) - 10} more excluded professors.*\n\n")

        f.write("---\n\n")

        # How to Override Filter Decisions (Task 6)
        f.write("## How to Override Filter Decisions\n\n")
        f.write("If you believe a professor was incorrectly filtered:\n\n")
        f.write("1. Create/edit `config/manual-professor-additions.json`\n")
        f.write("2. Add professor ID to \"additions\" list\n")
        f.write("3. Re-run the pipeline from Phase 3\n\n")
        f.write("The professor will be included in subsequent analysis.\n\n")
        f.write("**Example format:**\n\n")
        f.write("```json\n")
        f.write("{\n")
        f.write('  "additions": [\n')
        f.write("    {\n")
        f.write('      "professor_id": "prof-456",\n')
        f.write('      "reason": "User identified as relevant despite filter"\n')
        f.write("    }\n")
        f.write("  ]\n")
        f.write("}\n")
        f.write("```\n\n")

        # Cross-reference note (Task 7)
        if borderline_report_exists:
            f.write("---\n\n")
            f.write("**Note:** See `borderline-professors.md` for low-confidence\n")
            f.write("decisions that may require manual review.\n")

    logger.info(
        "Filtered professors report generated",
        report_path=str(report_path),
        total_professors=len(professors),
        included=stats["included"]["count"],
        excluded=stats["excluded"]["count"],
    )


async def load_manual_additions(config_path: str = "config/manual-professor-additions.json") -> dict[str, Any]:
    """Load manual professor additions from config file.

    Story 3.4: Task 5 - Enable Manual Professor Addition

    Loads JSON file with manual professor additions. File is optional -
    returns empty dict if not found.

    Args:
        config_path: Path to manual additions JSON file

    Returns:
        Dict with "additions" list or empty dict if file doesn't exist
    """
    logger = get_logger(
        correlation_id="manual-additions",
        phase="professor_filtering",
        component="professor_reporting",
    )

    additions_path = Path(config_path)

    if not additions_path.exists():
        logger.debug("Manual additions file not found, no additions to apply", path=config_path)
        return {"additions": []}

    try:
        with open(additions_path, "r", encoding="utf-8") as f:
            additions_data = json.load(f)

        logger.info(
            "Manual additions loaded",
            path=config_path,
            additions_count=len(additions_data.get("additions", [])),
        )

        return additions_data

    except json.JSONDecodeError as e:
        logger.error("Failed to parse manual additions file", path=config_path, error=str(e))
        return {"additions": []}
    except Exception as e:
        logger.error("Failed to load manual additions", path=config_path, error=str(e))
        return {"additions": []}


async def apply_manual_additions(
    professors: list[Professor], additions: dict[str, Any], correlation_id: str
) -> list[Professor]:
    """Apply manual overrides to professor list.

    Story 3.4: Task 5 - Enable Manual Professor Addition

    Matches professor IDs from additions to filtered professors.
    Sets is_relevant = True and adds "manual_addition" flag.

    EXECUTION TIMING: Must execute BEFORE report generation to include
    overridden professors in reports.

    Args:
        professors: List of Professor models to apply additions to
        additions: Dict from load_manual_additions()
        correlation_id: Correlation ID for logging

    Returns:
        Updated list of Professor models with manual additions applied
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_filtering",
        component="professor_reporting",
    )

    additions_list = additions.get("additions", [])

    if not additions_list:
        logger.debug("No manual additions to apply")
        return professors

    # Create professor ID lookup
    professors_by_id = {p.id: p for p in professors}

    addition_count = 0

    for addition in additions_list:
        prof_id = addition.get("professor_id")
        reason = addition.get("reason", "User manually added despite filter")

        if not prof_id:
            logger.warning("Invalid addition entry, missing professor_id", addition=addition)
            continue

        # Find professor
        professor = professors_by_id.get(prof_id)

        if not professor:
            logger.warning(
                "Professor ID not found in filtered list, cannot apply addition",
                professor_id=prof_id,
            )
            continue

        # Apply manual addition
        old_decision = "include" if professor.is_relevant else "exclude"

        # Override to include
        professor.is_relevant = True

        # Add manual_addition flag
        professor.add_quality_flag("manual_addition")

        # Update reasoning with manual addition note
        professor.relevance_reasoning = (
            f"MANUAL ADDITION: {reason} | "
            f"Original decision: {old_decision} (confidence: {professor.relevance_confidence}) | "
            f"Original reasoning: {professor.relevance_reasoning}"
        )

        logger.info(
            "Applied manual addition",
            professor_id=prof_id,
            professor_name=professor.name,
            old_decision=old_decision,
            new_decision="include",
            reason=reason[:100],
        )

        addition_count += 1

    logger.info(
        "Manual additions applied",
        total_additions=addition_count,
        total_professors=len(professors),
    )

    # Save updated professors to checkpoint
    if addition_count > 0:
        checkpoint_manager = CheckpointManager()
        checkpoint_manager.save_batch(
            phase="phase-2-professors-with-manual-additions",
            batch_id=1,
            data=professors,
        )
        logger.info(
            "Saved professors with manual additions to checkpoint",
            checkpoint_file="checkpoints/phase-2-professors-with-manual-additions-batch-1.jsonl",
        )

    return professors
