"""
Unit tests for contact information extraction (Story 4.3).

Tests cover:
- Email extraction with filtering
- Email validation
- Contact form URL extraction
- Application URL extraction
- Missing contact info handling
- Relative to absolute URL conversion
- Error handling and graceful degradation
"""

from src.agents.lab_research import (
    extract_emails,
    validate_email,
    extract_contact_form,
    extract_application_url,
    extract_contact_info_safe,
)


# ==============================================================================
# Email Extraction Tests (Task 2)
# ==============================================================================


def test_extract_emails_basic():
    """Test basic email extraction from text."""
    text = "Contact us at professor@university.edu or lab@cs.stanford.edu"
    emails = extract_emails(text)

    assert len(emails) == 2
    assert "professor@university.edu" in emails
    assert "lab@cs.stanford.edu" in emails


def test_extract_emails_filters_generic():
    """Test that generic emails are filtered out."""
    text = """
    Contact: professor@university.edu
    Email: webmaster@university.edu
    Support: admin@university.edu
    Lab: lab-contact@university.edu
    Info: info@university.edu
    No reply: noreply@university.edu
    """

    emails = extract_emails(text)

    assert "professor@university.edu" in emails
    assert "lab-contact@university.edu" in emails
    assert "webmaster@university.edu" not in emails
    assert "admin@university.edu" not in emails
    assert "info@university.edu" not in emails
    assert "noreply@university.edu" not in emails


def test_extract_emails_normalizes_to_lowercase():
    """Test that emails are normalized to lowercase."""
    text = "Contact: Professor@University.EDU and LAB@CS.Stanford.edu"
    emails = extract_emails(text)

    assert "professor@university.edu" in emails
    assert "lab@cs.stanford.edu" in emails
    assert "Professor@University.EDU" not in emails  # Should be normalized


def test_extract_emails_deduplicates():
    """Test that duplicate emails are removed."""
    text = """
    Email 1: professor@university.edu
    Email 2: professor@university.edu
    Email 3: Professor@University.EDU
    """
    emails = extract_emails(text)

    assert len(emails) == 1
    assert "professor@university.edu" in emails


def test_extract_emails_empty_text():
    """Test email extraction from empty text."""
    emails = extract_emails("")
    assert emails == []


def test_extract_emails_no_emails():
    """Test email extraction when no emails present."""
    text = "This text has no email addresses in it at all."
    emails = extract_emails(text)
    assert emails == []


def test_extract_emails_complex_patterns():
    """Test email extraction with complex patterns."""
    text = """
    john.doe+research@university.edu
    jane_smith-lab@cs.stanford.edu
    pi123@dept.university.co.uk
    """
    emails = extract_emails(text)

    assert len(emails) == 3
    assert "john.doe+research@university.edu" in emails
    assert "jane_smith-lab@cs.stanford.edu" in emails
    assert "pi123@dept.university.co.uk" in emails


# ==============================================================================
# Email Validation Tests (Task 2)
# ==============================================================================


def test_validate_email_valid():
    """Test validation of valid email addresses."""
    assert validate_email("professor@university.edu") is True
    assert validate_email("jane.smith@cs.stanford.edu") is True
    assert validate_email("john+lab@dept.university.co.uk") is True


def test_validate_email_invalid():
    """Test validation of invalid email addresses."""
    assert validate_email("not-an-email") is False
    assert validate_email("@university.edu") is False
    assert validate_email("professor@") is False
    assert validate_email("professor@.edu") is False
    assert validate_email("") is False


# ==============================================================================
# Contact Form URL Tests (Task 3)
# ==============================================================================


def test_extract_contact_form_absolute_url():
    """Test extraction of absolute contact form URL."""
    html = '<a href="https://lab.stanford.edu/contact">Contact Us</a>'
    base_url = "https://lab.stanford.edu"

    url = extract_contact_form(html, base_url)
    assert url == "https://lab.stanford.edu/contact"


def test_extract_contact_form_relative_url():
    """Test conversion of relative contact form URL to absolute."""
    html = '<a href="/contact">Contact Us</a>'
    base_url = "https://lab.stanford.edu"

    url = extract_contact_form(html, base_url)
    assert url == "https://lab.stanford.edu/contact"


def test_extract_contact_form_various_patterns():
    """Test extraction with various contact patterns."""
    test_cases = [
        ('<a href="/contact">Contact</a>', "contact"),
        ('<a href="/get-in-touch">Get in Touch</a>', "get-in-touch"),
        ('<a href="/reach-out">Reach Out</a>', "reach-out"),
        ('<a href="/join">Join</a>', "join"),
    ]

    base_url = "https://lab.stanford.edu"

    for html, expected_path in test_cases:
        url = extract_contact_form(html, base_url)
        assert url == f"https://lab.stanford.edu/{expected_path}"


def test_extract_contact_form_not_found():
    """Test when no contact form URL is found."""
    html = '<a href="/research">Research</a>'
    base_url = "https://lab.stanford.edu"

    url = extract_contact_form(html, base_url)
    assert url is None


def test_extract_contact_form_case_insensitive():
    """Test case-insensitive contact form extraction."""
    html = '<a href="/CONTACT">CONTACT US</a>'
    base_url = "https://lab.stanford.edu"

    url = extract_contact_form(html, base_url)
    assert url == "https://lab.stanford.edu/CONTACT"


# ==============================================================================
# Application URL Tests (Task 4)
# ==============================================================================


def test_extract_application_url_absolute():
    """Test extraction of absolute application URL."""
    html = '<a href="https://lab.stanford.edu/prospective">Prospective Students</a>'
    base_url = "https://lab.stanford.edu"

    url = extract_application_url(html, base_url)
    assert url == "https://lab.stanford.edu/prospective"


def test_extract_application_url_relative():
    """Test conversion of relative application URL to absolute."""
    html = '<a href="/apply">Apply</a>'
    base_url = "https://lab.stanford.edu"

    url = extract_application_url(html, base_url)
    assert url == "https://lab.stanford.edu/apply"


def test_extract_application_url_various_keywords():
    """Test extraction with various application keywords."""
    test_cases = [
        ('<a href="/prospective">Prospective</a>', "prospective"),
        ('<a href="/apply">Apply</a>', "apply"),
        ('<a href="/join">Join Us</a>', "join"),
        ('<a href="/positions">Positions</a>', "positions"),
        ('<a href="/openings">Openings</a>', "openings"),
        ('<a href="/opportunities">Opportunities</a>', "opportunities"),
    ]

    base_url = "https://lab.stanford.edu"

    for html, expected_path in test_cases:
        url = extract_application_url(html, base_url)
        assert url == f"https://lab.stanford.edu/{expected_path}"


def test_extract_application_url_not_found():
    """Test when no application URL is found."""
    html = '<a href="/research">Research</a>'
    base_url = "https://lab.stanford.edu"

    url = extract_application_url(html, base_url)
    assert url is None


def test_extract_application_url_case_insensitive():
    """Test case-insensitive application URL extraction."""
    html = '<a href="/PROSPECTIVE">PROSPECTIVE STUDENTS</a>'
    base_url = "https://lab.stanford.edu"

    url = extract_application_url(html, base_url)
    assert url == "https://lab.stanford.edu/PROSPECTIVE"


# ==============================================================================
# Orchestrator Tests (Tasks 2-5)
# ==============================================================================


def test_extract_contact_info_safe_full_extraction():
    """Test safe extraction with all contact info present."""
    html = """
    <html>
    <body>
        <p>Contact: professor@university.edu</p>
        <p>Lab: lab@cs.stanford.edu</p>
        <a href="/contact">Contact Us</a>
        <a href="/apply">Apply for PhD</a>
    </body>
    </html>
    """
    base_url = "https://lab.stanford.edu"

    result = extract_contact_info_safe(html, base_url)

    assert len(result["contact_emails"]) == 2
    assert "professor@university.edu" in result["contact_emails"]
    assert "lab@cs.stanford.edu" in result["contact_emails"]
    assert result["contact_form_url"] == "https://lab.stanford.edu/contact"
    assert result["application_url"] == "https://lab.stanford.edu/apply"
    assert "no_contact_info" not in result["data_quality_flags"]
    assert "no_email" not in result["data_quality_flags"]
    assert "no_contact_form" not in result["data_quality_flags"]
    assert "no_application_url" not in result["data_quality_flags"]


def test_extract_contact_info_safe_partial_extraction():
    """Test safe extraction with some contact info missing."""
    html = """
    <html>
    <body>
        <p>Contact: professor@university.edu</p>
    </body>
    </html>
    """
    base_url = "https://lab.stanford.edu"

    result = extract_contact_info_safe(html, base_url)

    assert len(result["contact_emails"]) == 1
    assert "professor@university.edu" in result["contact_emails"]
    assert result["contact_form_url"] is None
    assert result["application_url"] is None
    assert "no_contact_info" not in result["data_quality_flags"]
    assert "no_email" not in result["data_quality_flags"]
    assert "no_contact_form" in result["data_quality_flags"]
    assert "no_application_url" in result["data_quality_flags"]


def test_extract_contact_info_safe_no_contact_info():
    """Test safe extraction with no contact info found."""
    html = """
    <html>
    <body>
        <p>This is a lab website with no contact information.</p>
    </body>
    </html>
    """
    base_url = "https://lab.stanford.edu"

    result = extract_contact_info_safe(html, base_url)

    assert result["contact_emails"] == []
    assert result["contact_form_url"] is None
    assert result["application_url"] is None
    assert "no_contact_info" in result["data_quality_flags"]
    assert "no_email" not in result["data_quality_flags"]  # no_contact_info supersedes
    assert "no_contact_form" not in result["data_quality_flags"]
    assert "no_application_url" not in result["data_quality_flags"]


def test_extract_contact_info_safe_empty_content():
    """Test safe extraction with empty content."""
    result = extract_contact_info_safe("", "https://lab.stanford.edu")

    assert result["contact_emails"] == []
    assert result["contact_form_url"] is None
    assert result["application_url"] is None
    assert "no_contact_info" in result["data_quality_flags"]


def test_extract_contact_info_safe_filters_generic_emails():
    """Test that orchestrator filters generic emails correctly."""
    html = """
    <html>
    <body>
        <p>Contact: professor@university.edu</p>
        <p>Webmaster: webmaster@university.edu</p>
        <p>Support: support@university.edu</p>
    </body>
    </html>
    """
    base_url = "https://lab.stanford.edu"

    result = extract_contact_info_safe(html, base_url)

    assert len(result["contact_emails"]) == 1
    assert "professor@university.edu" in result["contact_emails"]
    assert "webmaster@university.edu" not in result["contact_emails"]
    assert "support@university.edu" not in result["contact_emails"]


# ==============================================================================
# Relative to Absolute URL Conversion Tests
# ==============================================================================


def test_relative_url_conversion_root_path():
    """Test conversion of root relative path."""
    html = '<a href="/contact">Contact</a>'
    base_url = "https://lab.stanford.edu/research"

    url = extract_contact_form(html, base_url)
    assert url == "https://lab.stanford.edu/contact"


def test_relative_url_conversion_nested_path():
    """Test conversion of nested relative path."""
    html = '<a href="contact/form">Contact</a>'
    base_url = "https://lab.stanford.edu/research/"

    url = extract_contact_form(html, base_url)
    assert url == "https://lab.stanford.edu/research/contact/form"


def test_relative_url_with_query_params():
    """Test URL extraction with query parameters."""
    html = '<a href="/contact?section=prospective">Contact</a>'
    base_url = "https://lab.stanford.edu"

    url = extract_contact_form(html, base_url)
    assert url == "https://lab.stanford.edu/contact?section=prospective"


# ==============================================================================
# Integration Test
# ==============================================================================


def test_full_contact_extraction_integration():
    """Integration test with realistic HTML content."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Vision Lab - Stanford University</title>
    </head>
    <body>
        <header>
            <h1>Vision Lab</h1>
            <nav>
                <a href="/research">Research</a>
                <a href="/publications">Publications</a>
                <a href="/contact">Contact</a>
                <a href="/prospective-students">Prospective Students</a>
            </nav>
        </header>
        <main>
            <section id="about">
                <p>Our lab focuses on computer vision and machine learning.</p>
            </section>
            <section id="contact-info">
                <h2>Contact Information</h2>
                <p>PI: Dr. Jane Smith - jane.smith@stanford.edu</p>
                <p>Lab Manager: lab-manager@cs.stanford.edu</p>
                <p>Webmaster: webmaster@stanford.edu</p>
            </section>
        </main>
        <footer>
            <p>© 2025 Vision Lab</p>
        </footer>
    </body>
    </html>
    """
    base_url = "https://vision.stanford.edu"

    result = extract_contact_info_safe(html, base_url)

    # Check emails (should filter out webmaster)
    assert len(result["contact_emails"]) == 2
    assert "jane.smith@stanford.edu" in result["contact_emails"]
    assert "lab-manager@cs.stanford.edu" in result["contact_emails"]
    assert "webmaster@stanford.edu" not in result["contact_emails"]

    # Check URLs
    assert result["contact_form_url"] == "https://vision.stanford.edu/contact"
    assert result["application_url"] == "https://vision.stanford.edu/prospective-students"

    # Check flags
    assert "no_contact_info" not in result["data_quality_flags"]
    assert "no_email" not in result["data_quality_flags"]
    assert "no_contact_form" not in result["data_quality_flags"]
    assert "no_application_url" not in result["data_quality_flags"]
