"""Tests for error handling in university structure discovery (Story 2.4)."""

import json
from unittest.mock import AsyncMock, Mock, patch
import pytest
import httpx

from src.models.department import Department, DATA_QUALITY_FLAGS
from src.agents.university_discovery import UniversityDiscoveryAgent, ValidationResult


class TestDepartmentModel:
    """Tests for Department model with data quality flags."""

    def test_department_creation_with_defaults(self):
        """Test creating department with default values."""
        dept = Department(name="Computer Science", url="https://example.edu/cs")

        assert dept.name == "Computer Science"
        assert dept.url == "https://example.edu/cs"
        assert dept.school is None
        assert dept.division is None
        assert dept.hierarchy_level == 0
        assert dept.is_relevant is False
        assert dept.relevance_reasoning == ""
        assert dept.data_quality_flags == []
        assert dept.id is not None  # UUID generated

    def test_department_creation_with_all_fields(self):
        """Test creating department with all fields populated."""
        dept = Department(
            name="Computer Science",
            school="Engineering",
            division="STEM",
            url="https://example.edu/cs",
            hierarchy_level=2,
            is_relevant=True,
            relevance_reasoning="Strong AI research",
            data_quality_flags=["missing_url"],
        )

        assert dept.name == "Computer Science"
        assert dept.school == "Engineering"
        assert dept.division == "STEM"
        assert dept.url == "https://example.edu/cs"
        assert dept.hierarchy_level == 2
        assert dept.is_relevant is True
        assert dept.relevance_reasoning == "Strong AI research"
        assert dept.data_quality_flags == ["missing_url"]

    def test_add_quality_flag_valid(self):
        """Test adding valid data quality flag."""
        dept = Department(name="CS", url="https://example.edu/cs")

        dept.add_quality_flag("missing_url")
        assert "missing_url" in dept.data_quality_flags

        dept.add_quality_flag("missing_school")
        assert "missing_school" in dept.data_quality_flags
        assert len(dept.data_quality_flags) == 2

    def test_add_quality_flag_invalid(self):
        """Test adding invalid flag raises ValueError."""
        dept = Department(name="CS", url="https://example.edu/cs")

        with pytest.raises(ValueError, match="Invalid data quality flag"):
            dept.add_quality_flag("invalid_flag")

    def test_add_quality_flag_duplicate(self):
        """Test adding duplicate flag doesn't create duplicates."""
        dept = Department(name="CS", url="https://example.edu/cs")

        dept.add_quality_flag("missing_url")
        dept.add_quality_flag("missing_url")

        assert dept.data_quality_flags.count("missing_url") == 1

    def test_has_quality_issues_true(self):
        """Test has_quality_issues returns True when flags present."""
        dept = Department(name="CS", url="https://example.edu/cs")
        dept.add_quality_flag("missing_school")

        assert dept.has_quality_issues() is True

    def test_has_quality_issues_false(self):
        """Test has_quality_issues returns False when no flags."""
        dept = Department(name="CS", url="https://example.edu/cs")

        assert dept.has_quality_issues() is False

    def test_all_data_quality_flags_are_valid(self):
        """Test all defined data quality flags can be added."""
        dept = Department(name="CS", url="https://example.edu/cs")

        for flag in DATA_QUALITY_FLAGS:
            dept.add_quality_flag(flag)  # Should not raise

        assert len(dept.data_quality_flags) == len(DATA_QUALITY_FLAGS)


class TestUniversityDiscoveryAgent:
    """Tests for UniversityDiscoveryAgent error handling."""

    @pytest.fixture
    def agent(self, tmp_path):
        """Create agent instance for testing."""
        return UniversityDiscoveryAgent(
            correlation_id="test-correlation-id",
            checkpoint_manager=None,
            output_dir=tmp_path / "output",
        )

    @pytest.mark.asyncio
    async def test_fetch_page_with_retry_success(self, agent):
        """Test successful page fetch on first attempt."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.text = "<html><body>Test</body></html>"
            mock_response.raise_for_status = Mock()

            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            result = await agent._fetch_page_with_retry("https://example.edu")

            assert result == "<html><body>Test</body></html>"
            mock_get.assert_called_once_with("https://example.edu")

    @pytest.mark.asyncio
    async def test_fetch_page_with_retry_transient_failure_then_success(self, agent):
        """Test retry logic succeeds after transient failure."""
        with patch("httpx.AsyncClient") as mock_client:
            # First call raises timeout, second succeeds
            mock_response = Mock()
            mock_response.text = "<html><body>Test</body></html>"
            mock_response.raise_for_status = Mock()

            mock_get = AsyncMock(
                side_effect=[httpx.TimeoutException("Timeout"), mock_response]
            )
            mock_client.return_value.__aenter__.return_value.get = mock_get

            result = await agent._fetch_page_with_retry("https://example.edu")

            assert result == "<html><body>Test</body></html>"
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_page_with_retry_max_retries_exceeded(self, agent):
        """Test retry logic fails after max retries."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with pytest.raises(httpx.TimeoutException):
                await agent._fetch_page_with_retry("https://example.edu")

            # Should have attempted 3 times (original + 2 retries = 3 total)
            assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_page_with_retry_http_error_no_retry(self, agent):
        """Test non-transient HTTP errors are not retried."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status = Mock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found", request=Mock(), response=mock_response
                )
            )

            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with pytest.raises(httpx.HTTPStatusError):
                await agent._fetch_page_with_retry("https://example.edu")

            # Should only attempt once (no retry for 404)
            assert mock_get.call_count == 1

    def test_detect_incomplete_structure_valid_html(self, agent):
        """Test detection with valid HTML returns no issues."""
        html = "<html><head></head><body><p>Content</p></body></html>"

        issues = agent._detect_incomplete_structure(html, "https://example.edu")

        assert issues == []

    def test_detect_incomplete_structure_none_html(self, agent):
        """Test detection with None HTML returns no_html_content issue."""
        issues = agent._detect_incomplete_structure(None, "https://example.edu")

        assert "no_html_content" in issues

    def test_detect_incomplete_structure_empty_html(self, agent):
        """Test detection with empty HTML returns empty_html_content issue."""
        issues = agent._detect_incomplete_structure("   ", "https://example.edu")

        assert "empty_html_content" in issues

    def test_detect_incomplete_structure_invalid_html(self, agent):
        """Test detection with invalid HTML structure returns issue."""
        html = "Just plain text, no HTML tags"

        issues = agent._detect_incomplete_structure(html, "https://example.edu")

        assert "invalid_html_structure" in issues

    def test_apply_graceful_degradation_missing_school(self, agent):
        """Test graceful degradation applies fallback for missing school."""
        department_data = {
            "name": "Computer Science",
            "url": "https://example.edu/cs",
            "hierarchy_level": 2,
        }

        dept = agent._apply_graceful_degradation(department_data, [])

        assert dept.name == "Computer Science"
        assert dept.school == "Unknown School"
        assert "missing_school" in dept.data_quality_flags

    def test_apply_graceful_degradation_missing_url(self, agent):
        """Test graceful degradation flags missing URL."""
        department_data = {"name": "Computer Science", "school": "Engineering"}

        dept = agent._apply_graceful_degradation(department_data, [])

        assert dept.url == ""
        assert "missing_url" in dept.data_quality_flags

    def test_apply_graceful_degradation_partial_metadata(self, agent):
        """Test graceful degradation flags partial metadata."""
        department_data = {
            "name": "Computer Science",
            # Missing school, division, and url
        }

        dept = agent._apply_graceful_degradation(department_data, [])

        assert "missing_school" in dept.data_quality_flags
        assert "missing_url" in dept.data_quality_flags
        assert "partial_metadata" in dept.data_quality_flags

    def test_apply_graceful_degradation_ambiguous_hierarchy(self, agent):
        """Test graceful degradation flags ambiguous hierarchy."""
        department_data = {
            "name": "Computer Science",
            "school": "Engineering",
            "url": "https://example.edu/cs",
            "hierarchy_level": 0,
        }

        dept = agent._apply_graceful_degradation(
            department_data, ["ambiguous_hierarchy"]
        )

        assert "ambiguous_hierarchy" in dept.data_quality_flags

    def test_load_manual_fallback_success(self, agent, tmp_path):
        """Test loading manual fallback configuration."""
        fallback_path = tmp_path / "departments_fallback.json"
        fallback_data = {
            "departments": [
                {
                    "name": "Computer Science",
                    "school": "Engineering",
                    "url": "https://example.edu/cs",
                    "hierarchy_level": 2,
                },
                {
                    "name": "Mathematics",
                    "school": "Sciences",
                    "url": "https://example.edu/math",
                    "hierarchy_level": 2,
                },
            ]
        }

        with open(fallback_path, "w") as f:
            json.dump(fallback_data, f)

        departments = agent._load_manual_fallback(fallback_path)

        assert len(departments) == 2
        assert departments[0].name == "Computer Science"
        assert departments[0].school == "Engineering"
        assert "manual_entry" in departments[0].data_quality_flags
        assert departments[1].name == "Mathematics"
        assert "manual_entry" in departments[1].data_quality_flags

    def test_load_manual_fallback_file_not_found(self, agent, tmp_path):
        """Test loading manual fallback when file doesn't exist."""
        fallback_path = tmp_path / "nonexistent.json"

        departments = agent._load_manual_fallback(fallback_path)

        assert departments == []

    def test_load_manual_fallback_invalid_json(self, agent, tmp_path):
        """Test loading manual fallback with invalid JSON."""
        fallback_path = tmp_path / "invalid.json"

        with open(fallback_path, "w") as f:
            f.write("{ invalid json ")

        departments = agent._load_manual_fallback(fallback_path)

        assert departments == []

    def test_validate_department_structure_no_departments(self, agent):
        """Test validation fails when no departments discovered."""
        result = agent.validate_department_structure([])

        assert result.is_valid is False
        assert result.total_departments == 0
        assert "No departments discovered" in result.errors

    def test_validate_department_structure_below_50_percent_urls(self, agent):
        """Test validation fails when <50% have URLs."""
        departments = [
            Department(name="CS", url="https://example.edu/cs", school="Engineering"),
            Department(name="Math", url="", school="Sciences"),  # Missing URL
            Department(name="Physics", url="", school="Sciences"),  # Missing URL
        ]

        result = agent.validate_department_structure(departments)

        assert result.is_valid is False
        assert result.total_departments == 3
        assert result.departments_with_urls == 1
        assert any("URLs" in error for error in result.errors)

    def test_validate_department_structure_below_50_percent_schools(self, agent):
        """Test validation fails when <50% have school names."""
        departments = [
            Department(name="CS", url="https://example.edu/cs", school="Engineering"),
            Department(name="Math", url="https://example.edu/math"),  # Missing school
            Department(
                name="Physics", url="https://example.edu/physics"
            ),  # Missing school
        ]

        result = agent.validate_department_structure(departments)

        assert result.is_valid is False
        assert result.total_departments == 3
        assert result.departments_with_schools == 1
        assert any("school names" in error for error in result.errors)

    def test_validate_department_structure_passes_at_50_percent(self, agent):
        """Test validation passes at exactly 50% threshold."""
        departments = [
            Department(name="CS", url="https://example.edu/cs", school="Engineering"),
            Department(name="Math", url="", school="Sciences"),  # Missing URL
        ]

        result = agent.validate_department_structure(departments)

        assert result.is_valid is True
        assert result.has_warnings is True
        assert result.departments_with_urls == 1
        assert result.departments_with_schools == 2

    def test_validate_department_structure_passes_with_warnings(self, agent):
        """Test validation passes with warnings for incomplete data."""
        departments = [
            Department(name="CS", url="https://example.edu/cs", school="Engineering"),
            Department(name="Math", url="https://example.edu/math", school="Sciences"),
            Department(name="Physics", url="", school="Sciences"),  # Missing URL
        ]

        result = agent.validate_department_structure(departments)

        assert result.is_valid is True
        assert result.has_warnings is True
        assert len(result.warnings) > 0

    def test_validate_department_structure_passes_perfectly(self, agent):
        """Test validation passes without warnings for complete data."""
        departments = [
            Department(name="CS", url="https://example.edu/cs", school="Engineering"),
            Department(name="Math", url="https://example.edu/math", school="Sciences"),
        ]

        result = agent.validate_department_structure(departments)

        assert result.is_valid is True
        assert result.has_warnings is False
        assert len(result.warnings) == 0

    def test_save_validation_results(self, agent):
        """Test saving validation results to JSON file."""
        result = ValidationResult()
        result.is_valid = True
        result.has_warnings = True
        result.total_departments = 3
        result.departments_with_urls = 2
        result.departments_with_schools = 3
        result.warnings = ["Some URLs missing"]

        agent.save_validation_results(result)

        output_path = agent.output_dir / "structure-validation.json"
        assert output_path.exists()

        with open(output_path, "r") as f:
            data = json.load(f)

        assert data["is_valid"] is True
        assert data["has_warnings"] is True
        assert data["total_departments"] == 3
        assert data["warnings"] == ["Some URLs missing"]

    def test_generate_structure_gap_report_no_issues(self, agent):
        """Test gap report generation when no issues found."""
        departments = [
            Department(name="CS", url="https://example.edu/cs", school="Engineering"),
            Department(name="Math", url="https://example.edu/math", school="Sciences"),
        ]

        agent.generate_structure_gap_report(departments)

        output_path = agent.output_dir / "structure-gaps.md"
        assert output_path.exists()

        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "No data quality issues detected" in content
        assert "**Total Departments:** 2" in content

    def test_generate_structure_gap_report_with_issues(self, agent):
        """Test gap report generation with data quality issues."""
        dept1 = Department(name="CS", url="", school="Engineering")
        dept1.add_quality_flag("missing_url")

        dept2 = Department(
            name="Math", url="https://example.edu/math", school="Unknown School"
        )
        dept2.add_quality_flag("missing_school")

        departments = [dept1, dept2]

        agent.generate_structure_gap_report(departments)

        output_path = agent.output_dir / "structure-gaps.md"
        assert output_path.exists()

        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "**Departments with Data Quality Issues:** 2" in content
        assert "### CS" in content
        assert "### Math" in content
        assert "missing_url" in content
        assert "missing_school" in content
        assert "Recommendations" in content

    def test_get_flag_description(self, agent):
        """Test getting user-friendly flag descriptions."""
        assert "URL could not be found" in agent._get_flag_description("missing_url")
        assert "school/college name" in agent._get_flag_description("missing_school")
        assert "hierarchy level" in agent._get_flag_description("ambiguous_hierarchy")

    @pytest.mark.asyncio
    async def test_discover_structure_http_error_with_fallback(self, agent, tmp_path):
        """Test discovery handles HTTP error and uses fallback."""
        fallback_path = tmp_path / "departments_fallback.json"
        fallback_data = {
            "departments": [
                {"name": "CS", "school": "Engineering", "url": "https://example.edu/cs"}
            ]
        }

        with open(fallback_path, "w") as f:
            json.dump(fallback_data, f)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status = Mock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found", request=Mock(), response=mock_response
                )
            )

            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            departments = await agent.discover_structure(
                "https://example.edu/notfound", manual_fallback_path=fallback_path
            )

            assert len(departments) == 1
            assert departments[0].name == "CS"
            assert "manual_entry" in departments[0].data_quality_flags

    @pytest.mark.asyncio
    async def test_discover_structure_timeout_with_fallback(self, agent, tmp_path):
        """Test discovery handles timeout and uses fallback."""
        fallback_path = tmp_path / "departments_fallback.json"
        fallback_data = {
            "departments": [
                {
                    "name": "Math",
                    "school": "Sciences",
                    "url": "https://example.edu/math",
                }
            ]
        }

        with open(fallback_path, "w") as f:
            json.dump(fallback_data, f)

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.return_value.__aenter__.return_value.get = mock_get

            departments = await agent.discover_structure(
                "https://example.edu/timeout", manual_fallback_path=fallback_path
            )

            assert len(departments) == 1
            assert departments[0].name == "Math"
            assert "manual_entry" in departments[0].data_quality_flags

    @pytest.mark.asyncio
    async def test_discover_structure_error_no_fallback_raises(self, agent):
        """Test discovery re-raises error when no fallback available."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status = Mock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found", request=Mock(), response=mock_response
                )
            )

            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with pytest.raises(httpx.HTTPStatusError):
                await agent.discover_structure("https://example.edu/notfound")
