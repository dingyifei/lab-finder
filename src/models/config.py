"""
Configuration Models

Pydantic models for system configuration validation.
"""

from pydantic import BaseModel, Field, field_validator


class BatchConfig(BaseModel):
    """Batch configuration for parallel processing."""

    department_discovery_batch_size: int = Field(default=5, gt=0, lt=100)
    professor_discovery_batch_size: int = Field(default=10, gt=0, lt=100)
    publication_retrieval_batch_size: int = Field(default=20, gt=0, lt=100)
    linkedin_matching_batch_size: int = Field(default=15, gt=0, lt=100)

    @field_validator(
        "department_discovery_batch_size",
        "professor_discovery_batch_size",
        "publication_retrieval_batch_size",
        "linkedin_matching_batch_size",
    )
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        """Validate batch size is within reasonable range."""
        if v <= 0:
            raise ValueError("Batch size must be greater than 0")
        if v >= 100:
            raise ValueError("Batch size must be less than 100")
        return v


class RateLimits(BaseModel):
    """Rate limiting configuration."""

    archive_org: int = Field(default=30, gt=0)
    linkedin: int = Field(default=10, gt=0)
    paper_search: int = Field(default=20, gt=0)


class Timeouts(BaseModel):
    """Timeout configuration in seconds."""

    web_scraping: int = Field(default=30, gt=0)
    mcp_query: int = Field(default=60, gt=0)


class ConfidenceThresholds(BaseModel):
    """Confidence threshold configuration."""

    professor_filter: float = Field(default=70.0, ge=0.0, le=100.0)
    linkedin_match: float = Field(default=75.0, ge=0.0, le=100.0)


class SystemParams(BaseModel):
    """System parameters configuration model."""

    batch_config: BatchConfig = Field(default_factory=BatchConfig)
    rate_limits: RateLimits = Field(default_factory=RateLimits)
    timeouts: Timeouts = Field(default_factory=Timeouts)
    confidence_thresholds: ConfidenceThresholds = Field(
        default_factory=ConfidenceThresholds
    )
    publication_years: int = Field(default=3, gt=0)
    log_level: str = Field(default="INFO")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v.upper()
