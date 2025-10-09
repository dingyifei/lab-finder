"""
Lab Model

Pydantic model for lab website data and metadata.
Story 4.1: Task 2
"""

import hashlib
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Lab(BaseModel):
    """Lab website and metadata model.

    Represents a research lab with scraped website content and metadata.
    """

    id: str = Field(
        ...,
        description="Unique identifier (SHA256 hash of professor_id:lab_name, first 16 chars)"
    )
    professor_id: str = Field(..., description="Foreign key to Professor")
    professor_name: str = Field(..., description="PI name for display")
    department: str = Field(..., description="Department affiliation")
    lab_name: str = Field(..., description="Lab name")
    lab_url: Optional[str] = Field(None, description="Lab website URL")
    last_updated: Optional[datetime] = Field(None, description="Last website update")
    description: str = Field(default="", description="Lab description/overview")
    research_focus: list[str] = Field(
        default_factory=list, description="Research themes"
    )
    news_updates: list[str] = Field(
        default_factory=list, description="Recent news items"
    )
    website_content: str = Field(
        default="", description="Full text content (for analysis)"
    )
    data_quality_flags: list[str] = Field(
        default_factory=list, description="Quality issues"
    )

    @staticmethod
    def generate_id(professor_id: str, lab_name: str) -> str:
        """Generate unique lab ID from professor_id and lab_name.

        Args:
            professor_id: Professor unique identifier
            lab_name: Lab name

        Returns:
            First 16 characters of SHA256 hash of "professor_id:lab_name"
        """
        composite_key = f"{professor_id}:{lab_name}"
        hash_digest = hashlib.sha256(composite_key.encode("utf-8")).hexdigest()
        return hash_digest[:16]
