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
        "description": "Vision research lab",
        "research_focus": ["Computer Vision", "ML"],
        "news_updates": ["New paper"],
        "website_content": "Full content",
        "last_updated": datetime(2025, 10, 1),
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
    with patch(
        "src.agents.lab_research.CheckpointManager"
    ) as mock_checkpoint_manager:
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
        "research_focus": ["AI"],
        "news_updates": [],
        "website_content": "Content",
        "last_updated": None,
        "data_quality_flags": [],
    }

    # Mock checkpoint manager
    mock_cm = MagicMock()
    mock_cm.get_resume_point.return_value = 1
    mock_cm.load_batches.return_value = [[mock_professors[0]], [mock_professors[1]]]
    mock_cm.save_batch = MagicMock()

    with patch(
        "src.agents.lab_research.CheckpointManager", return_value=mock_cm
    ), patch(
        "src.agents.lab_research.SystemParams.load"
    ) as mock_system_params, patch(
        "src.agents.lab_research.scrape_lab_website",
        new=AsyncMock(return_value=mock_scraped_data),
    ), patch(
        "src.utils.progress_tracker.ProgressTracker"
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
        "research_focus": ["Physics"],
        "news_updates": [],
        "website_content": "Content",
        "last_updated": None,
        "data_quality_flags": [],
    }

    with patch(
        "src.agents.lab_research.CheckpointManager", return_value=mock_cm
    ), patch(
        "src.agents.lab_research.SystemParams.load"
    ) as mock_system_params, patch(
        "src.agents.lab_research.scrape_lab_website",
        new=AsyncMock(return_value=mock_scraped_data),
    ), patch(
        "src.utils.progress_tracker.ProgressTracker"
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
