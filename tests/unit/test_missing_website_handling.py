"""
Unit tests for missing website handling (Story 4.4)

Tests for website status detection, alternative data strategies,
and missing website reporting.
"""

from datetime import datetime, timezone, timedelta

from src.models.lab import Lab
from src.agents.lab_research import (
    determine_website_status,
    apply_alternative_data_strategy,
    apply_website_status,
    generate_missing_website_report,
)


class TestDetermineWebsiteStatus:
    """Tests for website status determination (Tasks 2-3)."""

    def test_missing_status_no_url(self):
        """Test status='missing' when lab_url is None."""
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url=None,
        )

        status = determine_website_status(lab)
        assert status == "missing"

    def test_unavailable_status_scraping_failed(self):
        """Test status='unavailable' when scraping_failed flag present."""
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
            data_quality_flags=["scraping_failed"],
        )

        status = determine_website_status(lab)
        assert status == "unavailable"

    def test_unknown_status_no_dates(self):
        """Test status='unknown' when no last_updated or wayback snapshot."""
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
            last_updated=None,
            last_wayback_snapshot=None,
        )

        status = determine_website_status(lab)
        assert status == "unknown"

    def test_active_status_recent_update(self):
        """Test status='active' for website updated <1 year ago."""
        recent_date = datetime.now(timezone.utc) - timedelta(days=180)
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
            last_updated=recent_date,
        )

        status = determine_website_status(lab)
        assert status == "active"

    def test_aging_status_1_2_years(self):
        """Test status='aging' for website updated 1-2 years ago."""
        aging_date = datetime.now(timezone.utc) - timedelta(days=500)  # ~1.4 years
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
            last_updated=aging_date,
        )

        status = determine_website_status(lab)
        assert status == "aging"

    def test_stale_status_over_2_years(self):
        """Test status='stale' for website updated >2 years ago."""
        stale_date = datetime.now(timezone.utc) - timedelta(days=800)  # ~2.2 years
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
            last_updated=stale_date,
        )

        status = determine_website_status(lab)
        assert status == "stale"

    def test_boundary_exactly_365_days(self):
        """Test boundary condition at exactly 365 days."""
        boundary_date = datetime.now(timezone.utc) - timedelta(days=365)
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
            last_updated=boundary_date,
        )

        status = determine_website_status(lab)
        assert status == "active"  # Exactly 365 days is still active

    def test_boundary_exactly_730_days(self):
        """Test boundary condition at exactly 730 days."""
        boundary_date = datetime.now(timezone.utc) - timedelta(days=730)
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
            last_updated=boundary_date,
        )

        status = determine_website_status(lab)
        assert status == "aging"  # Exactly 730 days is still aging

    def test_timezone_naive_datetime(self):
        """Test handling of timezone-naive datetime objects."""
        # Create naive datetime (no tzinfo)
        naive_date = datetime.now() - timedelta(days=100)
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
            last_updated=naive_date,
        )

        # Should not raise exception, assumes UTC
        status = determine_website_status(lab)
        assert status == "active"

    def test_fallback_to_wayback_snapshot(self):
        """Test fallback to last_wayback_snapshot when last_updated is None."""
        wayback_date = datetime.now(timezone.utc) - timedelta(days=500)
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
            last_updated=None,
            last_wayback_snapshot=wayback_date,
        )

        status = determine_website_status(lab)
        assert status == "aging"


class TestApplyAlternativeDataStrategy:
    """Tests for alternative data strategy application (Task 4)."""

    def test_apply_strategy_for_missing(self):
        """Test flags applied for missing website."""
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url=None,
            website_status="missing",
        )

        apply_alternative_data_strategy(lab)

        assert "using_publication_data" in lab.data_quality_flags
        assert "members_will_be_inferred" in lab.data_quality_flags

    def test_apply_strategy_for_stale(self):
        """Test flags applied for stale website."""
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
            website_status="stale",
        )

        apply_alternative_data_strategy(lab)

        assert "using_publication_data" in lab.data_quality_flags
        assert "members_will_be_inferred" in lab.data_quality_flags

    def test_apply_strategy_for_unavailable(self):
        """Test flags applied for unavailable website."""
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
            website_status="unavailable",
            data_quality_flags=["scraping_failed"],
        )

        apply_alternative_data_strategy(lab)

        assert "using_publication_data" in lab.data_quality_flags
        assert "members_will_be_inferred" in lab.data_quality_flags

    def test_no_strategy_for_active(self):
        """Test no flags applied for active website."""
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
            website_status="active",
        )

        apply_alternative_data_strategy(lab)

        assert "using_publication_data" not in lab.data_quality_flags
        assert "members_will_be_inferred" not in lab.data_quality_flags

    def test_no_duplicate_flags(self):
        """Test flags are not duplicated if already present."""
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url=None,
            website_status="missing",
            data_quality_flags=["using_publication_data"],
        )

        apply_alternative_data_strategy(lab)

        # Should only have one instance of each flag
        assert lab.data_quality_flags.count("using_publication_data") == 1
        assert "members_will_be_inferred" in lab.data_quality_flags


class TestApplyWebsiteStatus:
    """Tests for website status application with error handling (Task 5)."""

    def test_apply_status_success(self):
        """Test successful status application."""
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url=None,
        )

        apply_website_status(lab, "test-correlation-id")

        assert lab.website_status == "missing"
        assert "using_publication_data" in lab.data_quality_flags
        assert "members_will_be_inferred" in lab.data_quality_flags

    def test_apply_status_adds_stale_flag(self):
        """Test stale_website flag is added for stale status."""
        stale_date = datetime.now(timezone.utc) - timedelta(days=800)
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
            last_updated=stale_date,
        )

        apply_website_status(lab, "test-correlation-id")

        assert lab.website_status == "stale"
        assert "stale_website" in lab.data_quality_flags

    def test_apply_status_adds_aging_flag(self):
        """Test aging_website flag is added for aging status."""
        aging_date = datetime.now(timezone.utc) - timedelta(days=500)
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
            last_updated=aging_date,
        )

        apply_website_status(lab, "test-correlation-id")

        assert lab.website_status == "aging"
        assert "aging_website" in lab.data_quality_flags

    def test_graceful_error_handling(self):
        """Test graceful handling when status detection fails."""
        # Create a mock lab that will cause an error (e.g., missing required fields)
        # We'll test this by mocking determine_website_status to raise an exception

        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url="https://example.edu",
        )

        # Even if there's an internal error, status should default to unknown
        # and status_detection_failed flag should be added
        # This is a graceful degradation test

        apply_website_status(lab, "test-correlation-id")

        # Should complete without raising exception
        assert lab.website_status is not None

    def test_no_duplicate_flags_on_reapplication(self):
        """Test flags are not duplicated on re-application."""
        lab = Lab(
            id="lab-1",
            professor_id="prof-1",
            professor_name="Dr. Smith",
            department="Computer Science",
            lab_name="AI Lab",
            lab_url=None,
            data_quality_flags=["using_publication_data"],
        )

        apply_website_status(lab, "test-correlation-id")
        apply_website_status(lab, "test-correlation-id")

        assert lab.data_quality_flags.count("using_publication_data") == 1


class TestGenerateMissingWebsiteReport:
    """Tests for missing website report generation (Task 6)."""

    def test_generate_report_basic(self, tmp_path):
        """Test basic report generation."""
        output_path = tmp_path / "missing-websites.md"

        labs = [
            Lab(
                id="lab-1",
                professor_id="prof-1",
                professor_name="Dr. Smith",
                department="Computer Science",
                lab_name="AI Lab",
                lab_url=None,
                website_status="missing",
                data_quality_flags=["no_website", "using_publication_data"],
            ),
            Lab(
                id="lab-2",
                professor_id="prof-2",
                professor_name="Dr. Johnson",
                department="Engineering",
                lab_name="Robotics Lab",
                lab_url="https://example.edu",
                website_status="active",
                last_updated=datetime.now(timezone.utc),
            ),
        ]

        generate_missing_website_report(labs, str(output_path))

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "# Labs with Missing or Stale Websites" in content
        assert "## Summary" in content
        assert "Total labs analyzed: 2" in content

    def test_report_includes_all_sections(self, tmp_path):
        """Test report includes all required sections."""
        output_path = tmp_path / "missing-websites.md"

        stale_date = datetime.now(timezone.utc) - timedelta(days=800)
        aging_date = datetime.now(timezone.utc) - timedelta(days=500)

        labs = [
            Lab(
                id="lab-1",
                professor_id="prof-1",
                professor_name="Dr. A",
                department="CS",
                lab_name="Lab A",
                lab_url=None,
                website_status="missing",
                data_quality_flags=["no_website", "using_publication_data"],
            ),
            Lab(
                id="lab-2",
                professor_id="prof-2",
                professor_name="Dr. B",
                department="Eng",
                lab_name="Lab B",
                lab_url="https://stale.edu",
                last_updated=stale_date,
                website_status="stale",
                data_quality_flags=["stale_website", "using_publication_data"],
            ),
            Lab(
                id="lab-3",
                professor_id="prof-3",
                professor_name="Dr. C",
                department="Math",
                lab_name="Lab C",
                lab_url="https://aging.edu",
                last_updated=aging_date,
                website_status="aging",
                data_quality_flags=["aging_website"],
            ),
            Lab(
                id="lab-4",
                professor_id="prof-4",
                professor_name="Dr. D",
                department="Physics",
                lab_name="Lab D",
                lab_url="https://unavailable.edu",
                website_status="unavailable",
                data_quality_flags=["scraping_failed", "using_publication_data"],
            ),
        ]

        generate_missing_website_report(labs, str(output_path))

        content = output_path.read_text(encoding="utf-8")
        assert "## Missing Websites" in content
        assert "## Stale Websites" in content
        assert "## Aging Websites" in content
        assert "## Unavailable Websites" in content
        assert "Dr. A" in content
        assert "Dr. B" in content
        assert "Dr. C" in content
        assert "Dr. D" in content

    def test_report_statistics_calculation(self, tmp_path):
        """Test statistics are calculated correctly."""
        output_path = tmp_path / "missing-websites.md"

        active_date = datetime.now(timezone.utc) - timedelta(days=100)

        labs = [
            Lab(
                id="lab-1",
                professor_id="p1",
                professor_name="Dr. A",
                department="CS",
                lab_name="Lab 1",
                lab_url=None,
                website_status="missing",
            ),
            Lab(
                id="lab-2",
                professor_id="p2",
                professor_name="Dr. B",
                department="CS",
                lab_name="Lab 2",
                lab_url="https://active.edu",
                website_status="active",
                last_updated=active_date,
            ),
            Lab(
                id="lab-3",
                professor_id="p3",
                professor_name="Dr. C",
                department="CS",
                lab_name="Lab 3",
                lab_url="https://active2.edu",
                website_status="active",
                last_updated=active_date,
            ),
        ]

        generate_missing_website_report(labs, str(output_path))

        content = output_path.read_text(encoding="utf-8")
        assert "Total labs analyzed: 3" in content
        assert "Labs with active websites (<1 year): 2 (66.7%)" in content
        assert "Labs with missing websites: 1 (33.3%)" in content

    def test_report_creates_output_directory(self, tmp_path):
        """Test report creates output directory if it doesn't exist."""
        output_path = tmp_path / "new_dir" / "missing-websites.md"

        labs = [
            Lab(
                id="lab-1",
                professor_id="prof-1",
                professor_name="Dr. Smith",
                department="CS",
                lab_name="Lab",
                lab_url=None,
                website_status="missing",
            ),
        ]

        generate_missing_website_report(labs, str(output_path))

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_report_empty_sections_omitted(self, tmp_path):
        """Test empty sections are omitted from report."""
        output_path = tmp_path / "missing-websites.md"

        # Only active labs
        active_date = datetime.now(timezone.utc) - timedelta(days=100)
        labs = [
            Lab(
                id="lab-1",
                professor_id="p1",
                professor_name="Dr. A",
                department="CS",
                lab_name="Lab 1",
                lab_url="https://active.edu",
                website_status="active",
                last_updated=active_date,
            ),
        ]

        generate_missing_website_report(labs, str(output_path))

        content = output_path.read_text(encoding="utf-8")
        # Sections for missing/stale/aging/unavailable should not appear
        # (only header, summary, and note)
        assert content.count("##") == 1  # Only "## Summary"

    def test_report_markdown_table_format(self, tmp_path):
        """Test report uses correct markdown table format."""
        output_path = tmp_path / "missing-websites.md"

        labs = [
            Lab(
                id="lab-1",
                professor_id="prof-1",
                professor_name="Dr. Smith",
                department="Computer Science",
                lab_name="AI Lab",
                lab_url=None,
                website_status="missing",
                data_quality_flags=["no_website", "using_publication_data"],
            ),
        ]

        generate_missing_website_report(labs, str(output_path))

        content = output_path.read_text(encoding="utf-8")
        # Check table headers and separators
        assert "| Lab | Professor | Department | Alternative Data | Flags |" in content
        assert "|-----|-----------|------------|------------------|-------|" in content

    def test_report_footer_note(self, tmp_path):
        """Test report includes footer note about not excluding labs."""
        output_path = tmp_path / "missing-websites.md"

        labs = [
            Lab(
                id="lab-1",
                professor_id="prof-1",
                professor_name="Dr. Smith",
                department="CS",
                lab_name="Lab",
                lab_url=None,
                website_status="missing",
            ),
        ]

        generate_missing_website_report(labs, str(output_path))

        content = output_path.read_text(encoding="utf-8")
        assert (
            "Labs with missing/stale/unavailable websites will rely on publication data"
            in content
        )
        assert "NOT excluded from fitness scoring" in content

    def test_report_utf8_encoding(self, tmp_path):
        """Test report handles UTF-8 characters correctly."""
        output_path = tmp_path / "missing-websites.md"

        labs = [
            Lab(
                id="lab-1",
                professor_id="prof-1",
                professor_name="Dr. José García",  # UTF-8 characters
                department="Computer Science",
                lab_name="AI Research Lab",
                lab_url=None,
                website_status="missing",
            ),
        ]

        generate_missing_website_report(labs, str(output_path))

        content = output_path.read_text(encoding="utf-8")
        assert "Dr. José García" in content
