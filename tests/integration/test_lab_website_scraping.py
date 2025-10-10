"""
Integration tests for Lab Website Scraping.

Story 4.1: Tasks 8-11
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.agents.lab_research import (
    process_single_lab,
    discover_and_scrape_labs_batch,
)
from src.models.professor import Professor
from src.models.lab import Lab


@pytest.mark.asyncio
async def test_process_single_lab_with_url():
    """Test process_single_lab with valid lab URL."""
    # Arrange
    professor = Professor(
        id="prof1",
        name="Dr. Jane Smith",
        title="Professor",
        department_id="dept1",
        department_name="Computer Science",
        profile_url="https://cs.example.edu/jsmith",
        lab_url="https://visionlab.example.edu",
    )

    mock_scraped_data = {
        # Category 1: lab_information
        "description": "Vision research lab",
        "news_updates": ["New paper published"],
        "last_updated": datetime(2025, 10, 1),
        # Category 2: contact
        "contact_emails": ["vision@example.edu"],
        "contact_form_url": "https://visionlab.example.edu/contact",
        "application_url": "https://visionlab.example.edu/join",
        # Category 3: people
        "lab_members": ["Dr. Jane Smith (PI)", "Alice Chen (PhD)", "Bob Li (Postdoc)"],
        # Category 4: research_focus
        "research_focus": ["Computer Vision", "ML"],
        # Category 5: publications
        "publications_list": ["Paper 1: Vision Transformers", "Paper 2: 3D Reconstruction"],
        # Other
        "website_content": "Full content",
        "data_quality_flags": [],
    }

    with patch(
        "src.agents.lab_research.scrape_lab_website",
        new=AsyncMock(return_value=mock_scraped_data),
    ):
        # Act
        lab = await process_single_lab(professor, "test-correlation-id")

        # Assert
        assert lab.professor_id == "prof1"
        assert lab.professor_name == "Dr. Jane Smith"
        assert lab.lab_url == "https://visionlab.example.edu"
        assert lab.description == "Vision research lab"
        assert len(lab.research_focus) == 2
        assert "Computer Vision" in lab.research_focus


@pytest.mark.asyncio
async def test_process_single_lab_no_url():
    """Test process_single_lab when no lab URL found."""
    # Arrange
    professor = Professor(
        id="prof2",
        name="Dr. John Doe",
        title="Associate Professor",
        department_id="dept2",
        department_name="Physics",
        profile_url="https://physics.example.edu/jdoe",
        lab_url=None,
    )

    # Act
    lab = await process_single_lab(professor, "test-correlation-id")

    # Assert
    assert lab.professor_id == "prof2"
    assert lab.lab_url is None
    assert "no_website" in lab.data_quality_flags
    assert lab.description == ""
    assert lab.research_focus == []


@pytest.mark.asyncio
async def test_process_single_lab_scraping_fails():
    """Test process_single_lab when scraping fails."""
    # Arrange
    professor = Professor(
        id="prof3",
        name="Dr. Alice Brown",
        title="Professor",
        department_id="dept3",
        department_name="Mathematics",
        profile_url="https://math.example.edu/abrown",
        lab_url="https://mathlab.example.edu",
    )

    with patch(
        "src.agents.lab_research.scrape_lab_website",
        new=AsyncMock(side_effect=Exception("Network error")),
    ):
        # Act
        lab = await process_single_lab(professor, "test-correlation-id")

        # Assert
        assert lab.professor_id == "prof3"
        assert lab.lab_url == "https://mathlab.example.edu"
        assert "scraping_failed" in lab.data_quality_flags


@pytest.mark.asyncio
async def test_discover_and_scrape_labs_batch_no_professors():
    """Test batch orchestrator with no professors."""
    # Arrange
    with patch("src.agents.lab_research.CheckpointManager") as mock_checkpoint_manager:
        mock_cm_instance = MagicMock()
        mock_cm_instance.get_resume_point.return_value = 1
        mock_cm_instance.load_batches.side_effect = FileNotFoundError()
        mock_checkpoint_manager.return_value = mock_cm_instance

        # Act
        labs = await discover_and_scrape_labs_batch()

        # Assert
        assert labs == []


@pytest.mark.asyncio
async def test_discover_and_scrape_labs_batch_with_professors(mocker):
    """Test batch orchestrator with mock professors."""
    # Arrange
    mock_professors = [
        {
            "id": "prof1",
            "name": "Dr. Alice",
            "title": "Professor",
            "department_id": "dept1",
            "department_name": "CS",
            "profile_url": "https://cs.edu/alice",
            "lab_url": "https://alicelab.edu",
            "is_relevant": True,
            "relevance_confidence": 90,
            "relevance_reasoning": "Test",
        },
        {
            "id": "prof2",
            "name": "Dr. Bob",
            "title": "Professor",
            "department_id": "dept2",
            "department_name": "Physics",
            "profile_url": "https://physics.edu/bob",
            "lab_url": None,
            "is_relevant": True,
            "relevance_confidence": 85,
            "relevance_reasoning": "Test",
        },
    ]

    mock_scraped_data = {
        "description": "Test lab",
        "news_updates": [],
        "last_updated": None,
        "contact_emails": ["test@lab.edu"],
        "contact_form_url": None,
        "application_url": None,
        "lab_members": ["PI Name"],
        "research_focus": ["AI"],
        "publications_list": [],
        "website_content": "Content",
        "data_quality_flags": [],
    }

    # Mock checkpoint manager
    mock_cm = MagicMock()
    mock_cm.get_resume_point.return_value = 1
    mock_cm.load_batches.return_value = [[mock_professors[0]], [mock_professors[1]]]
    mock_cm.save_batch = MagicMock()

    with (
        patch("src.agents.lab_research.CheckpointManager", return_value=mock_cm),
        patch("src.agents.lab_research.SystemParams.load") as mock_system_params,
        patch(
            "src.agents.lab_research.scrape_lab_website",
            new=AsyncMock(return_value=mock_scraped_data),
        ),
        patch("src.utils.progress_tracker.ProgressTracker"),
    ):
        # Mock system params
        mock_params = MagicMock()
        mock_params.batch_config.lab_discovery_batch_size = 10
        mock_system_params.return_value = mock_params

        # Act
        labs = await discover_and_scrape_labs_batch()

        # Assert
        assert len(labs) == 2
        assert all(isinstance(lab, Lab) for lab in labs)
        assert mock_cm.save_batch.called


@pytest.mark.asyncio
async def test_discover_and_scrape_labs_batch_resume_from_checkpoint(mocker):
    """Test batch orchestrator resuming from checkpoint."""
    # Arrange
    existing_lab_data = {
        "id": "lab1",
        "professor_id": "prof1",
        "professor_name": "Dr. Alice",
        "department": "CS",
        "lab_name": "Alice Lab",
        "lab_url": "https://alicelab.edu",
        "last_updated": None,
        "description": "Existing lab",
        "research_focus": [],
        "news_updates": [],
        "website_content": "",
        "data_quality_flags": [],
    }

    new_professor_data = {
        "id": "prof2",
        "name": "Dr. Bob",
        "title": "Professor",
        "department_id": "dept2",
        "department_name": "Physics",
        "profile_url": "https://physics.edu/bob",
        "lab_url": "https://boblab.edu",
        "is_relevant": True,
        "relevance_confidence": 80,
        "relevance_reasoning": "Test",
    }

    # Mock checkpoint manager to return resume_batch_id=2
    mock_cm = MagicMock()
    mock_cm.get_resume_point.return_value = 2
    mock_cm.load_batches.side_effect = [
        [[existing_lab_data]],  # Existing labs
        [[new_professor_data]],  # All professors
    ]
    mock_cm.save_batch = MagicMock()

    mock_scraped_data = {
        "description": "Bob's lab",
        "news_updates": [],
        "last_updated": None,
        "contact_emails": [],
        "contact_form_url": None,
        "application_url": None,
        "lab_members": [],
        "research_focus": ["Physics"],
        "publications_list": [],
        "website_content": "Content",
        "data_quality_flags": [],
    }

    with (
        patch("src.agents.lab_research.CheckpointManager", return_value=mock_cm),
        patch("src.agents.lab_research.SystemParams.load") as mock_system_params,
        patch(
            "src.agents.lab_research.scrape_lab_website",
            new=AsyncMock(return_value=mock_scraped_data),
        ),
        patch("src.utils.progress_tracker.ProgressTracker"),
    ):
        # Mock system params with batch size 1 to ensure multiple batches
        mock_params = MagicMock()
        mock_params.batch_config.lab_discovery_batch_size = 1
        mock_system_params.return_value = mock_params

        # Act
        labs = await discover_and_scrape_labs_batch()

        # Assert
        # Should have 1 existing lab + 0 new labs (resume from batch 2, which is beyond total batches)
        assert len(labs) >= 1
        assert labs[0].description == "Existing lab"


@pytest.mark.asyncio
async def test_process_single_lab_extracts_five_categories(mocker):
    """Test that lab scraping extracts all 5 data categories per Story 4.1 v1.1."""
    # Arrange
    professor = Professor(
        id="prof5",
        name="Dr. Emily Zhang",
        title="Professor",
        department_id="dept5",
        department_name="Bioengineering",
        profile_url="https://bioeng.edu/ezhang",
        lab_url="https://zhanglab.bioeng.edu",
    )

    # Mock data with all 5 categories populated
    mock_scraped_data = {
        # Category 1: lab_information
        "description": "Synthetic biology and bioengineering research",
        "news_updates": ["NIH grant awarded", "New postdoc joined"],
        "last_updated": datetime(2025, 9, 15),
        # Category 2: contact
        "contact_emails": ["zhang@bioeng.edu", "lab@zhanglab.edu"],
        "contact_form_url": "https://zhanglab.bioeng.edu/contact",
        "application_url": "https://zhanglab.bioeng.edu/positions",
        # Category 3: people
        "lab_members": [
            "Dr. Emily Zhang (PI)",
            "Sarah Kim (Postdoc)",
            "Michael Chen (PhD Student)",
            "Lisa Wang (Research Assistant)",
        ],
        # Category 4: research_focus
        "research_focus": [
            "Synthetic Biology",
            "Gene Editing",
            "CRISPR Technologies",
            "Metabolic Engineering",
        ],
        # Category 5: publications
        "publications_list": [
            "Zhang et al. Nature 2025: CRISPR-based biosensors",
            "Kim & Zhang Cell 2024: Metabolic pathway optimization",
            "Chen et al. Science 2024: Synthetic gene circuits",
        ],
        # Other
        "website_content": "Full website text content for analysis",
        "data_quality_flags": [],
    }

    with patch(
        "src.agents.lab_research.scrape_lab_website",
        new=AsyncMock(return_value=mock_scraped_data),
    ):
        # Act
        lab = await process_single_lab(professor, "test-correlation-id")

        # Assert - Verify all 5 categories extracted
        # Category 1: lab_information
        assert lab.description == "Synthetic biology and bioengineering research"
        assert len(lab.news_updates) == 2
        assert "NIH grant awarded" in lab.news_updates
        assert lab.last_updated == datetime(2025, 9, 15)

        # Category 2: contact
        assert len(lab.contact_emails) == 2
        assert "zhang@bioeng.edu" in lab.contact_emails
        assert lab.contact_form_url == "https://zhanglab.bioeng.edu/contact"
        assert lab.application_url == "https://zhanglab.bioeng.edu/positions"

        # Category 3: people
        assert len(lab.lab_members) == 4
        assert "Dr. Emily Zhang (PI)" in lab.lab_members
        assert "Michael Chen (PhD Student)" in lab.lab_members

        # Category 4: research_focus
        assert len(lab.research_focus) == 4
        assert "Synthetic Biology" in lab.research_focus
        assert "CRISPR Technologies" in lab.research_focus

        # Category 5: publications
        assert len(lab.publications_list) == 3
        assert any("Nature 2025" in pub for pub in lab.publications_list)

        # Data quality flags: archive data will be added from Story 4.2
        # Only 'no_archive_data' expected since archive.org integration runs
        assert "no_archive_data" in lab.data_quality_flags or lab.data_quality_flags == []
