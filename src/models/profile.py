"""
User Profile Data Models
"""

from typing import List
from pydantic import BaseModel


class ConsolidatedProfile(BaseModel):
    """Consolidated user research profile."""

    name: str
    current_degree: str
    target_university: str
    target_department: str
    research_interests: List[str]
    streamlined_interests: str  # LLM-generated concise summary
    education_background: str
    skills_summary: str
    research_experience_summary: str
    key_qualifications: List[str]
    preferred_graduation_duration: float
    university_website: str
    generated_at: str
