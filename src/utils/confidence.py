"""Confidence Score Validation and Management.

Story 3.3: Confidence-based quality assessment for professor filtering.

Provides functions for:
- Validating and normalizing LLM confidence scores
- Generating borderline case reports for manual review
- Calculating confidence distribution statistics
- Applying manual overrides with audit trails
"""

import json
from pathlib import Path
from typing import Any

from src.models.config import SystemParams
from src.models.professor import Professor
from src.utils.logger import get_logger


def validate_confidence_score(
    raw_confidence: Any, professor_name: str, correlation_id: str
) -> tuple[int, list[str]]:
    """Validate and normalize confidence score from LLM response.

    Story 3.3: Task 4 - Parse and Validate Confidence Scores

    Handles multiple types (int, float, string) and validates range (0-100).
    Applies clamping for out-of-range values and neutral default for invalid values.

    Args:
        raw_confidence: Confidence value from LLM (any type)
        professor_name: Professor name for logging
        correlation_id: Correlation ID for logging

    Returns:
        Tuple of (validated_confidence: int, flags: list[str])
        - validated_confidence: Integer in range 0-100
        - flags: List of data quality flags to add
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_filtering",
        component="confidence",
    )

    flags: list[str] = []

    # Type conversion: handle int, float, string
    try:
        if isinstance(raw_confidence, bool):
            # bool is subclass of int, handle explicitly
            raise ValueError("Boolean type not valid for confidence")

        if isinstance(raw_confidence, (int, float)):
            confidence = int(round(float(raw_confidence)))
        elif isinstance(raw_confidence, str):
            # Attempt string to float to int conversion
            confidence = int(round(float(raw_confidence)))
        else:
            raise ValueError(f"Unsupported type: {type(raw_confidence)}")

    except (ValueError, TypeError) as e:
        # Non-numeric or invalid type - set to neutral 50
        logger.warning(
            "Invalid confidence type, using neutral default",
            professor=professor_name,
            raw_value=str(raw_confidence)[:50],
            error=str(e),
        )
        flags.append("llm_response_error")
        return 50, flags

    # Range validation and clamping
    if confidence < 0:
        logger.error(
            "Negative confidence returned, clamping to 0",
            confidence=confidence,
            professor=professor_name,
        )
        flags.append("confidence_out_of_range")
        return 0, flags

    if confidence > 100:
        logger.error(
            "Confidence exceeds 100, clamping to 100",
            confidence=confidence,
            professor=professor_name,
        )
        flags.append("confidence_out_of_range")
        return 100, flags

    # Valid confidence in range 0-100
    return confidence, flags


def generate_borderline_report(professors: list[Professor]) -> None:
    """Generate borderline professor review report.

    Story 3.3: Task 6 - Generate Borderline Cases Review Report

    Creates output/borderline-professors.md with:
    - Summary statistics
    - Professors with low confidence scores
    - Grouped by decision (included vs. excluded)
    - Actionable recommendations

    Args:
        professors: List of all professors with filtering results
    """
    logger = get_logger(
        correlation_id="borderline-report",
        phase="professor_filtering",
        component="confidence",
    )

    # Load configuration
    system_params = SystemParams.load()
    low_threshold = system_params.filtering_config.low_confidence_threshold

    # Filter borderline cases (confidence < threshold)
    borderline_professors = [
        p for p in professors if p.relevance_confidence < low_threshold
    ]

    if not borderline_professors:
        logger.info("No borderline cases found, skipping report generation")
        return

    # Split by decision
    included_borderline = [p for p in borderline_professors if p.is_relevant]
    excluded_borderline = [p for p in borderline_professors if not p.is_relevant]

    # Calculate statistics
    total_borderline = len(borderline_professors)
    borderline_percentage = (
        (total_borderline / len(professors) * 100) if professors else 0
    )

    # Create output directory if needed
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Generate report
    report_path = output_dir / "borderline-professors.md"

    with open(report_path, "w", encoding="utf-8") as f:
        # Header
        f.write("# Borderline Professor Filtering Cases\n\n")
        f.write(f"**Low Confidence Threshold:** {low_threshold}\n")
        f.write(
            f"**Total Borderline Cases:** {total_borderline} ({borderline_percentage:.1f}% of total professors)\n"
        )
        f.write(
            f"**Breakdown:** {len(included_borderline)} included (low confidence), {len(excluded_borderline)} excluded (low confidence)\n\n"
        )
        f.write("---\n\n")

        # Included professors section
        f.write(
            f"## Included Professors (Low Confidence) - {len(included_borderline)} cases\n\n"
        )
        f.write(
            "These professors were **included** despite low confidence. Consider if they should be excluded.\n\n"
        )

        if included_borderline:
            f.write(
                "| Professor | Department | Research Areas | Confidence | Reasoning | Profile Link | Recommend Override? |\n"
            )
            f.write(
                "|-----------|------------|----------------|------------|-----------|--------------|---------------------|\n"
            )

            for prof in included_borderline:
                research_areas = ", ".join(
                    prof.research_areas[:3]
                )  # Limit to 3 for readability
                if len(prof.research_areas) > 3:
                    research_areas += "..."

                reasoning_short = (
                    prof.relevance_reasoning[:80] + "..."
                    if len(prof.relevance_reasoning) > 80
                    else prof.relevance_reasoning
                )

                # Recommend override logic based on reasoning keywords
                recommend = _get_override_recommendation(
                    prof.relevance_reasoning, prof.is_relevant
                )

                f.write(
                    f"| [{prof.name}]({prof.profile_url}) | {prof.department_name} | {research_areas} | {prof.relevance_confidence} | {reasoning_short} | [View Profile]({prof.profile_url}) | {recommend} |\n"
                )
        else:
            f.write("*No included professors with low confidence.*\n")

        f.write(
            "\n## Excluded Professors (Low Confidence) - "
            + str(len(excluded_borderline))
            + " cases\n\n"
        )
        f.write(
            "These professors were **excluded** due to low confidence. Consider if they should be included.\n\n"
        )

        if excluded_borderline:
            f.write(
                "| Professor | Department | Research Areas | Confidence | Reasoning | Profile Link | Recommend Override? |\n"
            )
            f.write(
                "|-----------|------------|----------------|------------|-----------|--------------|---------------------|\n"
            )

            for prof in excluded_borderline:
                research_areas = ", ".join(prof.research_areas[:3])
                if len(prof.research_areas) > 3:
                    research_areas += "..."

                reasoning_short = (
                    prof.relevance_reasoning[:80] + "..."
                    if len(prof.relevance_reasoning) > 80
                    else prof.relevance_reasoning
                )

                recommend = _get_override_recommendation(
                    prof.relevance_reasoning, prof.is_relevant
                )

                f.write(
                    f"| [{prof.name}]({prof.profile_url}) | {prof.department_name} | {research_areas} | {prof.relevance_confidence} | {reasoning_short} | [View Profile]({prof.profile_url}) | {recommend} |\n"
                )
        else:
            f.write("*No excluded professors with low confidence.*\n")

        # Action instructions
        f.write("\n---\n\n")
        f.write(
            "**Action Required:** Review these borderline cases manually. To override decisions, add entries to `config/manual-overrides.json`:\n\n"
        )
        f.write("```json\n")
        f.write("{\n")
        f.write('  "professor_overrides": [\n')
        f.write("    {\n")
        f.write('      "professor_id": "prof-id-here",\n')
        f.write('      "decision": "include",\n')
        f.write('      "reason": "Your reasoning here",\n')
        f.write('      "timestamp": "2025-10-08T14:30:00Z",\n')
        f.write('      "original_confidence": 65,\n')
        f.write('      "original_decision": "exclude"\n')
        f.write("    }\n")
        f.write("  ]\n")
        f.write("}\n")
        f.write("```\n")

    logger.info(
        "Borderline report generated",
        report_path=str(report_path),
        total_borderline=total_borderline,
        included_borderline=len(included_borderline),
        excluded_borderline=len(excluded_borderline),
    )


def _get_override_recommendation(reasoning: str, is_relevant: bool) -> str:
    """Determine override recommendation based on reasoning keywords.

    Args:
        reasoning: LLM reasoning text
        is_relevant: Current decision

    Returns:
        Recommendation string for override column
    """
    reasoning_lower = reasoning.lower()

    # Keywords suggesting reconsideration
    interdisciplinary_keywords = ["interdisciplinary", "cross-field"]
    emerging_keywords = ["emerging", "new field", "cutting-edge", "innovative", "novel"]
    tangential_keywords = ["tangential", "weak", "minimal", "indirect"]

    if any(kw in reasoning_lower for kw in interdisciplinary_keywords):
        return "Review - interdisciplinary"
    elif any(kw in reasoning_lower for kw in emerging_keywords):
        return "Consider - emerging field"
    elif any(kw in reasoning_lower for kw in tangential_keywords):
        if is_relevant:
            return "Review - tangential match"
        else:
            return "Likely correct"
    else:
        return "Review manually"


def calculate_confidence_stats(professors: list[Professor]) -> dict[str, Any]:
    """Calculate confidence distribution statistics for filtering results.

    Story 3.3: Task 7 - Implement Confidence-Based Statistics

    Categorizes professors by confidence level:
    - High confidence (>=90): Strong match certainty
    - Medium confidence (70-89): Moderate match certainty
    - Low confidence (<70): Requires review

    Calculates for both included and excluded professors, and provides
    quality validation warnings if distribution is outside expected ranges.

    Args:
        professors: List of professors with filtering results

    Returns:
        Dict with confidence distribution statistics and quality assessment
    """
    logger = get_logger(
        correlation_id="confidence-stats",
        phase="professor_filtering",
        component="confidence",
    )

    # Load thresholds
    system_params = SystemParams.load()
    low_threshold = system_params.filtering_config.low_confidence_threshold
    high_threshold = system_params.filtering_config.high_confidence_threshold

    # Split by decision
    included = [p for p in professors if p.is_relevant]
    excluded = [p for p in professors if not p.is_relevant]

    # Calculate distributions
    def categorize(profs: list[Professor]) -> dict[str, int]:
        high = sum(1 for p in profs if p.relevance_confidence >= high_threshold)
        medium = sum(
            1 for p in profs if low_threshold <= p.relevance_confidence < high_threshold
        )
        low = sum(1 for p in profs if p.relevance_confidence < low_threshold)
        return {"high": high, "medium": medium, "low": low, "total": len(profs)}

    included_dist = categorize(included)
    excluded_dist = categorize(excluded)

    # Overall low-confidence percentage
    total_low = included_dist["low"] + excluded_dist["low"]
    low_percentage = (total_low / len(professors) * 100) if professors else 0

    # Quality validation (expected: 10-20% low-confidence)
    deviation_msg = ""
    quality_assessment = ""

    if low_percentage > 30:
        logger.warning(
            "High proportion of low-confidence decisions detected",
            low_confidence_percentage=f"{low_percentage:.1f}%",
            expected_range="10-20%",
            message="Consider reviewing prompt or research profile specificity",
        )
        deviation_msg = f"High ({low_percentage:.1f}% vs expected 10-20%)"
        quality_assessment = "Warning - High low-confidence rate suggests prompt issues"
    elif low_percentage < 10:
        deviation_msg = f"Low ({low_percentage:.1f}% vs expected 10-20%)"
        quality_assessment = "Good - Low ambiguity in filtering decisions"
    else:
        deviation_msg = "Within expected range"
        quality_assessment = "Good - Distribution matches expectations"

    stats = {
        "total_professors": len(professors),
        "included": included_dist,
        "excluded": excluded_dist,
        "distribution_analysis": {
            "low_confidence_percentage": round(low_percentage, 1),
            "expected_range": "10-20%",
            "deviation_from_expected": deviation_msg,
            "quality_assessment": quality_assessment,
        },
    }

    logger.info(
        "Confidence distribution calculated",
        total=len(professors),
        included_high=included_dist["high"],
        included_medium=included_dist["medium"],
        included_low=included_dist["low"],
        excluded_high=excluded_dist["high"],
        excluded_medium=excluded_dist["medium"],
        excluded_low=excluded_dist["low"],
        low_percentage=f"{low_percentage:.1f}%",
        quality=quality_assessment,
    )

    return stats


def save_confidence_stats_report(stats: dict[str, Any]) -> None:
    """Save confidence statistics to JSON file for visualization.

    Story 3.3: Task 8 - Add Confidence Visualization to Reports

    Creates output/filter-confidence-stats.json with:
    - Total professor counts
    - Confidence distribution for included/excluded
    - Distribution quality analysis

    Args:
        stats: Confidence statistics dict from calculate_confidence_stats()
    """
    logger = get_logger(
        correlation_id="confidence-stats-report",
        phase="professor_filtering",
        component="confidence",
    )

    # Create output directory if needed
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Save to JSON
    stats_path = output_dir / "filter-confidence-stats.json"

    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    logger.info(
        "Confidence statistics report saved",
        report_path=str(stats_path),
        total_professors=stats["total_professors"],
        quality_assessment=stats["distribution_analysis"]["quality_assessment"],
    )


def apply_manual_overrides(professors: list[Professor]) -> int:
    """Apply manual overrides from config/manual-overrides.json.

    Story 3.3: Task 9 - Enable Manual Override of Low-Confidence Cases

    Loads manual override decisions and applies them to professor records.
    Adds audit trail to professor records for transparency.

    Args:
        professors: List of professors to apply overrides to

    Returns:
        Number of overrides applied
    """
    logger = get_logger(
        correlation_id="manual-overrides",
        phase="professor_filtering",
        component="confidence",
    )

    # Check if override file exists
    overrides_path = Path("config/manual-overrides.json")
    if not overrides_path.exists():
        logger.debug("No manual overrides file found, skipping")
        return 0

    # Load overrides
    try:
        with open(overrides_path, "r", encoding="utf-8") as f:
            overrides_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse manual overrides file", error=str(e))
        return 0

    # Get professor overrides list
    professor_overrides = overrides_data.get("professor_overrides", [])

    if not professor_overrides:
        logger.debug("No professor overrides found in file")
        return 0

    # Create professor ID lookup
    professors_by_id = {p.id: p for p in professors}

    # Apply overrides
    override_count = 0
    for override in professor_overrides:
        prof_id = override.get("professor_id")
        new_decision = override.get("decision")
        reason = override.get("reason", "Manual override")
        timestamp = override.get("timestamp", "")
        original_confidence = override.get("original_confidence")
        original_decision = override.get("original_decision")

        # Validate override fields
        if not prof_id or not new_decision:
            logger.warning(
                "Invalid override entry, skipping",
                professor_id=prof_id,
                decision=new_decision,
            )
            continue

        # Find professor
        professor = professors_by_id.get(prof_id)
        if not professor:
            logger.warning(
                "Professor ID not found in filtered list, skipping override",
                professor_id=prof_id,
            )
            continue

        # Apply override
        old_decision = "include" if professor.is_relevant else "exclude"
        professor.is_relevant = new_decision == "include"

        # Add manual override flag
        professor.add_quality_flag("manual_override")

        # Update reasoning with audit trail
        professor.relevance_reasoning = (
            f"MANUAL OVERRIDE ({timestamp}): {reason} | "
            f"Original: {original_decision} (confidence: {original_confidence}) | "
            f"LLM reasoning: {professor.relevance_reasoning}"
        )

        logger.info(
            "Applied manual override",
            professor_id=prof_id,
            professor_name=professor.name,
            old_decision=old_decision,
            new_decision=new_decision,
            reason=reason[:100],
        )

        override_count += 1

    logger.info(
        "Manual overrides applied",
        total_overrides=override_count,
        total_professors=len(professors),
    )

    return override_count
