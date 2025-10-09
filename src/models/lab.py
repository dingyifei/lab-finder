"""
Lab Model

Pydantic model for lab website data and metadata.
Story 4.1: Task 2
Story 4.2: Task 1 (Archive.org fields)
Story 4.3: Task 1 (Contact fields)
Story 4.4: Task 1 (Website status field and flags)
"""

import hashlib
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# Data quality flag constants (Stories 4.1, 4.2, 4.3, 4.4)
LAB_DATA_QUALITY_FLAGS = {
    # Story 4.1 flags
    "no_website",  # No lab website URL found
    "scraping_failed",  # Website scraping failed
    "playwright_fallback",  # WebFetch failed, used Playwright
    "missing_description",  # No description found
    "missing_research_focus",  # No research focus/areas found
    "missing_news",  # No news/updates found
    "missing_last_updated",  # No last updated date found
    # Story 4.2 flags (Archive.org)
    "no_archive_data",  # No snapshots found in Wayback Machine
    "archive_query_failed",  # Archive.org API query failed
    # Story 4.3 flags (Contact extraction)
    "no_contact_info",  # No contact information found at all
    "no_email",  # No email addresses found
    "no_contact_form",  # No contact form URL found
    "no_application_url",  # No application URL found
    "email_extraction_failed",  # Email extraction raised exception
    "contact_form_extraction_failed",  # Contact form extraction raised exception
    "application_url_extraction_failed",  # Application URL extraction raised exception
    # Story 4.4 flags (Website status)
    "stale_website",  # Website not updated >2 years
    "aging_website",  # Website not updated 1-2 years
    "using_publication_data",  # Relying on publications due to missing/stale website
    "members_will_be_inferred",  # Lab members will be inferred from co-authorship (Story 5.5)
    "status_detection_failed",  # Error occurred during status detection
}


class Lab(BaseModel):
    """Lab website and metadata model.

    Represents a research lab with scraped website content and metadata.
    """

    id: str = Field(
        ...,
        description="Unique identifier (SHA256 hash of professor_id:lab_name, first 16 chars)",
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
    # Archive.org fields (Story 4.2)
    last_wayback_snapshot: Optional[datetime] = Field(
        None, description="Most recent Archive.org snapshot date"
    )
    wayback_snapshots: list[datetime] = Field(
        default_factory=list, description="Snapshot dates over past 3 years"
    )
    update_frequency: str = Field(
        default="unknown",
        description="Website update frequency (weekly/monthly/quarterly/yearly/stale/unknown)",
    )
    # Contact fields (Story 4.3)
    contact_emails: list[str] = Field(
        default_factory=list, description="Professor/lab email addresses"
    )
    contact_form_url: Optional[str] = Field(
        None, description="Contact form URL if available"
    )
    application_url: Optional[str] = Field(
        None, description="Prospective student/application URL"
    )
    # Website status (Story 4.4)
    website_status: str = Field(
        default="unknown",
        description="Website status (active/aging/stale/missing/unavailable/unknown)",
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
