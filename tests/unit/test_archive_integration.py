"""
Unit tests for Archive.org integration (Story 4.2).

Tests:
1. query_wayback_snapshots with mocked API
2. Most recent snapshot identification
3. 3-year snapshot collection
4. Update frequency calculation (all categories)
5. Rate limiting enforcement
6. Missing archive data handling
7. API failure graceful degradation
8. Integration with Lab model enrichment
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from waybackpy.exceptions import NoCDXRecordFound

from src.agents.lab_research import (
    calculate_update_frequency,
    query_wayback_snapshots,
    enrich_with_archive_data,
)
from src.models.lab import Lab


# ============================================================================
# Task 8: Calculate Update Frequency Tests
# ============================================================================


def test_calculate_update_frequency_weekly():
    """Test weekly update frequency detection."""
    # Arrange - Snapshots with ~7-14 day intervals
    base_date = datetime(2025, 1, 1)
    snapshots = [
        base_date,
        base_date + timedelta(days=7),
        base_date + timedelta(days=14),
        base_date + timedelta(days=21),
    ]

    # Act
    frequency = calculate_update_frequency(snapshots)

    # Assert
    assert frequency == "weekly"


def test_calculate_update_frequency_monthly():
    """Test monthly update frequency detection."""
    # Arrange - Snapshots with ~30-60 day intervals
    base_date = datetime(2025, 1, 1)
    snapshots = [
        base_date,
        base_date + timedelta(days=45),
        base_date + timedelta(days=90),
        base_date + timedelta(days=140),
    ]

    # Act
    frequency = calculate_update_frequency(snapshots)

    # Assert
    assert frequency == "monthly"


def test_calculate_update_frequency_quarterly():
    """Test quarterly update frequency detection."""
    # Arrange - Snapshots with ~90-150 day intervals
    base_date = datetime(2025, 1, 1)
    snapshots = [
        base_date,
        base_date + timedelta(days=120),
        base_date + timedelta(days=240),
    ]

    # Act
    frequency = calculate_update_frequency(snapshots)

    # Assert
    assert frequency == "quarterly"


def test_calculate_update_frequency_yearly():
    """Test yearly update frequency detection."""
    # Arrange - Snapshots with ~180-365 day intervals
    base_date = datetime(2025, 1, 1)
    snapshots = [
        base_date,
        base_date + timedelta(days=200),
        base_date + timedelta(days=450),
    ]

    # Act
    frequency = calculate_update_frequency(snapshots)

    # Assert
    assert frequency == "yearly"


def test_calculate_update_frequency_stale():
    """Test stale update frequency detection."""
    # Arrange - Snapshots with >545 day intervals
    base_date = datetime(2025, 1, 1)
    snapshots = [
        base_date,
        base_date + timedelta(days=600),
        base_date + timedelta(days=1200),
    ]

    # Act
    frequency = calculate_update_frequency(snapshots)

    # Assert
    assert frequency == "stale"


def test_calculate_update_frequency_unknown_insufficient_data():
    """Test unknown frequency with <2 snapshots."""
    # Arrange - Only 1 snapshot
    snapshots = [datetime(2025, 1, 1)]

    # Act
    frequency = calculate_update_frequency(snapshots)

    # Assert
    assert frequency == "unknown"


def test_calculate_update_frequency_unknown_empty():
    """Test unknown frequency with empty snapshot list."""
    # Arrange
    snapshots = []

    # Act
    frequency = calculate_update_frequency(snapshots)

    # Assert
    assert frequency == "unknown"


# ============================================================================
# Task 5: query_wayback_snapshots Tests
# ============================================================================


@pytest.mark.asyncio
async def test_query_wayback_snapshots_success(mocker):
    """Test successful Wayback Machine API query."""
    # Arrange
    test_url = "https://example.edu/lab"
    correlation_id = "test-corr-id"

    # Mock snapshot objects
    mock_snapshot1 = Mock()
    mock_snapshot1.datetime_timestamp = datetime(2025, 1, 1)
    mock_snapshot1.archive_url = "https://web.archive.org/web/20250101/example.edu/lab"
    mock_snapshot1.original = test_url

    mock_snapshot2 = Mock()
    mock_snapshot2.datetime_timestamp = datetime(2024, 6, 1)
    mock_snapshot2.archive_url = "https://web.archive.org/web/20240601/example.edu/lab"
    mock_snapshot2.original = test_url

    # Mock WaybackMachineCDXServerAPI
    mock_cdx = Mock()
    mock_cdx.snapshots.return_value = [mock_snapshot1, mock_snapshot2]

    mocker.patch(
        "src.agents.lab_research.WaybackMachineCDXServerAPI",
        return_value=mock_cdx
    )

    # Mock rate limiter
    mock_rate_limiter = mocker.patch("src.agents.lab_research.rate_limiter")
    mock_rate_limiter.acquire = AsyncMock()

    # Act
    snapshots = await query_wayback_snapshots(test_url, correlation_id, years=3)

    # Assert
    assert len(snapshots) == 2
    assert snapshots[0]["datetime"] == datetime(2025, 1, 1)
    assert snapshots[1]["datetime"] == datetime(2024, 6, 1)
    assert "archive_url" in snapshots[0]
    assert "original_url" in snapshots[0]
    mock_rate_limiter.acquire.assert_called_once()


@pytest.mark.asyncio
async def test_query_wayback_snapshots_no_records(mocker):
    """Test handling of NoCDXRecordFound exception."""
    # Arrange
    test_url = "https://example.edu/newlab"
    correlation_id = "test-corr-id"

    # Mock WaybackMachineCDXServerAPI to raise NoCDXRecordFound
    mocker.patch(
        "src.agents.lab_research.WaybackMachineCDXServerAPI",
        side_effect=NoCDXRecordFound
    )

    # Mock rate limiter
    mock_rate_limiter = mocker.patch("src.agents.lab_research.rate_limiter")
    mock_rate_limiter.acquire = AsyncMock()

    # Act
    snapshots = await query_wayback_snapshots(test_url, correlation_id, years=3)

    # Assert
    assert snapshots == []
    mock_rate_limiter.acquire.assert_called_once()


@pytest.mark.asyncio
async def test_query_wayback_snapshots_rate_limiting(mocker):
    """Test that rate limiter is called before API request."""
    # Arrange
    test_url = "https://example.edu/lab"
    correlation_id = "test-corr-id"

    # Mock CDX API
    mock_cdx = Mock()
    mock_cdx.snapshots.return_value = []
    mocker.patch(
        "src.agents.lab_research.WaybackMachineCDXServerAPI",
        return_value=mock_cdx
    )

    # Mock rate limiter
    mock_rate_limiter = mocker.patch("src.agents.lab_research.rate_limiter")
    mock_rate_limiter.acquire = AsyncMock()

    # Act
    await query_wayback_snapshots(test_url, correlation_id, years=3)

    # Assert
    mock_rate_limiter.acquire.assert_called_once_with("https://web.archive.org/cdx/search")


@pytest.mark.asyncio
async def test_query_wayback_snapshots_filters_by_date(mocker):
    """Test that snapshots are filtered to specified time range."""
    # Arrange
    test_url = "https://example.edu/lab"
    correlation_id = "test-corr-id"

    # Mock snapshots - some within 3 years, some older
    mock_snapshot_recent = Mock()
    mock_snapshot_recent.datetime_timestamp = datetime.now() - timedelta(days=365)
    mock_snapshot_recent.archive_url = "https://web.archive.org/recent"
    mock_snapshot_recent.original = test_url

    mock_snapshot_old = Mock()
    mock_snapshot_old.datetime_timestamp = datetime.now() - timedelta(days=1500)
    mock_snapshot_old.archive_url = "https://web.archive.org/old"
    mock_snapshot_old.original = test_url

    # Mock CDX API
    mock_cdx = Mock()
    mock_cdx.snapshots.return_value = [mock_snapshot_recent, mock_snapshot_old]
    mocker.patch(
        "src.agents.lab_research.WaybackMachineCDXServerAPI",
        return_value=mock_cdx
    )

    # Mock rate limiter
    mock_rate_limiter = mocker.patch("src.agents.lab_research.rate_limiter")
    mock_rate_limiter.acquire = AsyncMock()

    # Act
    snapshots = await query_wayback_snapshots(test_url, correlation_id, years=3)

    # Assert
    assert len(snapshots) == 1  # Only recent snapshot included
    assert snapshots[0]["datetime"] == mock_snapshot_recent.datetime_timestamp


# ============================================================================
# Task 9: enrich_with_archive_data Tests
# ============================================================================


@pytest.mark.asyncio
async def test_enrich_with_archive_data_success(mocker):
    """Test successful archive data enrichment."""
    # Arrange
    lab = Lab(
        id="test-lab-id",
        professor_id="prof-123",
        professor_name="Dr. Test",
        department="Computer Science",
        lab_name="Test Lab",
        lab_url="https://example.edu/lab",
    )
    correlation_id = "test-corr-id"

    # Mock query_wayback_snapshots
    # Intervals: 45 days, 50 days -> average 47.5 days = monthly
    mock_snapshots = [
        {"datetime": datetime(2025, 3, 1), "archive_url": "url1", "original_url": lab.lab_url},
        {"datetime": datetime(2025, 1, 15), "archive_url": "url2", "original_url": lab.lab_url},
        {"datetime": datetime(2024, 11, 26), "archive_url": "url3", "original_url": lab.lab_url},
    ]
    mocker.patch(
        "src.agents.lab_research.query_wayback_snapshots",
        return_value=mock_snapshots
    )

    # Act
    enriched_lab = await enrich_with_archive_data(lab, correlation_id)

    # Assert
    assert enriched_lab.last_wayback_snapshot == datetime(2025, 3, 1)
    assert len(enriched_lab.wayback_snapshots) == 3
    assert enriched_lab.update_frequency == "monthly"
    assert "no_archive_data" not in enriched_lab.data_quality_flags
    assert "archive_query_failed" not in enriched_lab.data_quality_flags


@pytest.mark.asyncio
async def test_enrich_with_archive_data_no_lab_url(mocker):
    """Test enrichment skips labs with no URL."""
    # Arrange
    lab = Lab(
        id="test-lab-id",
        professor_id="prof-123",
        professor_name="Dr. Test",
        department="Computer Science",
        lab_name="Test Lab",
        lab_url=None,
    )
    correlation_id = "test-corr-id"

    # Mock query_wayback_snapshots (should not be called)
    mock_query = mocker.patch("src.agents.lab_research.query_wayback_snapshots")

    # Act
    enriched_lab = await enrich_with_archive_data(lab, correlation_id)

    # Assert
    assert enriched_lab.last_wayback_snapshot is None
    assert enriched_lab.wayback_snapshots == []
    assert enriched_lab.update_frequency == "unknown"
    mock_query.assert_not_called()


@pytest.mark.asyncio
async def test_enrich_with_archive_data_no_snapshots_found(mocker):
    """Test handling of labs with no archive snapshots."""
    # Arrange
    lab = Lab(
        id="test-lab-id",
        professor_id="prof-123",
        professor_name="Dr. Test",
        department="Computer Science",
        lab_name="Test Lab",
        lab_url="https://example.edu/lab",
    )
    correlation_id = "test-corr-id"

    # Mock query_wayback_snapshots to return empty list
    mocker.patch(
        "src.agents.lab_research.query_wayback_snapshots",
        return_value=[]
    )

    # Act
    enriched_lab = await enrich_with_archive_data(lab, correlation_id)

    # Assert
    assert enriched_lab.last_wayback_snapshot is None
    assert enriched_lab.wayback_snapshots == []
    assert enriched_lab.update_frequency == "unknown"
    assert "no_archive_data" in enriched_lab.data_quality_flags


@pytest.mark.asyncio
async def test_enrich_with_archive_data_api_failure(mocker):
    """Test graceful handling of API failures."""
    # Arrange
    lab = Lab(
        id="test-lab-id",
        professor_id="prof-123",
        professor_name="Dr. Test",
        department="Computer Science",
        lab_name="Test Lab",
        lab_url="https://example.edu/lab",
    )
    correlation_id = "test-corr-id"

    # Mock query_wayback_snapshots to raise exception
    mocker.patch(
        "src.agents.lab_research.query_wayback_snapshots",
        side_effect=Exception("API Error")
    )

    # Act
    enriched_lab = await enrich_with_archive_data(lab, correlation_id)

    # Assert
    assert enriched_lab.last_wayback_snapshot is None
    assert enriched_lab.wayback_snapshots == []
    assert enriched_lab.update_frequency == "unknown"
    assert "archive_query_failed" in enriched_lab.data_quality_flags


@pytest.mark.asyncio
async def test_enrich_with_archive_data_sorts_snapshots(mocker):
    """Test that snapshots are sorted chronologically."""
    # Arrange
    lab = Lab(
        id="test-lab-id",
        professor_id="prof-123",
        professor_name="Dr. Test",
        department="Computer Science",
        lab_name="Test Lab",
        lab_url="https://example.edu/lab",
    )
    correlation_id = "test-corr-id"

    # Mock query_wayback_snapshots with unsorted dates
    mock_snapshots = [
        {"datetime": datetime(2025, 2, 1), "archive_url": "url2", "original_url": lab.lab_url},
        {"datetime": datetime(2025, 3, 1), "archive_url": "url1", "original_url": lab.lab_url},
        {"datetime": datetime(2025, 1, 1), "archive_url": "url3", "original_url": lab.lab_url},
    ]
    mocker.patch(
        "src.agents.lab_research.query_wayback_snapshots",
        return_value=mock_snapshots
    )

    # Act
    enriched_lab = await enrich_with_archive_data(lab, correlation_id)

    # Assert
    assert enriched_lab.wayback_snapshots[0] == datetime(2025, 1, 1)
    assert enriched_lab.wayback_snapshots[1] == datetime(2025, 2, 1)
    assert enriched_lab.wayback_snapshots[2] == datetime(2025, 3, 1)
    assert enriched_lab.last_wayback_snapshot == datetime(2025, 3, 1)


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_calculate_update_frequency_boundary_weekly_monthly():
    """Test boundary between weekly and monthly (30 days)."""
    # Arrange - Exactly 30 days average
    base_date = datetime(2025, 1, 1)
    snapshots = [
        base_date,
        base_date + timedelta(days=30),
        base_date + timedelta(days=60),
    ]

    # Act
    frequency = calculate_update_frequency(snapshots)

    # Assert
    assert frequency == "monthly"  # Threshold is <30 for weekly


def test_calculate_update_frequency_boundary_monthly_quarterly():
    """Test boundary between monthly and quarterly (90 days)."""
    # Arrange - Exactly 90 days average
    base_date = datetime(2025, 1, 1)
    snapshots = [
        base_date,
        base_date + timedelta(days=90),
        base_date + timedelta(days=180),
    ]

    # Act
    frequency = calculate_update_frequency(snapshots)

    # Assert
    assert frequency == "quarterly"  # Threshold is <90 for monthly


def test_calculate_update_frequency_boundary_quarterly_yearly():
    """Test boundary between quarterly and yearly (180 days)."""
    # Arrange - Exactly 180 days average
    base_date = datetime(2025, 1, 1)
    snapshots = [
        base_date,
        base_date + timedelta(days=180),
        base_date + timedelta(days=360),
    ]

    # Act
    frequency = calculate_update_frequency(snapshots)

    # Assert
    assert frequency == "yearly"  # Threshold is <180 for quarterly


def test_calculate_update_frequency_boundary_yearly_stale():
    """Test boundary between yearly and stale (545 days)."""
    # Arrange - Exactly 545 days average
    base_date = datetime(2025, 1, 1)
    snapshots = [
        base_date,
        base_date + timedelta(days=545),
        base_date + timedelta(days=1090),
    ]

    # Act
    frequency = calculate_update_frequency(snapshots)

    # Assert
    assert frequency == "stale"  # Threshold is <545 for yearly


@pytest.mark.asyncio
async def test_enrich_with_archive_data_single_snapshot(mocker):
    """Test enrichment with only one snapshot (frequency = unknown)."""
    # Arrange
    lab = Lab(
        id="test-lab-id",
        professor_id="prof-123",
        professor_name="Dr. Test",
        department="Computer Science",
        lab_name="Test Lab",
        lab_url="https://example.edu/lab",
    )
    correlation_id = "test-corr-id"

    # Mock query_wayback_snapshots with single snapshot
    mock_snapshots = [
        {"datetime": datetime(2025, 1, 1), "archive_url": "url1", "original_url": lab.lab_url},
    ]
    mocker.patch(
        "src.agents.lab_research.query_wayback_snapshots",
        return_value=mock_snapshots
    )

    # Act
    enriched_lab = await enrich_with_archive_data(lab, correlation_id)

    # Assert
    assert enriched_lab.last_wayback_snapshot == datetime(2025, 1, 1)
    assert len(enriched_lab.wayback_snapshots) == 1
    assert enriched_lab.update_frequency == "unknown"  # Need 2+ for frequency
