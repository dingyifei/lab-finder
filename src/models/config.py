"""
Configuration Models

Pydantic models for system configuration validation.
"""

import json
from pathlib import Path
from pydantic import BaseModel, Field, ValidationInfo, field_validator


class BatchConfig(BaseModel):
    """Batch configuration for parallel processing."""

    department_discovery_batch_size: int = Field(default=5, gt=0, lt=100)
    professor_discovery_batch_size: int = Field(default=10, gt=0, lt=100)
    professor_filtering_batch_size: int = Field(default=15, gt=0, lt=100)
    publication_retrieval_batch_size: int = Field(default=20, gt=0, lt=100)
    linkedin_matching_batch_size: int = Field(default=15, gt=0, lt=100)

    @field_validator(
        "department_discovery_batch_size",
        "professor_discovery_batch_size",
        "professor_filtering_batch_size",
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


class RateLimiting(BaseModel):
    """Rate limiting for concurrent operations.

    Story 3.5: Task 7
    """

    max_concurrent_llm_calls: int = Field(
        default=5,
        gt=0,
        le=20,
        description="Maximum concurrent LLM API calls within batch processing"
    )


class Timeouts(BaseModel):
    """Timeout configuration in seconds."""

    web_scraping: int = Field(default=30, gt=0)
    mcp_query: int = Field(default=60, gt=0)


class ConfidenceThresholds(BaseModel):
    """Confidence threshold configuration."""

    professor_filter: float = Field(default=70.0, ge=0.0, le=100.0)
    linkedin_match: float = Field(default=75.0, ge=0.0, le=100.0)


class FilteringConfig(BaseModel):
    """Filtering configuration for confidence-based decisions.

    Story 3.3: Task 1
    """

    low_confidence_threshold: int = Field(default=70, ge=0, le=100)
    high_confidence_threshold: int = Field(default=90, ge=0, le=100)
    borderline_review_enabled: bool = Field(default=True)

    @field_validator("high_confidence_threshold")
    @classmethod
    def validate_threshold_ordering(cls, v: int, info: ValidationInfo) -> int:
        """Validate that high > low and both are in valid range (0-100).

        Validation: 0 < low < high <= 100
        """
        # Get low_confidence_threshold from values dict
        low = info.data.get("low_confidence_threshold", 70)

        if low <= 0:
            raise ValueError("low_confidence_threshold must be greater than 0")
        if v <= low:
            raise ValueError(
                f"high_confidence_threshold ({v}) must be greater than "
                f"low_confidence_threshold ({low})"
            )
        if v > 100:
            raise ValueError("high_confidence_threshold must be <= 100")

        return v


class SystemParams(BaseModel):
    """System parameters configuration model."""

    batch_config: BatchConfig = Field(default_factory=BatchConfig)
    rate_limits: RateLimits = Field(default_factory=RateLimits)
    rate_limiting: RateLimiting = Field(default_factory=RateLimiting)
    timeouts: Timeouts = Field(default_factory=Timeouts)
    confidence_thresholds: ConfidenceThresholds = Field(
        default_factory=ConfidenceThresholds
    )
    filtering_config: FilteringConfig = Field(default_factory=FilteringConfig)
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

    @classmethod
    def load(cls, config_path: Path | str | None = None) -> "SystemParams":
        """Load system parameters from config file.

        Args:
            config_path: Path to system_params.json (defaults to config/system_params.json)

        Returns:
            SystemParams: Validated configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config validation fails
        """
        if config_path is None:
            config_path = Path("config/system_params.json")
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}. "
                f"Copy {config_path.stem}.example.json to {config_path.name}"
            )

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        return cls(**config_data)
