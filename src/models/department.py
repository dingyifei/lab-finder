"""Department data model with data quality tracking."""

from typing import Optional
from pydantic import BaseModel, Field
import uuid


# Data quality flag constants
DATA_QUALITY_FLAGS = {
    "missing_url",  # Department URL not found
    "missing_school",  # School name unknown (using placeholder)
    "ambiguous_hierarchy",  # Hierarchy level unclear
    "partial_metadata",  # Some fields missing
    "inference_based",  # Information inferred not scraped
    "manual_entry",  # From manual fallback config
    "scraping_failed",  # Web scraping failed, using fallback
}


class Department(BaseModel):
    """Represents a university department with metadata and quality tracking.

    Attributes:
        id: Unique identifier (auto-generated UUID)
        name: Department name
        school: Parent school/college (optional)
        division: Parent division (optional)
        url: Department homepage URL
        hierarchy_level: Depth in organizational tree (0 = top level)
        is_relevant: Result of relevance filtering (Story 2.3)
        relevance_reasoning: LLM explanation for relevance (Story 2.3)
        data_quality_flags: List of data quality issues from DATA_QUALITY_FLAGS
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    school: Optional[str] = None
    division: Optional[str] = None
    url: str
    hierarchy_level: int = 0
    is_relevant: bool = False
    relevance_reasoning: str = ""
    data_quality_flags: list[str] = Field(default_factory=list)

    def add_quality_flag(self, flag: str) -> None:
        """Add a data quality flag if it's valid and not already present.

        Args:
            flag: Flag from DATA_QUALITY_FLAGS constant set

        Raises:
            ValueError: If flag is not in DATA_QUALITY_FLAGS
        """
        if flag not in DATA_QUALITY_FLAGS:
            raise ValueError(
                f"Invalid data quality flag: {flag}. Must be one of {DATA_QUALITY_FLAGS}"
            )

        if flag not in self.data_quality_flags:
            self.data_quality_flags.append(flag)

    def has_quality_issues(self) -> bool:
        """Check if department has any data quality issues.

        Returns:
            True if data_quality_flags is non-empty
        """
        return len(self.data_quality_flags) > 0
