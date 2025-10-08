"""Unit tests for Department model."""

import pytest
from pydantic import ValidationError

from src.models.department import Department, DATA_QUALITY_FLAGS


class TestDepartmentModel:
    """Test Department Pydantic model."""

    def test_department_creation_minimal(self):
        """Test creating department with minimal required fields."""
        dept = Department(name="Computer Science", url="https://cs.example.edu")

        assert dept.name == "Computer Science"
        assert dept.url == "https://cs.example.edu"
        assert dept.school is None
        assert dept.division is None
        assert dept.hierarchy_level == 0
        assert dept.data_quality_flags == []
        assert len(dept.id) == 8  # UUID truncated to 8 chars

    def test_department_creation_full(self):
        """Test creating department with all fields."""
        dept = Department(
            name="Computer Science",
            url="https://cs.example.edu",
            school="School of Engineering",
            division="Computing Division",
            hierarchy_level=2,
        )

        assert dept.name == "Computer Science"
        assert dept.school == "School of Engineering"
        assert dept.division == "Computing Division"
        assert dept.hierarchy_level == 2

    def test_department_id_generation(self):
        """Test that department IDs are unique 8-char UUIDs."""
        dept1 = Department(name="CS", url="https://cs.example.edu")
        dept2 = Department(name="CS", url="https://cs.example.edu")

        # IDs should be different even for identical data
        assert dept1.id != dept2.id
        assert len(dept1.id) == 8
        assert len(dept2.id) == 8

    def test_department_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        with pytest.raises(ValidationError) as exc_info:
            Department(name="CS")  # Missing url

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("url",) for e in errors)

    def test_add_quality_flag_valid(self):
        """Test adding valid data quality flags."""
        dept = Department(name="CS", url="https://cs.example.edu")

        dept.add_quality_flag("missing_school")
        assert "missing_school" in dept.data_quality_flags

        dept.add_quality_flag("inference_based")
        assert "inference_based" in dept.data_quality_flags
        assert len(dept.data_quality_flags) == 2

    def test_add_quality_flag_duplicate(self):
        """Test adding duplicate flag doesn't create duplicates."""
        dept = Department(name="CS", url="https://cs.example.edu")

        dept.add_quality_flag("missing_school")
        dept.add_quality_flag("missing_school")

        assert dept.data_quality_flags.count("missing_school") == 1

    def test_add_quality_flag_invalid(self):
        """Test adding invalid flag raises ValueError."""
        dept = Department(name="CS", url="https://cs.example.edu")

        with pytest.raises(ValueError) as exc_info:
            dept.add_quality_flag("invalid_flag")

        assert "Invalid data quality flag" in str(exc_info.value)

    def test_has_quality_issues_empty(self):
        """Test has_quality_issues returns False when no issues."""
        dept = Department(name="CS", url="https://cs.example.edu")

        assert not dept.has_quality_issues()

    def test_has_quality_issues_with_flags(self):
        """Test has_quality_issues returns True when flags present."""
        dept = Department(name="CS", url="https://cs.example.edu")
        dept.add_quality_flag("missing_school")

        assert dept.has_quality_issues()

    def test_all_data_quality_flags_valid(self):
        """Test all defined data quality flags can be added."""
        dept = Department(name="CS", url="https://cs.example.edu")

        for flag in DATA_QUALITY_FLAGS:
            dept.add_quality_flag(flag)

        assert len(dept.data_quality_flags) == len(DATA_QUALITY_FLAGS)

    def test_model_dump(self):
        """Test model serialization to dict."""
        dept = Department(
            name="Computer Science",
            url="https://cs.example.edu",
            school="Engineering",
            hierarchy_level=1,
        )
        dept.add_quality_flag("inference_based")

        data = dept.model_dump()

        assert data["name"] == "Computer Science"
        assert data["url"] == "https://cs.example.edu"
        assert data["school"] == "Engineering"
        assert data["hierarchy_level"] == 1
        assert "inference_based" in data["data_quality_flags"]
        assert "id" in data
        assert len(data["id"]) == 8
