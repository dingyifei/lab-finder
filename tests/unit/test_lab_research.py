"""
Unit tests for Lab Research Agent.

Story 4.1: Tasks 3-7
"""

from src.agents.lab_research import (
    validate_url,
    discover_lab_website,
    parse_date_string,
    extract_last_updated,
    extract_lab_description,
    extract_research_focus,
    extract_news_updates,
)
from src.models.professor import Professor


def test_validate_url_valid():
    """Test URL validation with valid URLs."""
    # Arrange & Act & Assert
    assert validate_url("https://example.com") is True
    assert validate_url("http://university.edu/lab") is True
    assert validate_url("https://cs.mit.edu/vision-lab") is True


def test_validate_url_invalid():
    """Test URL validation with invalid URLs."""
    # Arrange & Act & Assert
    assert validate_url("") is False
    assert validate_url("   ") is False
    assert validate_url("not-a-url") is False
    assert validate_url("ftp://example.com") is False


def test_validate_url_none():
    """Test URL validation with None."""
    # Arrange & Act & Assert
    assert validate_url(None) is False  # type: ignore


def test_discover_lab_website_from_professor_field():
    """Test lab discovery from professor.lab_url field."""
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

    # Act
    url = discover_lab_website(professor)

    # Assert
    assert url == "https://visionlab.example.edu"


def test_discover_lab_website_empty_lab_url():
    """Test lab discovery with empty professor.lab_url."""
    # Arrange
    professor = Professor(
        id="prof1",
        name="Dr. Jane Smith",
        title="Professor",
        department_id="dept1",
        department_name="Computer Science",
        profile_url="https://cs.example.edu/jsmith",
        lab_url="   ",  # Empty/whitespace
    )

    # Act
    url = discover_lab_website(professor)

    # Assert - Should return None (strategies 2-4 are TODOs)
    assert url is None


def test_discover_lab_website_none_lab_url():
    """Test lab discovery with None professor.lab_url."""
    # Arrange
    professor = Professor(
        id="prof1",
        name="Dr. Jane Smith",
        title="Professor",
        department_id="dept1",
        department_name="Computer Science",
        profile_url="https://cs.example.edu/jsmith",
        lab_url=None,
    )

    # Act
    url = discover_lab_website(professor)

    # Assert - Should return None (strategies 2-4 are TODOs)
    assert url is None


def test_parse_date_string_iso_format():
    """Test date parsing with ISO format."""
    # Arrange & Act
    date = parse_date_string("2025-10-01")

    # Assert
    assert date is not None
    assert date.year == 2025
    assert date.month == 10
    assert date.day == 1


def test_parse_date_string_various_formats():
    """Test date parsing with various formats."""
    # Arrange & Act
    date1 = parse_date_string("10/01/2025")  # US format
    date2 = parse_date_string("October 1, 2025")  # Long format
    date3 = parse_date_string("01-Oct-2025")  # Short month

    # Assert
    assert all(d is not None for d in [date1, date2, date3])
    assert all(d.year == 2025 for d in [date1, date2, date3])


def test_parse_date_string_invalid():
    """Test date parsing with invalid string."""
    # Arrange & Act
    date = parse_date_string("invalid date")

    # Assert
    assert date is None


def test_extract_last_updated_meta_tag():
    """Test extracting last updated from meta tag."""
    # Arrange
    html = '<html><head><meta name="last-modified" content="2025-10-01"></head></html>'

    # Act
    date = extract_last_updated(html)

    # Assert
    assert date is not None
    assert date.year == 2025


def test_extract_last_updated_text_pattern():
    """Test extracting last updated from text pattern."""
    # Arrange
    html = "<html><body><p>Last Updated: October 1, 2025</p></body></html>"

    # Act
    date = extract_last_updated(html)

    # Assert
    assert date is not None
    assert date.year == 2025


def test_extract_last_updated_not_found():
    """Test extracting last updated when not present."""
    # Arrange
    html = "<html><body><p>Some content</p></body></html>"

    # Act
    date = extract_last_updated(html)

    # Assert
    assert date is None


def test_extract_lab_description_with_selector():
    """Test extracting description with common selector."""
    # Arrange
    html = """
    <html>
        <body>
            <div class="lab-overview">
                This is the lab description with more than fifty characters to meet threshold.
            </div>
        </body>
    </html>
    """

    # Act
    description = extract_lab_description(html)

    # Assert
    assert "lab description" in description.lower()
    assert len(description) > 50


def test_extract_lab_description_not_found():
    """Test extracting description when not present."""
    # Arrange
    html = "<html><body><p>Short</p></body></html>"

    # Act
    description = extract_lab_description(html)

    # Assert
    assert description == ""


def test_extract_research_focus_with_list():
    """Test extracting research focus from list items."""
    # Arrange
    html = """
    <html>
        <body>
            <div class="research-areas">
                <ul>
                    <li>Machine Learning</li>
                    <li>Computer Vision</li>
                    <li>Natural Language Processing</li>
                </ul>
            </div>
        </body>
    </html>
    """

    # Act
    focus_areas = extract_research_focus(html)

    # Assert
    assert len(focus_areas) == 3
    assert "Machine Learning" in focus_areas
    assert "Computer Vision" in focus_areas


def test_extract_research_focus_not_found():
    """Test extracting research focus when not present."""
    # Arrange
    html = "<html><body><p>No research areas here</p></body></html>"

    # Act
    focus_areas = extract_research_focus(html)

    # Assert
    assert focus_areas == []


def test_extract_news_updates_with_items():
    """Test extracting news updates."""
    # Arrange
    html = """
    <html>
        <body>
            <div class="news">
                <ul>
                    <li>2025-10-01: New paper published in Nature</li>
                    <li>2025-09-15: PhD student awarded fellowship</li>
                </ul>
            </div>
        </body>
    </html>
    """

    # Act
    news = extract_news_updates(html)

    # Assert
    assert len(news) >= 1
    assert any("paper published" in item.lower() for item in news)


def test_extract_news_updates_not_found():
    """Test extracting news when not present."""
    # Arrange
    html = "<html><body><p>No news section</p></body></html>"

    # Act
    news = extract_news_updates(html)

    # Assert
    assert news == []
