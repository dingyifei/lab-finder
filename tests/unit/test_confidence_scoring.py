"""
Test suite for Story 3.3: Confidence Scoring for Filtering Decisions

Tests cover:
- Task 1: Confidence threshold configuration loading
- Task 2: LLM prompt enhancements (verified via integration)
- Task 3: Data quality flags
- Task 4: Confidence score parsing and validation
- Task 5: Low-confidence identification
- Task 6: Borderline report generation
- Task 7: Confidence statistics calculation
- Task 8: Stats report saving
- Task 9: Manual overrides application

Coverage: Confidence parsing, threshold checking, borderline identification,
stats calculation, edge case handling
"""

import json
import pytest
from unittest.mock import Mock, patch

from src.agents.professor_filter import (
    validate_confidence_score,
    calculate_confidence_stats,
    generate_borderline_report,
    save_confidence_stats_report,
    apply_manual_overrides,
    _get_override_recommendation,
)
from src.models.config import FilteringConfig
from src.models.professor import Professor, PROFESSOR_DATA_QUALITY_FLAGS


# ============================================================================
# Task 1: Configuration Tests
# ============================================================================


def test_filtering_config_defaults():
    """Test FilteringConfig default values."""
    config = FilteringConfig()

    assert config.low_confidence_threshold == 70
    assert config.high_confidence_threshold == 90
    assert config.borderline_review_enabled is True


def test_filtering_config_validation_valid():
    """Test FilteringConfig accepts valid threshold ordering."""
    config = FilteringConfig(low_confidence_threshold=60, high_confidence_threshold=85)

    assert config.low_confidence_threshold == 60
    assert config.high_confidence_threshold == 85


def test_filtering_config_validation_invalid_ordering():
    """Test FilteringConfig rejects invalid threshold ordering (low >= high)."""
    with pytest.raises(ValueError, match="must be greater than"):
        FilteringConfig(low_confidence_threshold=90, high_confidence_threshold=80)


def test_filtering_config_validation_equal_thresholds():
    """Test FilteringConfig rejects equal thresholds."""
    with pytest.raises(ValueError, match="must be greater than"):
        FilteringConfig(low_confidence_threshold=70, high_confidence_threshold=70)


def test_filtering_config_validation_out_of_range():
    """Test FilteringConfig rejects out-of-range values."""
    with pytest.raises(ValueError):
        FilteringConfig(low_confidence_threshold=0, high_confidence_threshold=101)


# ============================================================================
# Task 3: Data Quality Flags Tests
# ============================================================================


def test_professor_data_quality_flags_include_confidence_flags():
    """Test PROFESSOR_DATA_QUALITY_FLAGS includes new confidence-related flags."""
    assert "low_confidence_filter" in PROFESSOR_DATA_QUALITY_FLAGS
    assert "llm_response_error" in PROFESSOR_DATA_QUALITY_FLAGS
    assert "manual_override" in PROFESSOR_DATA_QUALITY_FLAGS
    assert "confidence_out_of_range" in PROFESSOR_DATA_QUALITY_FLAGS


def test_professor_add_quality_flag_valid():
    """Test Professor.add_quality_flag() accepts valid confidence flags."""
    prof = Professor(
        id="test-1",
        name="Dr. Test",
        title="Professor",
        department_id="dept-1",
        department_name="Computer Science",
        profile_url="https://example.edu/test",
    )

    prof.add_quality_flag("low_confidence_filter")
    prof.add_quality_flag("manual_override")

    assert "low_confidence_filter" in prof.data_quality_flags
    assert "manual_override" in prof.data_quality_flags


# ============================================================================
# Task 4: Confidence Validation Tests
# ============================================================================


def test_validate_confidence_score_valid_int():
    """Test confidence validation accepts valid integer."""
    confidence, flags = validate_confidence_score(85, "Dr. Test", "test-corr")

    assert confidence == 85
    assert flags == []


def test_validate_confidence_score_valid_float():
    """Test confidence validation converts float to int via rounding."""
    confidence, flags = validate_confidence_score(85.7, "Dr. Test", "test-corr")

    assert confidence == 86
    assert flags == []


def test_validate_confidence_score_float_rounding_down():
    """Test float-to-int conversion rounds correctly (down)."""
    confidence, flags = validate_confidence_score(85.4, "Dr. Test", "test-corr")

    assert confidence == 85
    assert flags == []


def test_validate_confidence_score_string_numeric():
    """Test confidence validation converts numeric string."""
    confidence, flags = validate_confidence_score("92", "Dr. Test", "test-corr")

    assert confidence == 92
    assert flags == []


def test_validate_confidence_score_string_float():
    """Test confidence validation converts float string."""
    confidence, flags = validate_confidence_score("88.5", "Dr. Test", "test-corr")

    assert confidence == 88  # rounds down
    assert flags == []


def test_validate_confidence_score_invalid_type():
    """Test confidence validation handles invalid types with neutral default."""
    confidence, flags = validate_confidence_score(None, "Dr. Test", "test-corr")

    assert confidence == 50
    assert "llm_response_error" in flags


def test_validate_confidence_score_invalid_string():
    """Test confidence validation handles non-numeric string."""
    confidence, flags = validate_confidence_score("invalid", "Dr. Test", "test-corr")

    assert confidence == 50
    assert "llm_response_error" in flags


def test_validate_confidence_score_negative():
    """Test confidence validation clamps negative values to 0."""
    confidence, flags = validate_confidence_score(-10, "Dr. Test", "test-corr")

    assert confidence == 0
    assert "confidence_out_of_range" in flags


def test_validate_confidence_score_exceeds_100():
    """Test confidence validation clamps values >100."""
    confidence, flags = validate_confidence_score(150, "Dr. Test", "test-corr")

    assert confidence == 100
    assert "confidence_out_of_range" in flags


def test_validate_confidence_score_boolean():
    """Test confidence validation rejects boolean type."""
    confidence, flags = validate_confidence_score(True, "Dr. Test", "test-corr")

    assert confidence == 50
    assert "llm_response_error" in flags


# ============================================================================
# Task 5: Low-Confidence Identification (tested via integration)
# ============================================================================

# Low-confidence identification is tested implicitly through filter_professor_single
# integration tests and borderline report tests


# ============================================================================
# Task 6: Borderline Report Tests
# ============================================================================


@pytest.fixture
def mock_professors():
    """Create mock professors with varying confidence levels."""
    return [
        Professor(
            id="prof-1",
            name="Dr. High Confidence",
            title="Professor",
            department_id="dept-1",
            department_name="CS",
            profile_url="https://example.edu/high",
            is_relevant=True,
            relevance_confidence=95,
            relevance_reasoning="Strong match",
            research_areas=["AI", "ML"],
        ),
        Professor(
            id="prof-2",
            name="Dr. Low Included",
            title="Professor",
            department_id="dept-1",
            department_name="CS",
            profile_url="https://example.edu/low-inc",
            is_relevant=True,
            relevance_confidence=65,
            relevance_reasoning="Tangential overlap",
            research_areas=["HCI"],
        ),
        Professor(
            id="prof-3",
            name="Dr. Low Excluded",
            title="Professor",
            department_id="dept-2",
            department_name="Math",
            profile_url="https://example.edu/low-exc",
            is_relevant=False,
            relevance_confidence=55,
            relevance_reasoning="Weak connection",
            research_areas=["Statistics"],
        ),
    ]


@patch("src.agents.professor_filter.SystemParams.load")
def test_generate_borderline_report_creates_file(
    mock_load, mock_professors, tmp_path, monkeypatch
):
    """Test borderline report file creation."""
    # Mock SystemParams with filtering config
    mock_config = Mock()
    mock_config.filtering_config.low_confidence_threshold = 70
    mock_load.return_value = mock_config

    # Change output directory to tmp_path
    monkeypatch.chdir(tmp_path)

    generate_borderline_report(mock_professors)

    report_path = tmp_path / "output" / "borderline-professors.md"
    assert report_path.exists()


@patch("src.agents.professor_filter.SystemParams.load")
def test_generate_borderline_report_content(
    mock_load, mock_professors, tmp_path, monkeypatch
):
    """Test borderline report includes correct professors."""
    # Mock SystemParams
    mock_config = Mock()
    mock_config.filtering_config.low_confidence_threshold = 70
    mock_load.return_value = mock_config

    monkeypatch.chdir(tmp_path)

    generate_borderline_report(mock_professors)

    report_path = tmp_path / "output" / "borderline-professors.md"
    content = report_path.read_text()

    # Should include low-confidence professors
    assert "Dr. Low Included" in content
    assert "Dr. Low Excluded" in content

    # Should NOT include high-confidence professor
    assert "Dr. High Confidence" not in content

    # Should have summary stats
    assert "Total Borderline Cases:** 2" in content
    assert "1 included (low confidence)" in content
    assert "1 excluded (low confidence)" in content


@patch("src.agents.professor_filter.SystemParams.load")
def test_generate_borderline_report_no_borderline_cases(
    mock_load, tmp_path, monkeypatch
):
    """Test borderline report skips generation when no borderline cases."""
    # Mock SystemParams
    mock_config = Mock()
    mock_config.filtering_config.low_confidence_threshold = 70
    mock_load.return_value = mock_config

    monkeypatch.chdir(tmp_path)

    # All high confidence
    professors = [
        Professor(
            id="prof-1",
            name="Dr. High",
            title="Professor",
            department_id="dept-1",
            department_name="CS",
            profile_url="https://example.edu/high",
            is_relevant=True,
            relevance_confidence=95,
            relevance_reasoning="Strong",
        ),
    ]

    generate_borderline_report(professors)

    report_path = tmp_path / "output" / "borderline-professors.md"
    assert not report_path.exists()  # Should skip creation


def test_get_override_recommendation_interdisciplinary():
    """Test override recommendation detects interdisciplinary keywords."""
    recommendation = _get_override_recommendation(
        "Professor works in interdisciplinary field", is_relevant=True
    )
    assert "interdisciplinary" in recommendation.lower()


def test_get_override_recommendation_emerging():
    """Test override recommendation detects emerging field keywords."""
    recommendation = _get_override_recommendation(
        "Research in emerging AI methods", is_relevant=False
    )
    assert "emerging field" in recommendation.lower()


def test_get_override_recommendation_tangential():
    """Test override recommendation handles tangential matches."""
    recommendation = _get_override_recommendation(
        "Tangential overlap with user interests", is_relevant=True
    )
    assert "tangential" in recommendation.lower()


# ============================================================================
# Task 7: Confidence Statistics Tests
# ============================================================================


def test_calculate_confidence_stats_distribution(mock_professors):
    """Test confidence stats calculate correct distribution."""
    stats = calculate_confidence_stats(mock_professors)

    assert stats["total_professors"] == 3
    assert stats["included"]["total"] == 2
    assert stats["excluded"]["total"] == 1

    # Check categorization (low < 70, medium 70-89, high >= 90)
    assert stats["included"]["high"] == 1  # prof-1: 95
    assert stats["included"]["medium"] == 0
    assert stats["included"]["low"] == 1  # prof-2: 65

    assert stats["excluded"]["low"] == 1  # prof-3: 55


def test_calculate_confidence_stats_quality_assessment(mock_professors):
    """Test confidence stats provide quality assessment."""
    stats = calculate_confidence_stats(mock_professors)

    analysis = stats["distribution_analysis"]

    assert "low_confidence_percentage" in analysis
    assert "expected_range" in analysis
    assert "quality_assessment" in analysis

    # 2 out of 3 = 66.7% low confidence
    assert analysis["low_confidence_percentage"] == 66.7


def test_calculate_confidence_stats_high_low_confidence_warning():
    """Test warning logged when >30% low confidence."""
    # Create professors with >30% low confidence
    professors = [
        Professor(
            id=f"prof-{i}",
            name=f"Dr. Test {i}",
            title="Professor",
            department_id="dept-1",
            department_name="CS",
            profile_url=f"https://example.edu/{i}",
            is_relevant=True,
            relevance_confidence=50 if i < 7 else 95,  # 70% low confidence
        )
        for i in range(10)
    ]

    stats = calculate_confidence_stats(professors)

    analysis = stats["distribution_analysis"]
    assert analysis["low_confidence_percentage"] == 70.0
    assert "Warning" in analysis["quality_assessment"]


# ============================================================================
# Task 8: Stats Report Saving Tests
# ============================================================================


def test_save_confidence_stats_report_creates_file(tmp_path, monkeypatch):
    """Test confidence stats report file creation."""
    monkeypatch.chdir(tmp_path)

    stats = {
        "total_professors": 100,
        "included": {"total": 60, "high": 40, "medium": 15, "low": 5},
        "excluded": {"total": 40, "high": 30, "medium": 8, "low": 2},
        "distribution_analysis": {
            "low_confidence_percentage": 7.0,
            "expected_range": "10-20%",
            "deviation_from_expected": "Within range",
            "quality_assessment": "Good",
        },
    }

    save_confidence_stats_report(stats)

    report_path = tmp_path / "output" / "filter-confidence-stats.json"
    assert report_path.exists()


def test_save_confidence_stats_report_content(tmp_path, monkeypatch):
    """Test confidence stats report has correct JSON structure."""
    monkeypatch.chdir(tmp_path)

    stats = {
        "total_professors": 50,
        "included": {"total": 30, "high": 20, "medium": 8, "low": 2},
        "excluded": {"total": 20, "high": 15, "medium": 4, "low": 1},
        "distribution_analysis": {
            "low_confidence_percentage": 6.0,
            "quality_assessment": "Good",
        },
    }

    save_confidence_stats_report(stats)

    report_path = tmp_path / "output" / "filter-confidence-stats.json"
    saved_data = json.loads(report_path.read_text())

    assert saved_data["total_professors"] == 50
    assert saved_data["included"]["high"] == 20
    assert saved_data["distribution_analysis"]["low_confidence_percentage"] == 6.0


# ============================================================================
# Task 9: Manual Overrides Tests
# ============================================================================


def test_apply_manual_overrides_no_file(tmp_path, monkeypatch):
    """Test manual overrides gracefully skips when no file exists."""
    monkeypatch.chdir(tmp_path)

    professors = [
        Professor(
            id="prof-1",
            name="Dr. Test",
            title="Professor",
            department_id="dept-1",
            department_name="CS",
            profile_url="https://example.edu/test",
            is_relevant=True,
            relevance_confidence=85,
        ),
    ]

    override_count = apply_manual_overrides(professors)

    assert override_count == 0
    assert professors[0].is_relevant is True  # Unchanged


def test_apply_manual_overrides_valid(tmp_path, monkeypatch):
    """Test manual overrides apply correctly."""
    monkeypatch.chdir(tmp_path)

    # Create config directory and override file
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    override_data = {
        "professor_overrides": [
            {
                "professor_id": "prof-1",
                "decision": "exclude",
                "reason": "Not relevant after review",
                "timestamp": "2025-10-08T12:00:00Z",
                "original_confidence": 65,
                "original_decision": "include",
            }
        ]
    }

    (config_dir / "manual-overrides.json").write_text(json.dumps(override_data))

    professors = [
        Professor(
            id="prof-1",
            name="Dr. Test",
            title="Professor",
            department_id="dept-1",
            department_name="CS",
            profile_url="https://example.edu/test",
            is_relevant=True,
            relevance_confidence=65,
            relevance_reasoning="Original reasoning",
        ),
    ]

    override_count = apply_manual_overrides(professors)

    assert override_count == 1
    assert professors[0].is_relevant is False  # Changed to exclude
    assert "manual_override" in professors[0].data_quality_flags
    assert "MANUAL OVERRIDE" in professors[0].relevance_reasoning
    assert "Not relevant after review" in professors[0].relevance_reasoning


def test_apply_manual_overrides_invalid_professor_id(tmp_path, monkeypatch):
    """Test manual overrides skip non-existent professor IDs."""
    monkeypatch.chdir(tmp_path)

    config_dir = tmp_path / "config"
    config_dir.mkdir()

    override_data = {
        "professor_overrides": [
            {
                "professor_id": "non-existent",
                "decision": "exclude",
                "reason": "Test",
            }
        ]
    }

    (config_dir / "manual-overrides.json").write_text(json.dumps(override_data))

    professors = [
        Professor(
            id="prof-1",
            name="Dr. Test",
            title="Professor",
            department_id="dept-1",
            department_name="CS",
            profile_url="https://example.edu/test",
            is_relevant=True,
            relevance_confidence=85,
        ),
    ]

    override_count = apply_manual_overrides(professors)

    assert override_count == 0  # Should skip invalid ID


def test_apply_manual_overrides_malformed_json(tmp_path, monkeypatch):
    """Test manual overrides handle malformed JSON gracefully."""
    monkeypatch.chdir(tmp_path)

    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Write invalid JSON
    (config_dir / "manual-overrides.json").write_text("{invalid json")

    professors = [
        Professor(
            id="prof-1",
            name="Dr. Test",
            title="Professor",
            department_id="dept-1",
            department_name="CS",
            profile_url="https://example.edu/test",
            is_relevant=True,
            relevance_confidence=85,
        ),
    ]

    override_count = apply_manual_overrides(professors)

    assert override_count == 0
