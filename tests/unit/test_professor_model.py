"""Unit tests for Professor model."""

import pytest
from pydantic import ValidationError

from src.models.professor import Professor, PROFESSOR_DATA_QUALITY_FLAGS


def test_professor_model_validation():
    """Test Professor model with valid data."""
    prof = Professor(
        id="test-001",
        name="Dr. Jane Smith",
        title="Professor",
        department_id="dept-001",
        department_name="Computer Science",
        profile_url="https://cs.edu/faculty/jsmith",
    )
    assert prof.name == "Dr. Jane Smith"
    assert prof.title == "Professor"
    assert prof.department_id == "dept-001"
    assert prof.department_name == "Computer Science"
    assert prof.profile_url == "https://cs.edu/faculty/jsmith"
    assert prof.data_quality_flags == []
    assert prof.research_areas == []
    assert prof.email is None
    assert prof.lab_name is None
    assert prof.lab_url is None


def test_professor_model_with_optional_fields():
    """Test Professor model with all optional fields populated."""
    prof = Professor(
        id="test-002",
        name="Dr. John Doe",
        title="Associate Professor",
        department_id="dept-002",
        department_name="Bioengineering",
        school="School of Engineering",
        lab_name="Computational Biology Lab",
        lab_url="https://compbio.edu",
        research_areas=["Machine Learning", "Bioinformatics"],
        profile_url="https://bioe.edu/faculty/jdoe",
        email="jdoe@example.edu",
        data_quality_flags=["missing_email"],
    )
    assert prof.school == "School of Engineering"
    assert prof.lab_name == "Computational Biology Lab"
    assert prof.lab_url == "https://compbio.edu"
    assert prof.research_areas == ["Machine Learning", "Bioinformatics"]
    assert prof.email == "jdoe@example.edu"
    assert prof.data_quality_flags == ["missing_email"]


def test_professor_model_missing_required_fields():
    """Test Professor model validation fails with missing required fields."""
    with pytest.raises(ValidationError):
        Professor(
            name="Dr. Jane Smith",
            title="Professor",
            # Missing id, department_id, department_name, profile_url
        )


def test_add_quality_flag():
    """Test adding quality flags to professor."""
    prof = Professor(
        id="test-003",
        name="Dr. Alice Brown",
        title="Assistant Professor",
        department_id="dept-003",
        department_name="Biology",
        profile_url="https://bio.edu/faculty/abrown",
    )

    assert prof.data_quality_flags == []
    assert not prof.has_quality_issues()

    prof.add_quality_flag("missing_email")
    assert "missing_email" in prof.data_quality_flags
    assert prof.has_quality_issues()

    # Adding same flag again should not duplicate
    prof.add_quality_flag("missing_email")
    assert prof.data_quality_flags == ["missing_email"]

    # Add another flag
    prof.add_quality_flag("missing_research_areas")
    assert len(prof.data_quality_flags) == 2
    assert "missing_research_areas" in prof.data_quality_flags


def test_add_invalid_quality_flag():
    """Test adding invalid quality flag raises ValueError."""
    prof = Professor(
        id="test-004",
        name="Dr. Bob Wilson",
        title="Professor",
        department_id="dept-004",
        department_name="Chemistry",
        profile_url="https://chem.edu/faculty/bwilson",
    )

    with pytest.raises(ValueError, match="Invalid data quality flag"):
        prof.add_quality_flag("invalid_flag")


def test_has_quality_issues():
    """Test has_quality_issues method."""
    prof = Professor(
        id="test-005",
        name="Dr. Carol Davis",
        title="Professor",
        department_id="dept-005",
        department_name="Physics",
        profile_url="https://physics.edu/faculty/cdavis",
    )

    assert not prof.has_quality_issues()

    prof.add_quality_flag("missing_lab_affiliation")
    assert prof.has_quality_issues()


def test_professor_data_quality_flags_constant():
    """Test that PROFESSOR_DATA_QUALITY_FLAGS contains expected flags."""
    expected_flags = {
        "scraped_with_playwright_fallback",
        "missing_email",
        "missing_research_areas",
        "missing_lab_affiliation",
        "ambiguous_lab",
    }
    assert PROFESSOR_DATA_QUALITY_FLAGS == expected_flags
