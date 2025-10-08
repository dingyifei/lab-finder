"""Professor data model with research profile and lab affiliation tracking."""

from typing import Optional
from pydantic import BaseModel, Field


# Data quality flag constants
PROFESSOR_DATA_QUALITY_FLAGS = {
    "scraped_with_playwright_fallback",  # WebFetch failed, used Playwright
    "missing_email",  # No email address found
    "missing_research_areas",  # No research areas found in directory
    "missing_lab_affiliation",  # Lab name/URL not identified
    "ambiguous_lab",  # Multiple possible lab affiliations unclear
    "llm_filtering_failed",  # LLM call failed, used inclusive default (confidence=0)
    "low_confidence_filter",  # Confidence below threshold (for Story 3.3 use)
}


class Professor(BaseModel):
    """Represents a university professor with research profile and affiliations.

    Attributes:
        id: Unique identifier (SHA256 hash of name:department_id, first 16 chars)
        name: Full name
        title: Academic title (Professor, Associate Professor, etc.)
        department_id: Foreign key to Department.id
        department_name: Department name for display
        school: Parent school/college (optional)
        lab_name: Lab affiliation if available (optional)
        lab_url: Lab website URL (optional)
        research_areas: Research area descriptions/keywords
        profile_url: Faculty profile URL
        email: Contact email address (optional)
        data_quality_flags: List of data quality issues from PROFESSOR_DATA_QUALITY_FLAGS
        is_relevant: Filter decision from Story 3.2
        relevance_confidence: Confidence score 0-100 from LLM filtering
        relevance_reasoning: LLM explanation for filter decision
    """

    id: str
    name: str
    title: str
    department_id: str
    department_name: str
    school: Optional[str] = None
    lab_name: Optional[str] = None
    lab_url: Optional[str] = None
    research_areas: list[str] = Field(default_factory=list)
    profile_url: str
    email: Optional[str] = None
    data_quality_flags: list[str] = Field(default_factory=list)

    # NEW fields for Story 3.2 (LLM-based filtering)
    is_relevant: bool = False
    relevance_confidence: int = 0
    relevance_reasoning: str = ""

    def add_quality_flag(self, flag: str) -> None:
        """Add a data quality flag if it's valid and not already present.

        Args:
            flag: Flag from PROFESSOR_DATA_QUALITY_FLAGS constant set

        Raises:
            ValueError: If flag is not in PROFESSOR_DATA_QUALITY_FLAGS
        """
        if flag not in PROFESSOR_DATA_QUALITY_FLAGS:
            raise ValueError(
                f"Invalid data quality flag: {flag}. "
                f"Must be one of {PROFESSOR_DATA_QUALITY_FLAGS}"
            )

        if flag not in self.data_quality_flags:
            self.data_quality_flags.append(flag)

    def has_quality_issues(self) -> bool:
        """Check if professor record has any data quality issues.

        Returns:
            True if data_quality_flags is non-empty
        """
        return len(self.data_quality_flags) > 0
