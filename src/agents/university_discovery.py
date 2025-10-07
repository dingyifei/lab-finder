"""University structure discovery agent with error handling and graceful degradation."""

import json
from pathlib import Path
from typing import Any, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import httpx

from src.models.department import Department
from src.utils.logger import get_logger
from src.utils.checkpoint_manager import CheckpointManager


class ValidationResult:
    """Result of department structure validation.

    Attributes:
        is_valid: True if structure meets minimum requirements
        has_warnings: True if structure has quality issues but passes
        total_departments: Total number of departments discovered
        departments_with_urls: Count of departments with URLs
        departments_with_schools: Count of departments with school names
        errors: List of blocking errors
        warnings: List of non-blocking warnings
    """

    def __init__(self):
        self.is_valid = False
        self.has_warnings = False
        self.total_departments = 0
        self.departments_with_urls = 0
        self.departments_with_schools = 0
        self.errors: list[str] = []
        self.warnings: list[str] = []


class UniversityDiscoveryAgent:
    """Agent for discovering university department structure with error handling.

    Handles web scraping failures, missing data, and provides graceful degradation
    with comprehensive logging and data quality tracking.
    """

    def __init__(
        self,
        correlation_id: str,
        checkpoint_manager: Optional[CheckpointManager] = None,
        output_dir: Path = Path("output"),
    ):
        """Initialize discovery agent.

        Args:
            correlation_id: Unique ID for tracing this discovery session
            checkpoint_manager: Optional checkpoint manager for state persistence
            output_dir: Directory for output reports (default: ./output)
        """
        self.correlation_id = correlation_id
        self.logger: Any = get_logger(
            correlation_id=correlation_id,
            phase="university_discovery",
            component="university_discovery_agent",
        )
        self.checkpoint_manager = checkpoint_manager
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def _fetch_page_with_retry(self, url: str, timeout: int = 30) -> str:
        """Fetch page content with retry logic for transient failures.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            HTML content as string

        Raises:
            httpx.HTTPStatusError: For non-transient errors (404, 403, etc.)
            httpx.TimeoutException: After max retries exceeded
            httpx.NetworkError: After max retries exceeded
        """
        self.logger.info("Fetching page", url=url)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    def _detect_incomplete_structure(
        self, html_content: Optional[str], url: str
    ) -> list[str]:
        """Detect if structure discovery is incomplete or ambiguous.

        Args:
            html_content: HTML content from page (None if fetch failed)
            url: URL that was attempted

        Returns:
            List of detected issues (empty if no issues found)
        """
        issues = []

        # Check if HTML is valid
        if html_content is None:
            issues.append("no_html_content")
            self.logger.warning(
                "No HTML content returned", url=url, issue="no_html_content"
            )
            return issues

        if not html_content.strip():
            issues.append("empty_html_content")
            self.logger.warning(
                "Empty HTML content", url=url, issue="empty_html_content"
            )

        # Basic HTML validation
        if "<html" not in html_content.lower() and "<body" not in html_content.lower():
            issues.append("invalid_html_structure")
            self.logger.warning(
                "HTML missing basic structure tags",
                url=url,
                issue="invalid_html_structure",
            )

        return issues

    def _apply_graceful_degradation(
        self, department_data: dict, issues: list[str]
    ) -> Department:
        """Apply graceful degradation for missing or ambiguous data.

        Args:
            department_data: Raw department data from scraping
            issues: List of detected issues

        Returns:
            Department model with fallbacks applied and quality flags set
        """
        # Apply fallbacks for missing fields
        name = department_data.get("name", "Unknown Department")
        school = department_data.get("school")
        division = department_data.get("division")
        url = department_data.get("url", "")
        hierarchy_level = department_data.get("hierarchy_level", 0)

        # Create department instance
        dept = Department(
            name=name,
            school=school,
            division=division,
            url=url,
            hierarchy_level=hierarchy_level,
        )

        # Apply data quality flags based on missing data
        if not school or school == "Unknown School":
            dept.add_quality_flag("missing_school")
            if not school:
                dept.school = "Unknown School"

        if not url:
            dept.add_quality_flag("missing_url")

        if not division:
            # Division is optional, only flag if other metadata is also missing
            if not school or not url:
                dept.add_quality_flag("partial_metadata")

        if hierarchy_level == 0 and "ambiguous_hierarchy" in issues:
            dept.add_quality_flag("ambiguous_hierarchy")

        # Log degradation
        if dept.has_quality_issues():
            self.logger.warning(
                "Applied graceful degradation",
                department=name,
                school=school,
                quality_flags=dept.data_quality_flags,
            )

        return dept

    async def discover_structure(
        self, university_url: str, manual_fallback_path: Optional[Path] = None
    ) -> list[Department]:
        """Discover university department structure with error handling.

        Args:
            university_url: University main page or departments directory URL
            manual_fallback_path: Optional path to manual fallback config JSON

        Returns:
            List of discovered departments with quality flags

        Raises:
            ValueError: If validation fails and no fallback available
        """
        self.logger.info("Starting university structure discovery", url=university_url)

        departments: list[Department] = []

        try:
            # Attempt to fetch main page with retry logic
            html_content = await self._fetch_page_with_retry(university_url)

            # Detect incomplete structure
            # Note: issues would be used by actual scraping logic (Story 2.1)
            _ = self._detect_incomplete_structure(html_content, university_url)

            # TODO: Actual scraping logic would go here
            # For now, create placeholder to demonstrate error handling
            # This would be implemented in Story 2.1
            self.logger.info(
                "HTML fetch successful",
                url=university_url,
                content_length=len(html_content),
            )

        except httpx.HTTPStatusError as e:
            # Non-retryable HTTP error (404, 403, etc.)
            self.logger.error(
                "HTTP error during structure discovery",
                url=university_url,
                status_code=e.response.status_code,
                error=str(e),
            )

            # Try manual fallback
            if manual_fallback_path:
                departments = self._load_manual_fallback(manual_fallback_path)
                if departments:
                    return departments

            # If no fallback, re-raise
            raise

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            # Transient error that exceeded max retries
            self.logger.error(
                "Network error after max retries",
                url=university_url,
                error=str(e),
                attempted_retries=3,
            )

            # Try manual fallback
            if manual_fallback_path:
                departments = self._load_manual_fallback(manual_fallback_path)
                if departments:
                    return departments

            # If no fallback, re-raise
            raise

        except Exception as e:
            # Unexpected error
            self.logger.error(
                "Unexpected error during structure discovery",
                url=university_url,
                error_type=type(e).__name__,
                error=str(e),
            )

            # Try manual fallback
            if manual_fallback_path:
                departments = self._load_manual_fallback(manual_fallback_path)
                if departments:
                    return departments

            # If no fallback, re-raise
            raise

        return departments

    def _load_manual_fallback(self, fallback_path: Path) -> list[Department]:
        """Load departments from manual fallback configuration.

        Args:
            fallback_path: Path to departments_fallback.json

        Returns:
            List of departments from manual config, or empty list if load fails
        """
        self.logger.info("Attempting to load manual fallback", path=str(fallback_path))

        try:
            if not fallback_path.exists():
                self.logger.warning(
                    "Manual fallback file not found", path=str(fallback_path)
                )
                return []

            with open(fallback_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            departments = []
            for dept_data in data.get("departments", []):
                dept = Department(
                    name=dept_data["name"],
                    school=dept_data.get("school"),
                    division=dept_data.get("division"),
                    url=dept_data.get("url", ""),
                    hierarchy_level=dept_data.get("hierarchy_level", 0),
                )
                dept.add_quality_flag("manual_entry")
                departments.append(dept)

            self.logger.info(
                "Loaded manual fallback departments",
                count=len(departments),
                path=str(fallback_path),
            )

            return departments

        except Exception as e:
            self.logger.error(
                "Failed to load manual fallback", path=str(fallback_path), error=str(e)
            )
            return []

    def validate_department_structure(
        self, departments: list[Department]
    ) -> ValidationResult:
        """Validate discovered department structure against minimum requirements.

        Minimum requirements:
        - At least 1 department discovered
        - At least 50% of departments have URLs
        - At least 50% of departments have school names

        Args:
            departments: List of discovered departments

        Returns:
            ValidationResult with detailed validation status
        """
        result = ValidationResult()
        result.total_departments = len(departments)

        # Check minimum: at least 1 department
        if result.total_departments == 0:
            result.errors.append("No departments discovered")
            self.logger.error("Validation failed: no departments discovered")
            result.is_valid = False
            return result

        # Count departments with URLs and schools
        for dept in departments:
            if dept.url:
                result.departments_with_urls += 1
            if dept.school and dept.school != "Unknown School":
                result.departments_with_schools += 1

        # Calculate percentages
        url_percentage = (result.departments_with_urls / result.total_departments) * 100
        school_percentage = (
            result.departments_with_schools / result.total_departments
        ) * 100

        # Check 50% thresholds
        if url_percentage < 50:
            result.errors.append(
                f"Only {url_percentage:.1f}% of departments have URLs (minimum 50% required)"
            )

        if school_percentage < 50:
            result.errors.append(
                f"Only {school_percentage:.1f}% of departments have school names (minimum 50% required)"
            )

        # Determine validation status
        if result.errors:
            result.is_valid = False
            self.logger.error(
                "Validation failed",
                total_departments=result.total_departments,
                url_percentage=url_percentage,
                school_percentage=school_percentage,
                errors=result.errors,
            )
        else:
            result.is_valid = True

            # Check for warnings (between 50% and 100%)
            if url_percentage < 100:
                result.warnings.append(
                    f"{url_percentage:.1f}% of departments have URLs (some missing)"
                )
                result.has_warnings = True

            if school_percentage < 100:
                result.warnings.append(
                    f"{school_percentage:.1f}% of departments have school names (some missing)"
                )
                result.has_warnings = True

            if result.has_warnings:
                self.logger.warning(
                    "Validation passed with warnings",
                    total_departments=result.total_departments,
                    url_percentage=url_percentage,
                    school_percentage=school_percentage,
                    warnings=result.warnings,
                )
            else:
                self.logger.info(
                    "Validation passed", total_departments=result.total_departments
                )

        return result

    def save_validation_results(self, result: ValidationResult) -> None:
        """Save validation results to JSON file.

        Args:
            result: Validation result to save
        """
        output_path = self.output_dir / "structure-validation.json"

        validation_data = {
            "is_valid": result.is_valid,
            "has_warnings": result.has_warnings,
            "total_departments": result.total_departments,
            "departments_with_urls": result.departments_with_urls,
            "departments_with_schools": result.departments_with_schools,
            "url_percentage": (
                result.departments_with_urls / result.total_departments * 100
            )
            if result.total_departments > 0
            else 0,
            "school_percentage": (
                result.departments_with_schools / result.total_departments * 100
            )
            if result.total_departments > 0
            else 0,
            "errors": result.errors,
            "warnings": result.warnings,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(validation_data, f, indent=2)

        self.logger.info("Saved validation results", path=str(output_path))

    def generate_structure_gap_report(self, departments: list[Department]) -> None:
        """Generate user-facing report of structure data gaps.

        Args:
            departments: List of departments to analyze
        """
        output_path = self.output_dir / "structure-gaps.md"

        # Filter departments with quality issues
        departments_with_issues = [d for d in departments if d.has_quality_issues()]

        # Build report content
        report_lines = [
            "# University Structure Data Gaps Report",
            "",
            "## Summary",
            "",
            f"- **Total Departments:** {len(departments)}",
            f"- **Departments with Data Quality Issues:** {len(departments_with_issues)}",
            f"- **Completion Rate:** {((len(departments) - len(departments_with_issues)) / len(departments) * 100):.1f}%"
            if departments
            else "N/A",
            "",
        ]

        if not departments_with_issues:
            report_lines.extend(
                [
                    "✅ **No data quality issues detected!**",
                    "",
                    "All departments have complete metadata and were successfully discovered.",
                ]
            )
        else:
            report_lines.extend(
                [
                    "## Departments with Data Quality Issues",
                    "",
                    "⚠️ The following departments have incomplete or inferred data:",
                    "",
                ]
            )

            for dept in departments_with_issues:
                report_lines.append(f"### {dept.name}")
                if dept.school:
                    report_lines.append(f"**School:** {dept.school}")
                report_lines.append(f"**URL:** {dept.url or '*(missing)*'}")
                report_lines.append("")
                report_lines.append("**Data Quality Flags:**")

                for flag in dept.data_quality_flags:
                    # Provide user-friendly descriptions
                    description = self._get_flag_description(flag)
                    report_lines.append(f"- `{flag}`: {description}")

                report_lines.append("")

            report_lines.extend(
                [
                    "## Recommendations",
                    "",
                    "Consider manually verifying departments with data quality issues.",
                    "You can provide manual department data using `config/departments_fallback.json`.",
                    "",
                ]
            )

        # Write report
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        self.logger.info(
            "Generated structure gap report",
            path=str(output_path),
            total_departments=len(departments),
            departments_with_issues=len(departments_with_issues),
        )

    def _get_flag_description(self, flag: str) -> str:
        """Get user-friendly description for data quality flag.

        Args:
            flag: Data quality flag

        Returns:
            Human-readable description
        """
        descriptions = {
            "missing_url": "Department URL could not be found",
            "missing_school": "Parent school/college name is unknown",
            "ambiguous_hierarchy": "Organizational hierarchy level is unclear",
            "partial_metadata": "Some metadata fields are missing",
            "inference_based": "Information was inferred rather than directly scraped",
            "manual_entry": "Department was loaded from manual fallback configuration",
            "scraping_failed": "Web scraping failed, using fallback strategy",
        }
        return descriptions.get(flag, "Unknown data quality issue")
