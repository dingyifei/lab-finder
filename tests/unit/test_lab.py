"""
Unit tests for Lab model.

Story 4.1: Task 2
"""

from datetime import datetime
from src.models.lab import Lab


def test_lab_model_validation():
    """Test Lab model Pydantic validation."""
    # Arrange & Act
    lab = Lab(
        id="abc123",
        professor_id="prof456",
        professor_name="Dr. Jane Smith",
        department="Computer Science",
        lab_name="Vision Lab",
        lab_url="https://visionlab.example.edu",
        last_updated=datetime(2025, 10, 1),
        description="Research in computer vision",
        research_focus=["Computer Vision", "Machine Learning"],
        news_updates=["New paper published"],
        website_content="Full page content",
        data_quality_flags=[],
    )

    # Assert
    assert lab.id == "abc123"
    assert lab.professor_id == "prof456"
    assert lab.professor_name == "Dr. Jane Smith"
    assert lab.department == "Computer Science"
    assert lab.lab_name == "Vision Lab"
    assert lab.lab_url == "https://visionlab.example.edu"
    assert lab.last_updated == datetime(2025, 10, 1)
    assert lab.description == "Research in computer vision"
    assert len(lab.research_focus) == 2
    assert len(lab.news_updates) == 1
    assert lab.website_content == "Full page content"
    assert len(lab.data_quality_flags) == 0


def test_lab_generate_id():
    """Test Lab.generate_id() creates consistent 16-char hashes."""
    # Arrange
    professor_id = "prof123"
    lab_name = "Vision Lab"

    # Act
    lab_id1 = Lab.generate_id(professor_id, lab_name)
    lab_id2 = Lab.generate_id(professor_id, lab_name)

    # Assert
    assert len(lab_id1) == 16
    assert lab_id1 == lab_id2  # Same input = same ID
    assert isinstance(lab_id1, str)


def test_lab_generate_id_different_inputs():
    """Test Lab.generate_id() creates different IDs for different inputs."""
    # Arrange & Act
    id1 = Lab.generate_id("prof1", "Lab A")
    id2 = Lab.generate_id("prof2", "Lab A")
    id3 = Lab.generate_id("prof1", "Lab B")

    # Assert
    assert id1 != id2  # Different professor
    assert id1 != id3  # Different lab name
    assert id2 != id3


def test_lab_optional_fields_default():
    """Test Lab model with optional fields using defaults."""
    # Arrange & Act
    lab = Lab(
        id="test123",
        professor_id="prof789",
        professor_name="Dr. John Doe",
        department="Physics",
        lab_name="Quantum Lab",
    )

    # Assert - Optional fields have defaults
    assert lab.lab_url is None
    assert lab.last_updated is None
    assert lab.description == ""
    assert lab.research_focus == []
    assert lab.news_updates == []
    assert lab.website_content == ""
    assert lab.data_quality_flags == []
