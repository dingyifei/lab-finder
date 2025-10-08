"""University structure discovery agent with error handling and graceful degradation."""

import json
from pathlib import Path
from typing import Any, Optional

from src.models.department import Department
from src.utils.logger import get_logger
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.progress_tracker import ProgressTracker


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

    def __init__(self) -> None:
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

    async def run_discovery_workflow(
        self,
        university_url: str,
        system_params: dict,
        manual_fallback_path: Optional[Path] = None,
        use_progress_tracker: bool = True,
    ) -> list[Department]:
        """Run complete discovery workflow with parallel processing and checkpointing.

        Args:
            university_url: University main page URL
            system_params: System parameters dict with batch_config
            manual_fallback_path: Optional path to manual fallback config
            use_progress_tracker: Whether to display progress (default: True)

        Returns:
            List of discovered departments

        Raises:
            ValueError: If validation fails
        """
        self.logger.info(
            "Starting university discovery workflow",
            url=university_url,
            max_concurrent=system_params.get("batch_config", {}).get(
                "department_discovery_batch_size", 5
            ),
        )

        # Initialize progress tracker
        tracker = ProgressTracker() if use_progress_tracker else None

        try:
            # Discover departments
            if tracker:
                tracker.start_phase("Phase 1: University Discovery", total_items=1)

            departments = await self.discover_structure(
                university_url, manual_fallback_path
            )

            if tracker:
                tracker.update(completed=1)

            # Validate results
            validation_result = self.validate_department_structure(departments)
            self.save_validation_results(validation_result)

            if not validation_result.is_valid:
                error_msg = f"Validation failed: {', '.join(validation_result.errors)}"
                self.logger.error("Validation failed", errors=validation_result.errors)
                raise ValueError(error_msg)

            # Generate gap report
            self.generate_structure_gap_report(departments)

            # Save to checkpoint
            if self.checkpoint_manager:
                self.checkpoint_manager.save_batch(
                    phase="phase-1-departments",
                    batch_id=0,
                    data=departments,
                )
                self.logger.info(
                    "Saved departments to checkpoint",
                    phase="phase-1-departments",
                    count=len(departments),
                )

            if tracker:
                tracker.complete_phase()

            self.logger.info(
                "University discovery workflow complete",
                departments_discovered=len(departments),
                departments_with_issues=sum(1 for d in departments if d.has_quality_issues()),
            )

            return departments

        except Exception:
            if tracker and tracker.is_active():
                tracker.complete_phase()
            raise

    async def discover_structure(
        self, university_url: str, manual_fallback_path: Optional[Path] = None
    ) -> list[Department]:
        """Discover university department structure using Claude Agent SDK.

        Args:
            university_url: University main page or departments directory URL
            manual_fallback_path: Optional path to manual fallback config JSON

        Returns:
            List of discovered departments with quality flags

        Raises:
            ValueError: If discovery fails and no fallback available
        """
        self.logger.info("Starting university structure discovery", url=university_url)

        departments: list[Department] = []

        try:
            # Use Claude Agent SDK with WebFetch/WebSearch tools
            from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

            # Configure SDK with web scraping tools
            options = ClaudeAgentOptions(
                allowed_tools=["WebFetch", "WebSearch"],
                max_turns=3,
                system_prompt="You are a web scraping assistant specialized in extracting university organizational structures."
            )

            # Construct prompt for department extraction
            prompt = f"""Scrape the university website at {university_url} and extract all department information.

For each department, extract:
1. Department name
2. Department URL (full URL)
3. Parent school or college name (if available)
4. Parent division name (if available)
5. Organizational hierarchy level (0=school, 1=division, 2=department)

Return the data as a JSON array with this structure:
[
  {{
    "name": "Computer Science",
    "url": "https://example.edu/cs",
    "school": "School of Engineering",
    "division": null,
    "hierarchy_level": 2
  }}
]

If you cannot find certain fields, use null. Be thorough and extract all departments you can find."""

            self.logger.info("Using Claude Agent SDK for web scraping", url=university_url)

            # Query Claude via SDK
            response_text = ""
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text

            # Parse JSON response
            departments = self._parse_sdk_response(response_text, university_url)

            if not departments:
                self.logger.warning(
                    "No departments extracted from SDK response",
                    url=university_url,
                    response_length=len(response_text)
                )

                # Try manual fallback
                if manual_fallback_path:
                    departments = self._load_manual_fallback(manual_fallback_path)
                    if departments:
                        return departments

                raise ValueError(f"No departments found at {university_url}")

            self.logger.info(
                "University structure discovery complete",
                url=university_url,
                departments_found=len(departments),
                scraping_method="claude_agent_sdk"
            )

        except Exception as e:
            # SDK or parsing error
            self.logger.error(
                "Error during SDK-based structure discovery",
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

    def _parse_sdk_response(self, response_text: str, base_url: str) -> list[Department]:
        """Parse Claude Agent SDK JSON response into Department models.

        Args:
            response_text: Text response from Claude containing JSON
            base_url: Base university URL for logging

        Returns:
            List of Department models
        """
        departments: list[Department] = []

        try:
            # Extract JSON from response (Claude might wrap it in markdown code blocks)
            json_text = response_text.strip()

            # Remove markdown code block markers if present
            if json_text.startswith("```json"):
                json_text = json_text[7:]  # Remove ```json
            elif json_text.startswith("```"):
                json_text = json_text[3:]  # Remove ```

            if json_text.endswith("```"):
                json_text = json_text[:-3]  # Remove trailing ```

            json_text = json_text.strip()

            # Parse JSON
            dept_data_list = json.loads(json_text)

            if not isinstance(dept_data_list, list):
                self.logger.error(
                    "SDK response is not a JSON array",
                    response_preview=json_text[:200]
                )
                return []

            # Convert each JSON object to Department model
            for dept_data in dept_data_list:
                name = dept_data.get("name", "Unknown Department")
                school = dept_data.get("school")
                division = dept_data.get("division")
                url = dept_data.get("url", "")
                hierarchy_level = dept_data.get("hierarchy_level", 0)

                # Create department
                dept = Department(
                    name=name,
                    school=school if school else "Unknown School",
                    division=division,
                    url=url,
                    hierarchy_level=hierarchy_level
                )

                # Add data quality flags
                if not school:
                    dept.add_quality_flag("missing_school")
                if not url:
                    dept.add_quality_flag("missing_url")

                departments.append(dept)

                self.logger.debug(
                    "Parsed department from SDK response",
                    name=name,
                    url=url,
                    school=dept.school
                )

            self.logger.info(
                "Successfully parsed SDK response",
                departments_count=len(departments),
                base_url=base_url
            )

        except json.JSONDecodeError as e:
            self.logger.error(
                "Failed to parse JSON from SDK response",
                error=str(e),
                response_preview=response_text[:500]
            )
        except Exception as e:
            self.logger.error(
                "Unexpected error parsing SDK response",
                error_type=type(e).__name__,
                error=str(e)
            )

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

    def load_departments_from_checkpoint(self) -> list[Department]:
        """Load departments from phase-1 checkpoint.

        Returns:
            List of Department models loaded from checkpoint

        Raises:
            RuntimeError: If checkpoint file missing or no departments found
        """
        if not self.checkpoint_manager:
            self.logger.error(
                "Checkpoint manager not initialized",
                action="Initialize UniversityDiscoveryAgent with checkpoint_manager",
            )
            raise RuntimeError("Checkpoint manager required for loading departments")

        try:
            # Load all batches from phase-1-departments checkpoint
            # load_batches returns a flattened list of all records
            dept_records = self.checkpoint_manager.load_batches("phase-1-departments")

            if not dept_records:
                self.logger.error(
                    "No departments found in checkpoint",
                    checkpoint_file="phase-1-departments.jsonl",
                    action="Verify Story 2.1 completed successfully",
                )
                raise RuntimeError("Cannot proceed without Story 2.1 department data")

            # Deserialize to Department models
            departments: list[Department] = []
            for dept_dict in dept_records:
                try:
                    dept = Department(**dept_dict)
                    departments.append(dept)
                except Exception as e:
                    self.logger.warning(
                        "Failed to deserialize department",
                        error=str(e),
                        department_data=dept_dict,
                    )
                    # Continue processing other departments

            if not departments:
                self.logger.error(
                    "No valid departments after deserialization",
                    checkpoint_file="phase-1-departments.jsonl",
                    action="Check checkpoint file format",
                )
                raise RuntimeError(
                    "Failed to deserialize any departments from checkpoint"
                )

            self.logger.info(
                "Successfully loaded departments from checkpoint",
                total_departments=len(departments),
            )

            return departments

        except FileNotFoundError as e:
            self.logger.error(
                "Checkpoint file not found",
                checkpoint_file="phase-1-departments.jsonl",
                error=str(e),
                action="Run Story 2.1 to generate department checkpoint",
            )
            raise RuntimeError(
                "Checkpoint file not found. Run Story 2.1 first to discover departments."
            ) from e
        except Exception as e:
            self.logger.error(
                "Unexpected error loading departments from checkpoint",
                error=str(e),
                checkpoint_file="phase-1-departments.jsonl",
            )
            raise

    def calculate_department_summary(
        self, departments: list[Department]
    ) -> dict[str, Any]:
        """Calculate summary statistics from departments.

        Args:
            departments: List of Department models

        Returns:
            Dictionary with summary statistics (total_schools, total_divisions, total_departments)
        """
        # Count unique schools
        schools = {dept.school for dept in departments if dept.school}
        total_schools = len(schools)

        # Count unique divisions
        divisions = {dept.division for dept in departments if dept.division}
        total_divisions = len(divisions)

        # Total departments
        total_departments = len(departments)

        summary = {
            "total_schools": total_schools,
            "total_divisions": total_divisions,
            "total_departments": total_departments,
        }

        self.logger.info(
            "Department summary calculated",
            total_schools=total_schools,
            total_divisions=total_divisions,
            total_departments=total_departments,
        )

        return summary

    def create_hierarchical_json(
        self, departments: list[Department], stats: dict[str, Any]
    ) -> dict[str, Any]:
        """Create hierarchical JSON representation of department structure.

        Args:
            departments: List of Department models
            stats: Summary statistics from calculate_department_summary()

        Returns:
            Hierarchical JSON structure for human review
        """
        from datetime import date
        from urllib.parse import urlparse

        # Extract university name
        university_name = "Unknown University"

        # Priority 1: Check config file
        config_path = Path("config/university_config.json")
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    university_name = config.get("university_name", university_name)
            except Exception as e:
                self.logger.warning(
                    "Failed to load university name from config",
                    config_path=str(config_path),
                    error=str(e),
                )

        # Priority 2: Extract from first department URL
        if university_name == "Unknown University" and departments:
            try:
                first_url = departments[0].url
                domain = urlparse(first_url).netloc
                # Simple domain to name conversion (e.g., stanford.edu → Stanford University)
                domain_parts = domain.split(".")
                if len(domain_parts) >= 2:
                    name_part = domain_parts[-2]
                    university_name = f"{name_part.capitalize()} University"
            except Exception as e:
                self.logger.warning(
                    "Failed to extract university name from URL",
                    error=str(e),
                )

        # Priority 3: Log warning if still unknown
        if university_name == "Unknown University":
            self.logger.warning(
                "Using default university name",
                university_name=university_name,
                action="Set university_name in config/university_config.json",
            )

        # Build hierarchical structure
        hierarchy: dict[str, Any] = {
            "university": university_name,
            "discovery_date": date.today().isoformat(),
            "total_schools": stats["total_schools"],
            "total_divisions": stats["total_divisions"],
            "total_departments": stats["total_departments"],
            "schools": [],
        }

        # Group departments by school
        schools_map: dict[str, dict[str, Any]] = {}
        for dept in departments:
            school_name = dept.school or "Unknown School"

            # Initialize school if not exists
            if school_name not in schools_map:
                schools_map[school_name] = {
                    "name": school_name,
                    "url": dept.url if dept.hierarchy_level == 0 else "",
                    "divisions": {},
                    "departments": [],
                }

            # Handle departments with divisions
            if dept.division:
                division_name = dept.division

                # Initialize division if not exists
                if division_name not in schools_map[school_name]["divisions"]:
                    schools_map[school_name]["divisions"][division_name] = {
                        "name": division_name,
                        "url": dept.url if dept.hierarchy_level == 1 else "",
                        "departments": [],
                    }

                # Add department to division
                if dept.hierarchy_level >= 2:
                    schools_map[school_name]["divisions"][division_name][
                        "departments"
                    ].append(
                        {
                            "id": dept.id,
                            "name": dept.name,
                            "url": dept.url,
                            "hierarchy_level": dept.hierarchy_level,
                        }
                    )
            else:
                # Add department directly to school (no division)
                if dept.hierarchy_level >= 1:
                    schools_map[school_name]["departments"].append(
                        {
                            "id": dept.id,
                            "name": dept.name,
                            "url": dept.url,
                            "hierarchy_level": dept.hierarchy_level,
                        }
                    )

        # Convert divisions dict to list and clean up
        for school_name, school_data in schools_map.items():
            # Convert divisions dict to list
            if school_data["divisions"]:
                school_data["divisions"] = list(school_data["divisions"].values())
            else:
                # Remove empty divisions key for flat structures
                del school_data["divisions"]

            hierarchy["schools"].append(school_data)

        self.logger.info(
            "Hierarchical JSON created",
            university=university_name,
            total_schools=len(hierarchy["schools"]),
        )

        return hierarchy

    def validate_hierarchical_json(self, hierarchy_json: dict[str, Any]) -> None:
        """Validate hierarchical JSON against schema.

        Args:
            hierarchy_json: Hierarchical JSON structure to validate

        Raises:
            jsonschema.ValidationError: If JSON doesn't match schema
        """
        import jsonschema

        # Load schema
        schema_path = Path("src/schemas/department-structure.schema.json")
        if not schema_path.exists():
            self.logger.error(
                "Schema file not found",
                schema_path=str(schema_path),
                action="Ensure department-structure.schema.json exists",
            )
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
        except Exception as e:
            self.logger.error(
                "Failed to load schema file",
                schema_path=str(schema_path),
                error=str(e),
            )
            raise

        # Validate JSON against schema
        try:
            jsonschema.validate(instance=hierarchy_json, schema=schema)
            self.logger.info("JSON schema validation passed")
        except jsonschema.ValidationError as e:
            self.logger.error(
                "JSON validation failed",
                error=str(e),
                path=list(e.path),
                schema_path=list(e.schema_path),
            )
            raise

    def get_departments_for_parallel_processing(self) -> list[Department]:
        """Get flattened list of departments for parallel async processing.

        This method provides a simple interface for Epic 3 professor discovery
        to iterate over departments using asyncio.gather() pattern.

        Returns:
            Flattened list of all departments with full context

        Raises:
            RuntimeError: If checkpoint file missing or no departments found
        """
        # Reuse load_departments_from_checkpoint for consistency
        departments = self.load_departments_from_checkpoint()

        self.logger.info(
            "Departments prepared for parallel processing",
            total_departments=len(departments),
        )

        return departments

    def save_hierarchical_json(
        self, hierarchy_json: dict[str, Any], output_path: Optional[Path] = None
    ) -> Path:
        """Save hierarchical JSON to file with human-readable formatting.

        Args:
            hierarchy_json: Hierarchical JSON structure to save
            output_path: Optional custom output path (default: checkpoints/phase-1-department-structure.json)

        Returns:
            Path to saved file
        """
        if output_path is None:
            output_path = Path("checkpoints/phase-1-department-structure.json")

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save with human-readable formatting
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(hierarchy_json, f, indent=2, ensure_ascii=False)

            self.logger.info(
                "Hierarchical JSON saved",
                output_path=str(output_path),
                file_size_kb=output_path.stat().st_size / 1024,
            )

            # Verify file exists and is valid JSON
            with open(output_path, "r", encoding="utf-8") as f:
                json.load(f)  # Quick validation

            self.logger.info("JSON file verification passed")

            return output_path

        except Exception as e:
            self.logger.error(
                "Failed to save hierarchical JSON",
                output_path=str(output_path),
                error=str(e),
            )
            raise

    def load_user_profile(self, profile_path: Optional[Path] = None) -> dict[str, str]:
        """Load user research profile from markdown file.

        Args:
            profile_path: Optional path to profile file (default: output/user-profile.md)

        Returns:
            Dict with 'interests', 'degree', 'background' extracted from profile

        Raises:
            FileNotFoundError: If profile file doesn't exist
            ValueError: If profile format is invalid
        """
        if profile_path is None:
            profile_path = Path("output/user-profile.md")

        if not profile_path.exists():
            self.logger.error(
                "User profile not found",
                profile_path=str(profile_path),
                action="Run Story 1.7 to generate user profile",
            )
            raise FileNotFoundError(
                f"User profile not found at {profile_path}. "
                "Run Story 1.7 (profile consolidation) first."
            )

        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse markdown to extract key sections
            # Expected format from Story 1.7 ConsolidatedProfile
            profile_data = {
                "interests": "",
                "degree": "",
                "background": "",
            }

            # Extract research interests (streamlined_interests field)
            if "## Streamlined Research Interests" in content:
                start = content.index("## Streamlined Research Interests")
                end = content.find("\n##", start + 1)
                if end == -1:
                    end = len(content)
                profile_data["interests"] = content[start:end].replace(
                    "## Streamlined Research Interests", ""
                ).strip()

            # Extract degree program
            if "**Current Degree:**" in content:
                start = content.index("**Current Degree:**")
                end = content.find("\n", start)
                profile_data["degree"] = content[start:end].replace(
                    "**Current Degree:**", ""
                ).strip()

            # Extract educational background
            if "## Educational Background" in content:
                start = content.index("## Educational Background")
                end = content.find("\n##", start + 1)
                if end == -1:
                    end = len(content)
                profile_data["background"] = content[start:end].replace(
                    "## Educational Background", ""
                ).strip()

            # Validate required fields
            if not profile_data["interests"]:
                self.logger.warning(
                    "Research interests not found in profile",
                    profile_path=str(profile_path),
                )

            self.logger.info(
                "User profile loaded successfully",
                profile_path=str(profile_path),
                has_interests=bool(profile_data["interests"]),
                has_degree=bool(profile_data["degree"]),
            )

            return profile_data

        except Exception as e:
            self.logger.error(
                "Failed to load user profile",
                profile_path=str(profile_path),
                error=str(e),
            )
            raise ValueError(f"Invalid profile format: {e}") from e

    async def filter_departments(
        self,
        departments: list[Department],
        user_profile: dict[str, str],
        system_params: Optional[dict] = None,
        use_progress_tracker: bool = True,
    ) -> list[Department]:
        """Filter departments based on research relevance using LLM.

        Args:
            departments: List of departments to filter
            user_profile: User profile dict with 'interests', 'degree', 'background'
            system_params: Optional system parameters for batch size
            use_progress_tracker: Whether to display progress (default: True)

        Returns:
            List of all departments with is_relevant and relevance_reasoning fields updated
        """
        from src.utils.llm_helpers import analyze_department_relevance

        if not departments:
            self.logger.warning("No departments to filter")
            return []

        # Initialize progress tracker
        tracker = ProgressTracker() if use_progress_tracker else None

        if tracker:
            tracker.start_phase(
                "Phase 1: Department Filtering",
                total_items=len(departments)
            )

        self.logger.info(
            "Starting department relevance filtering",
            total_departments=len(departments),
            user_interests=user_profile.get("interests", "")[:100],
        )

        # Filter each department
        filtered_count = 0
        edge_cases: list[dict[str, Any]] = []

        for idx, dept in enumerate(departments):
            try:
                # Call LLM for relevance analysis
                result = await analyze_department_relevance(
                    department_name=dept.name,
                    school=dept.school or "Unknown School",
                    research_interests=user_profile.get("interests", ""),
                    degree=user_profile.get("degree", ""),
                    background=user_profile.get("background", ""),
                    correlation_id=self.correlation_id,
                )

                # Update department fields
                dept.is_relevant = result["decision"] == "include"
                dept.relevance_reasoning = result["reasoning"]

                # Log decision
                log_level = "info" if dept.is_relevant else "debug"
                getattr(self.logger, log_level)(
                    "Department relevance decision",
                    department_id=dept.id,
                    department_name=dept.name,
                    school=dept.school,
                    decision=result["decision"],
                    confidence=result["confidence"],
                    reasoning=result["reasoning"],
                )

                # Track edge cases (interdisciplinary, ambiguous, generic)
                if self._is_edge_case(dept, result):
                    edge_cases.append({
                        "department": dept.name,
                        "school": dept.school,
                        "decision": result["decision"],
                        "confidence": result["confidence"],
                        "reasoning": result["reasoning"],
                        "edge_case_type": self._classify_edge_case(dept),
                    })
                    self.logger.warning(
                        "Edge case department detected",
                        department=dept.name,
                        edge_case_type=self._classify_edge_case(dept),
                        decision=result["decision"],
                    )

                if not dept.is_relevant:
                    filtered_count += 1

                # Update progress
                if tracker:
                    tracker.update(completed=idx + 1)

            except Exception as e:
                self.logger.error(
                    "Error filtering department",
                    department_id=dept.id,
                    department_name=dept.name,
                    error=str(e),
                )
                # Default to exclude on error
                dept.is_relevant = False
                dept.relevance_reasoning = f"Error during filtering: {str(e)}"
                filtered_count += 1

        if tracker:
            tracker.complete_phase()

        relevant_count = len(departments) - filtered_count
        retention_rate = (relevant_count / len(departments) * 100) if departments else 0

        self.logger.info(
            "Department filtering complete",
            total_departments=len(departments),
            relevant_departments=relevant_count,
            filtered_departments=filtered_count,
            retention_rate_percent=retention_rate,
            edge_cases_count=len(edge_cases),
        )

        return departments

    def _is_edge_case(self, dept: Department, llm_result: dict[str, Any]) -> bool:
        """Determine if department is an edge case.

        Args:
            dept: Department model
            llm_result: LLM analysis result

        Returns:
            True if department is an edge case
        """
        dept_name_lower = dept.name.lower()

        # Check for interdisciplinary keywords
        interdisciplinary_keywords = [
            "interdisciplinary", "multidisciplinary", "cross-disciplinary",
            "&", "and", "joint", "combined"
        ]
        if any(kw in dept_name_lower for kw in interdisciplinary_keywords):
            return True

        # Check for generic department names
        generic_keywords = [
            "graduate studies", "research", "sciences", "engineering",
            "general", "studies", "school of"
        ]
        if any(dept_name_lower == kw or dept_name_lower.startswith(kw) for kw in generic_keywords):
            return True

        # Check for ambiguous confidence (between 40-60)
        confidence = llm_result.get("confidence", 0)
        if 40 <= confidence <= 60:
            return True

        return False

    def _classify_edge_case(self, dept: Department) -> str:
        """Classify the type of edge case.

        Args:
            dept: Department model

        Returns:
            Edge case type string
        """
        dept_name_lower = dept.name.lower()

        if any(kw in dept_name_lower for kw in ["&", "and", "interdisciplinary", "multidisciplinary"]):
            return "interdisciplinary"
        elif any(kw in dept_name_lower for kw in ["graduate", "general", "studies"]):
            return "generic"
        else:
            return "ambiguous"

    def save_filtered_departments_report(
        self, departments: list[Department], output_path: Optional[Path] = None
    ) -> None:
        """Save filtered (excluded) departments report for user review.

        Args:
            departments: List of all departments (with is_relevant flags)
            output_path: Optional custom output path (default: output/filtered-departments.md)
        """
        if output_path is None:
            output_path = self.output_dir / "filtered-departments.md"

        # Filter to excluded departments only
        excluded = [d for d in departments if not d.is_relevant]

        # Build markdown report
        lines = [
            "# Filtered Departments Report",
            "",
            "## Summary",
            "",
            f"**Total Departments:** {len(departments)}",
            f"**Relevant Departments:** {len(departments) - len(excluded)}",
            f"**Filtered Out:** {len(excluded)}",
            f"**Retention Rate:** {((len(departments) - len(excluded)) / len(departments) * 100):.1f}%"
            if departments else "N/A",
            "",
            "## Excluded Departments",
            "",
            "The following departments were filtered out as not relevant to your research interests.",
            "Review this list to ensure no relevant departments were excluded.",
            "",
            "| Department | School | Reason | Confidence |",
            "|------------|--------|--------|------------|",
        ]

        for dept in excluded:
            # Extract confidence from reasoning if available
            confidence = "N/A"
            reasoning = dept.relevance_reasoning or "No reasoning provided"

            lines.append(
                f"| {dept.name} | {dept.school or 'N/A'} | {reasoning} | {confidence} |"
            )

        lines.extend([
            "",
            "## Instructions",
            "",
            "If you find departments that should be included:",
            "1. Manually adjust `checkpoints/phase-1-relevant-departments.jsonl`",
            "2. Or re-run with adjusted research interests in your user profile",
            "",
        ])

        # Write report
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        self.logger.info(
            "Filtered departments report saved",
            output_path=str(output_path),
            excluded_count=len(excluded),
        )

    def save_relevant_departments_checkpoint(
        self, departments: list[Department]
    ) -> None:
        """Save relevant departments to checkpoint for next phase.

        Args:
            departments: List of all departments (with is_relevant flags)
        """
        if not self.checkpoint_manager:
            self.logger.error(
                "Checkpoint manager not initialized",
                action="Initialize UniversityDiscoveryAgent with checkpoint_manager",
            )
            raise RuntimeError("Checkpoint manager required for saving relevant departments")

        # Filter to relevant departments only
        relevant = [d for d in departments if d.is_relevant]

        if not relevant:
            self.logger.warning("No relevant departments to save to checkpoint")
            return

        # Save to checkpoint
        self.checkpoint_manager.save_batch(
            phase="phase-1-relevant-departments",
            batch_id=0,
            data=relevant,
        )

        self.logger.info(
            "Relevant departments saved to checkpoint",
            checkpoint_phase="phase-1-relevant-departments",
            relevant_count=len(relevant),
            total_count=len(departments),
        )
