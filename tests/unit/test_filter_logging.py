"""Unit tests for Story 3.4: Filtered Professor Logging & Transparency.

Tests reporting-specific functions:
- log_filter_decision()
- calculate_filter_statistics()
- generate_filter_report()
- load_manual_additions()
- apply_manual_additions()
"""

import json
import pytest
from src.agents.professor_reporting import (
    log_filter_decision,
    calculate_filter_statistics,
    generate_filter_report,
    load_manual_additions,
    apply_manual_additions,
)
from src.models.professor import Professor


# Fixtures


@pytest.fixture
def sample_professor_included():
    """Create sample professor marked as included."""
    return Professor(
        id="prof-1",
        name="Dr. Alice Smith",
        title="Professor",
        department_id="cs-1",
        department_name="Computer Science",
        school="Engineering",
        profile_url="https://example.edu/alice",
        research_areas=["Machine Learning", "AI"],
        is_relevant=True,
        relevance_confidence=95,
        relevance_reasoning="Strong match with user's ML interests",
    )


@pytest.fixture
def sample_professor_excluded():
    """Create sample professor marked as excluded."""
    return Professor(
        id="prof-2",
        name="Dr. Bob Johnson",
        title="Associate Professor",
        department_id="lit-1",
        department_name="Literature",
        school="Arts & Sciences",
        profile_url="https://example.edu/bob",
        research_areas=["Poetry", "Renaissance Literature"],
        is_relevant=False,
        relevance_confidence=98,
        relevance_reasoning="No overlap with user's technical interests",
    )


@pytest.fixture
def sample_professors_mixed(sample_professor_included, sample_professor_excluded):
    """Create mixed list of included and excluded professors."""
    # Create additional professors for more realistic testing
    prof3 = Professor(
        id="prof-3",
        name="Dr. Carol Davis",
        title="Assistant Professor",
        department_id="cs-1",
        department_name="Computer Science",
        school="Engineering",
        profile_url="https://example.edu/carol",
        research_areas=["Computer Vision"],
        is_relevant=True,
        relevance_confidence=85,
        relevance_reasoning="Moderate match with user's CV interests",
    )

    prof4 = Professor(
        id="prof-4",
        name="Dr. David Lee",
        title="Professor",
        department_id="bio-1",
        department_name="Biology",
        school="Sciences",
        profile_url="https://example.edu/david",
        research_areas=["Ecology", "Environmental Science"],
        is_relevant=False,
        relevance_confidence=75,
        relevance_reasoning="Minimal overlap with computational focus",
    )

    return [sample_professor_included, sample_professor_excluded, prof3, prof4]


# Test 1: Filter Decision Logging


def test_log_filter_decision(sample_professor_included, mocker):
    """Test filter decision logging to structlog.

    Story 3.4: Task 1
    """
    # Arrange
    mock_logger = mocker.patch("src.agents.professor_reporting.get_logger")
    mock_logger_instance = mock_logger.return_value

    # Act
    log_filter_decision(sample_professor_included, "test-corr-id")

    # Assert
    mock_logger.assert_called_once_with(
        correlation_id="test-corr-id",
        phase="professor_filtering",
        component="professor_reporting",
    )

    # Verify logging call with expected fields
    mock_logger_instance.info.assert_called_once()
    call_args = mock_logger_instance.info.call_args

    assert call_args[0][0] == "Filter decision logged"
    assert call_args[1]["professor_id"] == "prof-1"
    assert call_args[1]["professor_name"] == "Dr. Alice Smith"
    assert call_args[1]["decision"] == "include"
    assert call_args[1]["is_relevant"] is True
    assert call_args[1]["relevance_confidence"] == 95


# Test 2: Filtered-professors.md Report Generation


@pytest.mark.asyncio
async def test_generate_filter_report(tmp_path, sample_professors_mixed, mocker):
    """Test filtered-professors.md report generation.

    Story 3.4: Task 2
    """
    # Arrange
    mocker.patch("src.agents.professor_reporting.get_logger")

    # Act
    await generate_filter_report(sample_professors_mixed, str(tmp_path), "test-corr-id")

    # Assert
    report_path = tmp_path / "filtered-professors.md"
    assert report_path.exists()

    content = report_path.read_text(encoding="utf-8")

    # Check key sections
    assert "# Filtered Professors Report" in content
    assert "## Executive Summary" in content
    assert "## Filtering Statistics by Department" in content
    assert "## Excluded Professors" in content
    assert "## Included Professors Summary" in content
    assert "## How to Override Filter Decisions" in content

    # Check statistics (with markdown bold formatting)
    assert "**Total Professors Evaluated:** 4" in content
    assert "**Included for Analysis:** 2" in content
    assert "**Excluded:** 2" in content

    # Check professor names appear
    assert "Dr. Alice Smith" in content
    assert "Dr. Bob Johnson" in content


# Test 3: Filtering Statistics Calculation


def test_calculate_filter_statistics(sample_professors_mixed):
    """Test filtering statistics calculation.

    Story 3.4: Task 4
    """
    # Act
    stats = calculate_filter_statistics(sample_professors_mixed)

    # Assert
    assert stats["total"] == 4
    assert stats["included"]["count"] == 2
    assert stats["included"]["percentage"] == 50.0
    assert stats["excluded"]["count"] == 2
    assert stats["excluded"]["percentage"] == 50.0

    # Check confidence breakdown
    assert stats["included"]["high_confidence"] == 1  # Dr. Alice (95)
    assert stats["included"]["medium_confidence"] == 1  # Dr. Carol (85)
    assert stats["excluded"]["high_confidence"] == 1  # Dr. Bob (98)
    assert stats["excluded"]["medium_confidence"] == 1  # Dr. David (75)


# Test 4: Manual Professor Addition Loading


@pytest.mark.asyncio
async def test_load_manual_additions(tmp_path):
    """Test manual professor addition loading.

    Story 3.4: Task 5
    """
    # Arrange
    additions_file = tmp_path / "manual-professor-additions.json"
    additions_data = {
        "additions": [
            {"professor_id": "prof-123", "reason": "User identified as relevant"}
        ]
    }

    with open(additions_file, "w") as f:
        json.dump(additions_data, f)

    # Act
    result = await load_manual_additions(str(additions_file))

    # Assert
    assert "additions" in result
    assert len(result["additions"]) == 1
    assert result["additions"][0]["professor_id"] == "prof-123"


# Test 5: Cross-Referencing with Borderline Cases


@pytest.mark.asyncio
async def test_cross_reference_borderline_report(tmp_path, sample_professors_mixed):
    """Test cross-referencing with borderline-professors.md.

    Story 3.4: Task 7
    """
    # Arrange - Create borderline report
    borderline_file = tmp_path / "borderline-professors.md"
    borderline_file.write_text("# Borderline Professors\nSample content")

    # Act
    await generate_filter_report(sample_professors_mixed, str(tmp_path), "test-corr-id")

    # Assert
    report_path = tmp_path / "filtered-professors.md"
    content = report_path.read_text(encoding="utf-8")

    # Check cross-reference exists
    assert "borderline-professors.md" in content
    assert "low-confidence" in content.lower()


# Test 6: Report Formatting (Markdown Validity)


@pytest.mark.asyncio
async def test_report_markdown_formatting(tmp_path, sample_professors_mixed):
    """Test report markdown formatting is valid.

    Story 3.4: Task 2
    """
    # Act
    await generate_filter_report(sample_professors_mixed, str(tmp_path), "test-corr-id")

    # Assert
    report_path = tmp_path / "filtered-professors.md"
    content = report_path.read_text(encoding="utf-8")

    # Check markdown table formatting
    assert "| Professor | Department |" in content
    assert "|-----------|------------|" in content

    # Check markdown headers
    assert content.count("##") >= 5  # Multiple section headers
    assert content.count("###") >= 2  # Subsection headers

    # Check code block formatting
    assert "```json" in content
    assert "```" in content


# Test 7: Manual Professor Addition Application


@pytest.mark.asyncio
async def test_apply_manual_additions(sample_professor_excluded, tmp_path, mocker):
    """Test applying manual additions to professor list.

    Story 3.4: Task 5
    """
    # Arrange
    professors = [sample_professor_excluded]
    additions = {
        "additions": [
            {
                "professor_id": "prof-2",
                "reason": "User identified as relevant despite filter",
            }
        ]
    }

    # Mock checkpoint manager
    mocker.patch("src.agents.professor_reporting.CheckpointManager")

    # Act
    result = await apply_manual_additions(professors, additions, "test-corr-id")

    # Assert
    assert len(result) == 1
    assert result[0].is_relevant is True  # Changed from False to True
    assert "manual_addition" in result[0].data_quality_flags
    assert "MANUAL ADDITION" in result[0].relevance_reasoning


# Edge Case Tests (Subtasks 8.1, 8.2, 8.3)


# Subtask 8.1: All Professors Included


def test_calculate_stats_all_included():
    """Test edge case: all professors included.

    Story 3.4: Task 8, Subtask 8.1
    """
    # Arrange
    professors = [
        Professor(
            id=f"prof-{i}",
            name=f"Dr. Professor {i}",
            title="Professor",
            department_id="cs-1",
            department_name="Computer Science",
            profile_url=f"https://example.edu/prof{i}",
            research_areas=["AI"],
            is_relevant=True,
            relevance_confidence=95,
            relevance_reasoning="Matches user interests",
        )
        for i in range(5)
    ]

    # Act
    stats = calculate_filter_statistics(professors)

    # Assert
    assert stats["total"] == 5
    assert stats["included"]["count"] == 5
    assert stats["included"]["percentage"] == 100.0
    assert stats["excluded"]["count"] == 0
    assert stats["excluded"]["percentage"] == 0.0


@pytest.mark.asyncio
async def test_report_all_included(tmp_path):
    """Test report generation when all professors included.

    Story 3.4: Task 8, Subtask 8.1
    """
    # Arrange
    professors = [
        Professor(
            id=f"prof-{i}",
            name=f"Dr. Professor {i}",
            title="Professor",
            department_id="cs-1",
            department_name="Computer Science",
            profile_url=f"https://example.edu/prof{i}",
            research_areas=["AI"],
            is_relevant=True,
            relevance_confidence=95,
            relevance_reasoning="Matches",
        )
        for i in range(3)
    ]

    # Act
    await generate_filter_report(professors, str(tmp_path), "test-corr-id")

    # Assert
    report_path = tmp_path / "filtered-professors.md"
    content = report_path.read_text(encoding="utf-8")

    assert "**Included for Analysis:** 3 (100.0%)" in content
    assert "**Excluded:** 0 (0.0%)" in content
    assert "*No high-confidence exclusions.*" in content


# Subtask 8.2: All Professors Excluded


def test_calculate_stats_all_excluded():
    """Test edge case: all professors excluded.

    Story 3.4: Task 8, Subtask 8.2
    """
    # Arrange
    professors = [
        Professor(
            id=f"prof-{i}",
            name=f"Dr. Professor {i}",
            title="Professor",
            department_id="lit-1",
            department_name="Literature",
            profile_url=f"https://example.edu/prof{i}",
            research_areas=["Poetry"],
            is_relevant=False,
            relevance_confidence=95,
            relevance_reasoning="No match",
        )
        for i in range(5)
    ]

    # Act
    stats = calculate_filter_statistics(professors)

    # Assert
    assert stats["total"] == 5
    assert stats["included"]["count"] == 0
    assert stats["included"]["percentage"] == 0.0
    assert stats["excluded"]["count"] == 5
    assert stats["excluded"]["percentage"] == 100.0


@pytest.mark.asyncio
async def test_report_all_excluded(tmp_path):
    """Test report generation when all professors excluded.

    Story 3.4: Task 8, Subtask 8.2
    """
    # Arrange
    professors = [
        Professor(
            id=f"prof-{i}",
            name=f"Dr. Professor {i}",
            title="Professor",
            department_id="lit-1",
            department_name="Literature",
            profile_url=f"https://example.edu/prof{i}",
            research_areas=["Poetry"],
            is_relevant=False,
            relevance_confidence=95,
            relevance_reasoning="No match",
        )
        for i in range(3)
    ]

    # Act
    await generate_filter_report(professors, str(tmp_path), "test-corr-id")

    # Assert
    report_path = tmp_path / "filtered-professors.md"
    content = report_path.read_text(encoding="utf-8")

    assert "**Included for Analysis:** 0 (0.0%)" in content
    assert "**Excluded:** 3 (100.0%)" in content
    assert "*No high-confidence inclusions.*" in content


# Subtask 8.3: Empty Professor List


def test_calculate_stats_empty_list():
    """Test edge case: empty professor list.

    Story 3.4: Task 8, Subtask 8.3
    """
    # Arrange
    professors = []

    # Act
    stats = calculate_filter_statistics(professors)

    # Assert
    assert stats["total"] == 0
    assert stats["included"]["count"] == 0
    assert stats["included"]["percentage"] == 0.0
    assert stats["excluded"]["count"] == 0
    assert stats["excluded"]["percentage"] == 0.0

    # Verify no division-by-zero errors
    assert stats["included"]["high_confidence"] == 0
    assert stats["excluded"]["high_confidence"] == 0


@pytest.mark.asyncio
async def test_report_empty_list(tmp_path):
    """Test report generation with empty professor list.

    Story 3.4: Task 8, Subtask 8.3
    """
    # Arrange
    professors = []

    # Act
    await generate_filter_report(professors, str(tmp_path), "test-corr-id")

    # Assert
    report_path = tmp_path / "filtered-professors.md"
    assert report_path.exists()

    content = report_path.read_text(encoding="utf-8")

    # Verify statistics show 0 total professors
    assert "**Total Professors Evaluated:** 0" in content

    # Verify no division-by-zero errors in report
    assert "0.0%" in content or "0 (" in content


# Test Manual Additions: File Not Found


@pytest.mark.asyncio
async def test_load_manual_additions_file_not_found():
    """Test loading manual additions when file doesn't exist.

    Story 3.4: Task 5
    """
    # Act
    result = await load_manual_additions("nonexistent-file.json")

    # Assert
    assert result == {"additions": []}


# Test Manual Additions: Invalid JSON


@pytest.mark.asyncio
async def test_load_manual_additions_invalid_json(tmp_path):
    """Test loading manual additions with invalid JSON.

    Story 3.4: Task 5
    """
    # Arrange
    additions_file = tmp_path / "invalid.json"
    additions_file.write_text("{ invalid json content }")

    # Act
    result = await load_manual_additions(str(additions_file))

    # Assert
    assert result == {"additions": []}


# Test Manual Additions: No Matching Professor ID


@pytest.mark.asyncio
async def test_apply_manual_additions_no_match(sample_professor_included, mocker):
    """Test manual additions with non-matching professor ID.

    Story 3.4: Task 5
    """
    # Arrange
    professors = [sample_professor_included]
    additions = {"additions": [{"professor_id": "prof-999", "reason": "Test"}]}

    # Mock logger
    mocker.patch("src.agents.professor_reporting.get_logger")
    mocker.patch("src.agents.professor_reporting.CheckpointManager")

    # Act
    result = await apply_manual_additions(professors, additions, "test-corr-id")

    # Assert
    assert len(result) == 1
    assert result[0].is_relevant is True  # Unchanged
    assert "manual_addition" not in result[0].data_quality_flags


# Test Department-Level Statistics


@pytest.mark.asyncio
async def test_department_level_statistics(tmp_path):
    """Test department-level statistics in report.

    Story 3.4: Task 4
    """
    # Arrange
    professors = [
        Professor(
            id="prof-1",
            name="Dr. CS Prof 1",
            title="Professor",
            department_id="cs-1",
            department_name="Computer Science",
            profile_url="https://example.edu/cs1",
            research_areas=["AI"],
            is_relevant=True,
            relevance_confidence=95,
            relevance_reasoning="Match",
        ),
        Professor(
            id="prof-2",
            name="Dr. CS Prof 2",
            title="Professor",
            department_id="cs-1",
            department_name="Computer Science",
            profile_url="https://example.edu/cs2",
            research_areas=["ML"],
            is_relevant=True,
            relevance_confidence=90,
            relevance_reasoning="Match",
        ),
        Professor(
            id="prof-3",
            name="Dr. Lit Prof",
            title="Professor",
            department_id="lit-1",
            department_name="Literature",
            profile_url="https://example.edu/lit1",
            research_areas=["Poetry"],
            is_relevant=False,
            relevance_confidence=95,
            relevance_reasoning="No match",
        ),
    ]

    # Act
    await generate_filter_report(professors, str(tmp_path), "test-corr-id")

    # Assert
    report_path = tmp_path / "filtered-professors.md"
    content = report_path.read_text(encoding="utf-8")

    # Check department table exists
    assert "Computer Science" in content
    assert "Literature" in content

    # Verify inclusion rates
    # CS: 2/2 = 100%, Lit: 0/1 = 0%
    assert "100%" in content  # CS inclusion rate
