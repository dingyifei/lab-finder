"""
Profile Consolidator Agent
Combines user profile and university config into consolidated research profile document.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

from src.models.profile import ConsolidatedProfile
from src.utils.logger import get_logger
from src.utils.llm_helpers import call_llm_with_retry

logger = get_logger(
    correlation_id="profile-consolidation",
    phase="phase-0",
    component="profile_consolidator",
)


class ProfileConsolidator:
    """Consolidates user profile into research baseline document."""

    def __init__(self, output_dir: Path = Path("output")):
        """
        Initialize profile consolidator.

        Args:
            output_dir: Directory to save consolidated profile
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def consolidate(
        self, user_profile: Dict[str, Any], university_config: Dict[str, Any]
    ) -> ConsolidatedProfile:
        """
        Consolidate user profile and university config into baseline document.

        Args:
            user_profile: Validated user profile configuration
            university_config: Validated university configuration

        Returns:
            ConsolidatedProfile with all extracted and processed information
        """
        logger.info("Starting profile consolidation")  # type: ignore[attr-defined]

        # Extract basic information
        profile = ConsolidatedProfile(
            name=user_profile["name"],
            current_degree=user_profile["current_degree"],
            target_university=user_profile["target_university"],
            target_department=user_profile["target_department"],
            research_interests=user_profile["research_interests"],
            streamlined_interests=await self._streamline_interests(
                user_profile["research_interests"]
            ),
            education_background=self._extract_education(
                user_profile.get("resume_highlights", {})
            ),
            skills_summary=self._extract_skills(
                user_profile.get("resume_highlights", {})
            ),
            research_experience_summary=self._extract_research_experience(
                user_profile.get("resume_highlights", {})
            ),
            key_qualifications=self._extract_qualifications(user_profile),
            preferred_graduation_duration=user_profile.get(
                "preferred_graduation_duration", 5.5
            ),
            university_website=university_config["core_website"],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(  # type: ignore[attr-defined]
            "Profile consolidation complete",
            research_areas_count=len(profile.research_interests),
            qualifications_count=len(profile.key_qualifications),
        )

        return profile

    async def _streamline_interests(self, interests: List[str]) -> str:
        """
        Use LLM to streamline and clarify research interests.

        Args:
            interests: List of research interest statements

        Returns:
            Concise, coherent research interest summary
        """
        logger.debug("Streamlining research interests with LLM")  # type: ignore[attr-defined]

        interests_list = "\n".join(f"- {interest}" for interest in interests)

        prompt = f"""You are analyzing research interests to create a concise profile summary.

<research_interests>
{interests_list}
</research_interests>

<task>
Generate a JSON response with:
1. A 2-3 sentence summary identifying the main research domain and key focus areas
2. A list of 5-7 keyword phrases for research matching
</task>

<output_format>
Return ONLY valid JSON in this exact format (no markdown code blocks, no additional text):
{{"summary": "your summary text", "keywords": ["keyword1", "keyword2", "keyword3"]}}
</output_format>

<example>
Input:
- Developing novel machine learning algorithms for healthcare applications
- Natural language processing for clinical documentation
- Computer vision for medical imaging diagnosis

Output:
{{"summary": "The researcher focuses on applying artificial intelligence to healthcare, with expertise in machine learning algorithms, natural language processing for clinical text, and computer vision for medical imaging. Their work bridges AI and medicine to improve diagnostic and documentation systems.", "keywords": ["machine learning", "healthcare AI", "natural language processing", "computer vision", "medical imaging", "clinical applications", "diagnostic systems"]}}
</example>

Provide your JSON response:"""

        streamlined = await call_llm_with_retry(
            prompt, correlation_id="profile-consolidation"
        )

        # Parse JSON response
        import json
        try:
            # Extract JSON from response (may be in markdown code blocks)
            json_text = streamlined.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            elif json_text.startswith("```"):
                json_text = json_text[3:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()

            result = json.loads(json_text)
            summary = result.get("summary", streamlined.strip())
            keywords = result.get("keywords", [])

            logger.debug(  # type: ignore[attr-defined]
                "Research interests streamlined",
                summary_length=len(summary),
                keywords_count=len(keywords),
                keywords=keywords[:5] if keywords else []  # Log first 5 keywords
            )
            return summary

        except json.JSONDecodeError:
            # Fallback: use raw response if JSON parsing fails
            logger.warning("Failed to parse JSON from LLM, using raw response")  # type: ignore[attr-defined]
            return streamlined.strip()

    def _extract_education(self, resume_highlights: Dict[str, Any]) -> str:
        """
        Extract education background summary.

        Args:
            resume_highlights: Resume highlights section

        Returns:
            Education background summary string
        """
        education = resume_highlights.get("education", [])
        if not education:
            return "Education details not provided"

        # Format education entries
        entries = []
        for edu in education:
            degree = edu.get("degree", "Unknown Degree")
            institution = edu.get("institution", "Unknown Institution")
            year = edu.get("year", "")
            year_str = f" ({year})" if year else ""
            entries.append(f"{degree}, {institution}{year_str}")

        return "; ".join(entries)

    def _extract_skills(self, resume_highlights: Dict[str, Any]) -> str:
        """
        Extract skills summary.

        Args:
            resume_highlights: Resume highlights section

        Returns:
            Skills summary string
        """
        skills = resume_highlights.get("skills", [])
        if not skills:
            return "Skills not provided"

        return ", ".join(skills)

    def _extract_research_experience(self, resume_highlights: Dict[str, Any]) -> str:
        """
        Extract research experience summary.

        Args:
            resume_highlights: Resume highlights section

        Returns:
            Research experience summary string
        """
        experience = resume_highlights.get("research_experience", [])
        if not experience:
            return "Research experience not provided"

        # Format experience entries
        entries = []
        for exp in experience:
            title = exp.get("title", "Research Position")
            description = exp.get("description", "")
            duration = exp.get("duration", "")
            duration_str = f" ({duration})" if duration else ""
            entries.append(f"{title}{duration_str}: {description}")

        return "; ".join(entries)

    def _extract_qualifications(self, user_profile: Dict[str, Any]) -> List[str]:
        """
        Extract key qualifications from profile.

        Args:
            user_profile: User profile configuration

        Returns:
            List of key qualification statements
        """
        qualifications = []

        # Current degree
        qualifications.append(f"Currently pursuing {user_profile['current_degree']}")

        # Research interests count
        interests_count = len(user_profile["research_interests"])
        qualifications.append(f"{interests_count} primary research interest area(s)")

        # Skills count (if available)
        resume = user_profile.get("resume_highlights", {})
        skills = resume.get("skills", [])
        if skills:
            qualifications.append(f"{len(skills)} technical skills")

        # Research experience (if available)
        experience = resume.get("research_experience", [])
        if experience:
            qualifications.append(f"{len(experience)} research experience(s)")

        return qualifications

    def save_markdown(self, profile: ConsolidatedProfile) -> Path:
        """
        Save consolidated profile as markdown document.

        Args:
            profile: Consolidated profile to save

        Returns:
            Path to saved markdown file
        """
        output_path = self.output_dir / "user_profile.md"

        interests_list = "\n".join(
            f"- {interest}" for interest in profile.research_interests
        )
        qualifications_list = "\n".join(
            f"- {qual}" for qual in profile.key_qualifications
        )

        markdown_content = f"""# Research Profile: {profile.name}

**Generated:** {profile.generated_at}

---

## Overview

**Current Position:** {profile.current_degree}

**Target University:** {profile.target_university}

**Target Department:** {profile.target_department}

**University Website:** {profile.university_website}

---

## Research Interests

{interests_list}

### Streamlined Research Focus

{profile.streamlined_interests}

---

## Academic Background

### Education

{profile.education_background}

### Skills

{profile.skills_summary}

### Research Experience

{profile.research_experience_summary}

---

## Key Qualifications

{qualifications_list}

---

## Configuration

**Preferred PhD Graduation Duration:** {profile.preferred_graduation_duration} years

This value is used to estimate graduating PhD students when analyzing labs.

---

## Usage

This consolidated profile serves as the baseline for:

- **Department Filtering** (Epic 2): Identifies relevant departments at {profile.target_university}
- **Professor Filtering** (Epic 3): Matches professors based on research field alignment
- **Fitness Scoring** (Epic 7): Calculates lab-to-profile fit scores
- **Report Generation** (Epic 8): Personalizes lab recommendations

All filtering and matching decisions reference this profile to ensure consistency across the analysis pipeline.

---

*This document was automatically generated by the Lab Finder Profile Consolidator.*
"""

        output_path.write_text(markdown_content, encoding="utf-8")

        logger.info(  # type: ignore[attr-defined]
            "Consolidated profile saved", output_path=str(output_path)
        )

        return output_path

    def save_checkpoint(self, profile: ConsolidatedProfile) -> None:
        """Save profile to checkpoint for resumability."""
        checkpoint_path = Path("checkpoints/phase-0-validation.json")
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        checkpoint_data = profile.model_dump()
        checkpoint_path.write_text(
            json.dumps(checkpoint_data, indent=2), encoding="utf-8"
        )

        logger.info("Profile checkpoint saved", checkpoint=str(checkpoint_path))  # type: ignore[attr-defined]
