"""
Lab Research Agent

Discovers and scrapes lab websites for content and metadata.
Story 4.1: Epic 4 (Lab Intelligence)
Story 4.2: Archive.org integration
Story 4.3: Contact information extraction
Story 4.4: Missing/stale website handling
"""

import json
import re
from datetime import datetime, timezone
from typing import Optional, Any
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from waybackpy import WaybackMachineCDXServerAPI
from waybackpy.exceptions import NoCDXRecordFound

from src.models.lab import Lab
from src.models.professor import Professor
from src.models.config import SystemParams
from src.utils.logger import get_logger
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.rate_limiter import DomainRateLimiter
from pathlib import Path
from src.utils.web_scraping import scrape_with_sufficiency


# Archive.org rate limiter (Story 4.2: Task 3)
# Conservative rate: 15 req/min to avoid 429 responses
rate_limiter = DomainRateLimiter(default_rate=15.0, time_period=60.0)


def validate_url(url: str) -> bool:
    """Validate URL format.

    Args:
        url: URL string to validate

    Returns:
        True if URL is valid, False otherwise
    """
    if not url or not url.strip():
        return False

    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def discover_lab_website(professor: Professor) -> Optional[str]:
    """Discover lab website URL for a professor.

    Discovery strategies (in order):
    1. Check if professor.lab_url exists and is valid
    2. Search professor profile page for lab website link
    3. Search department page for professor's lab link
    4. Try common URL patterns

    Args:
        professor: Professor record

    Returns:
        Lab website URL if found, None otherwise

    Story 4.1: Task 3
    """
    # Strategy 1: Check professor.lab_url field
    if professor.lab_url and professor.lab_url.strip():
        url = professor.lab_url.strip()
        if validate_url(url):
            return url

    # Strategy 2: Search professor profile page
    # TODO: Implement profile page scraping for lab links
    # This will be implemented when we integrate ClaudeSDKClient web fetch

    # Strategy 3: Search department page
    # TODO: Implement department page scraping for lab links

    # Strategy 4: Try common URL patterns
    # TODO: Implement URL pattern matching with accessibility verification
    # Would check patterns like:
    # - {base_url}/labs/{last_name}
    # - {base_url}/research/{last_name}
    # - {base_url}/{last_name}-lab
    # And verify each URL responds with 200 before returning

    # No URL found
    return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def scrape_lab_website(lab_url: str, correlation_id: str) -> dict[str, Any]:
    """Scrape lab website for 5 data categories using multi-stage pattern.

    Uses Story 4.5 multi-stage pattern: WebFetch → Sufficiency → Puppeteer MCP.

    Categories extracted (Story 4.1 v1.1):
    1. lab_information - Description, mission, overview, news
    2. contact - Emails, forms, application URLs
    3. people - Lab members, roles
    4. research_focus - Research areas/topics
    5. publications - Recent papers

    Args:
        lab_url: Lab website URL
        correlation_id: Correlation ID for logging

    Returns:
        Dictionary with 5 categories + metadata:
        - description (str)
        - news_updates (list[str])
        - last_updated (Optional[datetime])
        - contact_emails (list[str])
        - contact_form_url (Optional[str])
        - application_url (Optional[str])
        - lab_members (list[str])
        - research_focus (list[str])
        - publications_list (list[str])
        - website_content (str)
        - data_quality_flags (list[str])

    Raises:
        Exception: If scraping fails after retries

    Story 4.1 v1.1: Tasks 4, 5, 6, 7 (5-category extraction)
    Story 4.3: Contact extraction integration
    Story 4.5 v0.5: Multi-stage pattern
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="phase-4-labs",
        component="lab-research-agent",
    )

    # Define required fields (5 categories per Story 4.1 v1.1)
    required_fields = [
        "lab_information",
        "contact",
        "people",
        "research_focus",
        "publications",
    ]

    try:
        # Use multi-stage scraping (Story 4.5)
        result = await scrape_with_sufficiency(
            url=lab_url,
            required_fields=required_fields,
            max_attempts=3,
            correlation_id=correlation_id,
        )

        # result["data"] is already a dict from scrape_with_sufficiency
        # If it's a string (JSON), parse it; otherwise use directly
        scraped_content = result["data"]
        if isinstance(scraped_content, str):
            parsed_data = parse_lab_content(scraped_content)
        else:
            parsed_data = scraped_content

        # Extract data with category-based fallbacks
        lab_info = parsed_data.get("lab_information", {})
        contact_info = parsed_data.get("contact", {})
        people_info = parsed_data.get("people", [])
        research_focus = parsed_data.get("research_focus", [])
        publications = parsed_data.get("publications", [])

        # Extract last_updated from lab_information
        last_updated = None
        if isinstance(lab_info, dict) and lab_info.get("last_updated"):
            last_updated = parse_date_string(str(lab_info["last_updated"]))

        # Start with scraping result flags
        flags_from_result = result.get("data_quality_flags", [])
        data_quality_flags: list[str] = list(flags_from_result) if isinstance(flags_from_result, list) else []

        # Add category-specific quality flags
        if not lab_info or not lab_info.get("description"):
            data_quality_flags.append("missing_description")
        if not contact_info:
            data_quality_flags.append("no_contact_info")
        if not people_info:
            data_quality_flags.append("missing_people_info")
        if not research_focus:
            data_quality_flags.append("missing_research_focus")
        if not publications:
            data_quality_flags.append("missing_publications")
        if not last_updated:
            data_quality_flags.append("missing_last_updated")

        # Build return dictionary with all 5 categories
        return_data = {
            # Category 1: lab_information
            "description": lab_info.get("description", "") if isinstance(lab_info, dict) else "",
            "news_updates": lab_info.get("news", []) if isinstance(lab_info, dict) else [],
            "last_updated": last_updated,

            # Category 2: contact (Story 4.3 integration)
            "contact_emails": contact_info.get("emails", []) if isinstance(contact_info, dict) else [],
            "contact_form_url": contact_info.get("contact_form") if isinstance(contact_info, dict) else None,
            "application_url": contact_info.get("application_url") if isinstance(contact_info, dict) else None,

            # Category 3: people
            "lab_members": people_info if isinstance(people_info, list) else [],

            # Category 4: research_focus
            "research_focus": research_focus if isinstance(research_focus, list) else [],

            # Category 5: publications
            "publications_list": publications if isinstance(publications, list) else [],

            # Other
            "website_content": str(scraped_content) if isinstance(scraped_content, dict) else scraped_content,
            "data_quality_flags": data_quality_flags,
        }

        logger.info(
            "Lab website scraped (multi-stage, 5 categories)",
            lab_url=lab_url,
            categories_extracted=5,
            data_quality_flags=data_quality_flags,
        )

        return return_data

    except Exception as e:
        logger.error("Multi-stage scraping failed", lab_url=lab_url, error=str(e))
        raise  # Will trigger retry via @retry decorator


def parse_lab_content(response_text: str) -> dict[str, Any]:
    """Parse JSON from Claude's response text for 5 data categories.

    Expected JSON structure (Story 4.1 v1.1):
    {
      "lab_information": {
        "description": "...",
        "news": ["...", "..."],
        "last_updated": "YYYY-MM-DD"
      },
      "contact": {
        "emails": ["...", "..."],
        "contact_form": "URL",
        "application_url": "URL"
      },
      "people": ["Name (Role)", "Name (Role)", ...],
      "research_focus": ["Area 1", "Area 2", ...],
      "publications": ["Title 1", "Title 2", ...]
    }

    Args:
        response_text: Response text from Claude or scraped content

    Returns:
        Parsed data dictionary with 5 categories

    Raises:
        ValueError: If JSON cannot be parsed
    """
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find raw JSON object
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            raise ValueError("No JSON object found in response")

    try:
        parsed = json.loads(json_str)
        # Return parsed data (may be missing some categories - handled by caller)
        return parsed

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in response: {e}")


def parse_date_string(date_str: str) -> Optional[datetime]:
    """Parse date string to datetime object.

    Tries common date formats:
    - ISO: 2025-10-01
    - US: 10/01/2025
    - Long: October 1, 2025

    Args:
        date_str: Date string

    Returns:
        Datetime object or None if parsing fails
    """
    from dateutil import parser as date_parser

    try:
        return date_parser.parse(date_str)
    except (ValueError, TypeError):
        return None


def extract_last_updated(html_content: str) -> Optional[datetime]:
    """Extract last updated date from HTML content.

    Checks for:
    - Explicit "Last Updated" metadata
    - HTML meta tags: <meta name="last-modified">
    - Text patterns: "Updated:", "Last modified:"

    Args:
        html_content: Raw HTML content

    Returns:
        Datetime object if date found, None otherwise

    Story 4.1: Task 5
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Check meta tags
    meta_modified = soup.find("meta", attrs={"name": "last-modified"})
    if meta_modified and meta_modified.get("content"):
        date_str = str(meta_modified.get("content"))
        parsed = parse_date_string(date_str)
        if parsed:
            return parsed

    # Check for text patterns
    text = soup.get_text()
    patterns = [
        r"Last Updated:?\s*([A-Za-z0-9,\s\-/]+)",
        r"Last Modified:?\s*([A-Za-z0-9,\s\-/]+)",
        r"Updated:?\s*([A-Za-z0-9,\s\-/]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            parsed = parse_date_string(date_str)
            if parsed:
                return parsed

    return None


def extract_lab_description(html_content: str) -> str:
    """Extract lab description/overview from HTML.

    Args:
        html_content: Raw HTML content

    Returns:
        Lab description text

    Story 4.1: Task 6
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Common selectors for lab description
    selectors = [
        ".lab-overview",
        "#about",
        ".description",
        "section.about",
        ".overview",
        "#overview",
    ]

    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(strip=True, separator=" ")
            if len(text) > 50:  # Meaningful description
                return text

    # Fallback: look for first substantial paragraph after heading
    for heading in soup.find_all(["h1", "h2", "h3"]):
        heading_text = heading.get_text().lower()
        if any(
            keyword in heading_text
            for keyword in ["about", "overview", "description", "mission"]
        ):
            # Get next sibling paragraph
            next_elem = heading.find_next(["p", "div"])
            if next_elem:
                text = next_elem.get_text(strip=True, separator=" ")
                if len(text) > 50:
                    return text

    return ""


def extract_research_focus(html_content: str) -> list[str]:
    """Extract research focus areas from HTML.

    Args:
        html_content: Raw HTML content

    Returns:
        List of research focus areas

    Story 4.1: Task 6
    """
    soup = BeautifulSoup(html_content, "html.parser")
    focus_areas = []

    # Common selectors for research focus
    selectors = [
        ".research-areas",
        "#research",
        ".focus",
        ".topics",
        ".research-focus",
        "#focus",
    ]

    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            # Look for list items
            list_items = element.find_all("li")
            if list_items:
                for item in list_items:
                    text = item.get_text(strip=True)
                    if text:
                        focus_areas.append(text)
                return focus_areas[:10]  # Limit to 10 items

            # Or get paragraphs
            paragraphs = element.find_all("p")
            if paragraphs:
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text:
                        focus_areas.append(text)
                return focus_areas[:10]

    # Fallback: look for "Research" heading followed by list
    for heading in soup.find_all(["h1", "h2", "h3"]):
        heading_text = heading.get_text().lower()
        if any(
            keyword in heading_text
            for keyword in ["research", "focus", "interests", "areas"]
        ):
            # Get next list
            next_list = heading.find_next(["ul", "ol"])
            if next_list:
                items = next_list.find_all("li")
                for item in items:
                    text = item.get_text(strip=True)
                    if text:
                        focus_areas.append(text)
                return focus_areas[:10]

    return focus_areas


def extract_news_updates(html_content: str) -> list[str]:
    """Extract recent news/updates from HTML.

    Args:
        html_content: Raw HTML content

    Returns:
        List of news items (last 5-10 entries)

    Story 4.1: Task 7
    """
    soup = BeautifulSoup(html_content, "html.parser")
    news_items = []

    # Common selectors for news/updates
    selectors = [
        ".news",
        ".updates",
        "#latest",
        "section.news",
        ".latest-news",
        "#news",
        ".announcements",
    ]

    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            # Look for list items or articles
            items = element.find_all(["li", "article", "div"], limit=10)
            for item in items:
                text = item.get_text(strip=True, separator=" ")
                if text and len(text) > 20:  # Meaningful content
                    news_items.append(text[:200])  # Limit length
            if news_items:
                return news_items[:10]

    # Fallback: look for "News" heading followed by content
    for heading in soup.find_all(["h1", "h2", "h3"]):
        heading_text = heading.get_text().lower()
        if any(
            keyword in heading_text
            for keyword in ["news", "updates", "latest", "announcements"]
        ):
            # Get next list or paragraphs
            next_elem = heading.find_next(["ul", "ol", "div"])
            if next_elem:
                items = next_elem.find_all(["li", "p"], limit=10)
                for item in items:
                    text = item.get_text(strip=True, separator=" ")
                    if text and len(text) > 20:
                        news_items.append(text[:200])
                if news_items:
                    return news_items[:10]

    return news_items


def extract_emails(text: str) -> list[str]:
    """Extract and filter email addresses from text.

    Args:
        text: Text content to extract emails from

    Returns:
        List of unique, filtered email addresses (normalized to lowercase)

    Story 4.3: Task 2
    """
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    emails = re.findall(pattern, text)

    # Normalize to lowercase for deduplication
    emails = [e.lower() for e in emails]

    # Filter generic emails
    generic_prefixes = (
        "webmaster@",
        "info@",
        "admin@",
        "support@",
        "contact@",
        "noreply@",
        "no-reply@",
    )
    filtered = [e for e in emails if not e.startswith(generic_prefixes)]

    # Remove duplicates (already normalized)
    return list(set(filtered))


def validate_email(email: str) -> bool:
    """Basic email format validation using regex.

    Args:
        email: Email address to validate

    Returns:
        True if email format is valid, False otherwise

    Story 4.3: Task 2
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def extract_contact_form(html: str, base_url: str) -> Optional[str]:
    """Extract contact form URL from HTML content.

    Args:
        html: Raw HTML content
        base_url: Base URL for converting relative links

    Returns:
        Absolute contact form URL if found, None otherwise

    Story 4.3: Task 3
    """
    contact_patterns = [
        r'href=["\']([^"\']*contact[^"\']*)["\']',
        r'href=["\']([^"\']*get-in-touch[^"\']*)["\']',
        r'href=["\']([^"\']*reach-out[^"\']*)["\']',
        r'href=["\']([^"\']*join[^"\']*)["\']',
    ]

    for pattern in contact_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            url = match.group(1)
            # Convert relative to absolute URL
            if not url.startswith(("http://", "https://")):
                url = urljoin(base_url, url)
            return url
    return None


def extract_application_url(html: str, base_url: str) -> Optional[str]:
    """Extract application/prospective student URL from HTML.

    Args:
        html: Raw HTML content
        base_url: Base URL for converting relative links

    Returns:
        Absolute application URL if found, None otherwise

    Story 4.3: Task 4
    """
    application_keywords = [
        "prospective",
        "apply",
        "join",
        "positions",
        "openings",
        "opportunities",
        "PhD application",
    ]

    for keyword in application_keywords:
        pattern = f"href=[\"']([^\"']*{keyword}[^\"']*)[\"']"
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            url = match.group(1)
            # Convert relative to absolute URL
            if not url.startswith(("http://", "https://")):
                url = urljoin(base_url, url)
            return url
    return None


def extract_contact_info_safe(website_content: str, lab_url: str) -> dict[str, Any]:
    """Safely extract contact info with error handling.

    Args:
        website_content: Full text content from lab website
        lab_url: Lab URL for relative→absolute conversion

    Returns:
        Dictionary with:
        - contact_emails: list[str]
        - contact_form_url: Optional[str]
        - application_url: Optional[str]
        - data_quality_flags: list[str]

    Story 4.3: Tasks 2-5
    """
    data_quality_flags = []

    try:
        emails = extract_emails(website_content)
    except Exception:
        emails = []
        data_quality_flags.append("email_extraction_failed")

    try:
        contact_form = extract_contact_form(website_content, lab_url)
    except Exception:
        contact_form = None
        data_quality_flags.append("contact_form_extraction_failed")

    try:
        application_url = extract_application_url(website_content, lab_url)
    except Exception:
        application_url = None
        data_quality_flags.append("application_url_extraction_failed")

    # Flag if no contact info found at all
    if not emails and not contact_form and not application_url:
        data_quality_flags.append("no_contact_info")
    else:
        # Flag specific missing fields
        if not emails:
            data_quality_flags.append("no_email")
        if not contact_form:
            data_quality_flags.append("no_contact_form")
        if not application_url:
            data_quality_flags.append("no_application_url")

    return {
        "contact_emails": emails,
        "contact_form_url": contact_form,
        "application_url": application_url,
        "data_quality_flags": data_quality_flags,
    }


async def process_single_lab(professor: Professor, correlation_id: str) -> Lab:
    """Process a single professor's lab.

    Orchestrates lab discovery, scraping, and data extraction.

    Args:
        professor: Professor record
        correlation_id: Correlation ID for logging

    Returns:
        Lab record with discovered/scraped data

    Story 4.1: Task 9
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="phase-4-labs",
        component="lab-research-agent",
    )

    # Discover lab URL
    lab_url = discover_lab_website(professor)

    # Use lab_name from professor if available, otherwise use default
    lab_name = professor.lab_name or f"{professor.name}'s Lab"

    # Generate lab ID
    lab_id = Lab.generate_id(professor.id, lab_name)

    # Initialize data quality flags
    data_quality_flags = []

    if not lab_url:
        # No website found - create minimal Lab record
        logger.info(
            "No website found for professor's lab",
            professor_name=professor.name,
            lab_name=lab_name,
        )
        data_quality_flags.append("no_website")

        lab = Lab(
            id=lab_id,
            professor_id=professor.id,
            professor_name=professor.name,
            department=professor.department_name,
            lab_name=lab_name,
            lab_url=None,
            last_updated=None,
            description="",
            research_focus=[],
            news_updates=[],
            lab_members=[],
            publications_list=[],
            website_content="",
            data_quality_flags=data_quality_flags,
            last_wayback_snapshot=None,
            wayback_snapshots=[],
            update_frequency="unknown",
            contact_emails=[],
            contact_form_url=None,
            application_url=None,
        )

        # Story 4.4: Apply website status detection
        apply_website_status(lab, correlation_id)

        return lab

    # Scrape lab website
    try:
        scraped_data = await scrape_lab_website(lab_url, correlation_id)
        data_quality_flags.extend(scraped_data["data_quality_flags"])

        logger.info(
            "Lab website scraped successfully",
            professor_name=professor.name,
            lab_url=lab_url,
        )

        # Contact info now extracted in scrape_lab_website() as part of 5 categories
        # Data quality flags already included in scraped_data["data_quality_flags"]

        lab = Lab(
            id=lab_id,
            professor_id=professor.id,
            professor_name=professor.name,
            department=professor.department_name,
            lab_name=lab_name,
            lab_url=lab_url,
            last_updated=scraped_data["last_updated"],
            description=scraped_data["description"],
            research_focus=scraped_data["research_focus"],
            news_updates=scraped_data["news_updates"],
            lab_members=scraped_data["lab_members"],  # NEW
            publications_list=scraped_data["publications_list"],  # NEW
            website_content=scraped_data["website_content"],
            data_quality_flags=data_quality_flags,
            last_wayback_snapshot=None,
            wayback_snapshots=[],
            update_frequency="unknown",
            # Story 4.3: Contact fields (now from scraped_data)
            contact_emails=scraped_data["contact_emails"],
            contact_form_url=scraped_data["contact_form_url"],
            application_url=scraped_data["application_url"],
        )

        # Story 4.2: Enrich with Archive.org data
        lab = await enrich_with_archive_data(lab, correlation_id)

        # Story 4.4: Apply website status detection
        apply_website_status(lab, correlation_id)

        return lab

    except Exception as e:
        logger.error(
            "Lab website scraping failed",
            professor_name=professor.name,
            lab_url=lab_url,
            error=str(e),
        )
        data_quality_flags.append("scraping_failed")

        lab = Lab(
            id=lab_id,
            professor_id=professor.id,
            professor_name=professor.name,
            department=professor.department_name,
            lab_name=lab_name,
            lab_url=lab_url,
            last_updated=None,
            description="",
            research_focus=[],
            news_updates=[],
            lab_members=[],
            publications_list=[],
            website_content="",
            data_quality_flags=data_quality_flags,
            last_wayback_snapshot=None,
            wayback_snapshots=[],
            update_frequency="unknown",
            contact_emails=[],
            contact_form_url=None,
            application_url=None,
        )

        # Story 4.2: Try to enrich with Archive.org data even if scraping failed
        lab = await enrich_with_archive_data(lab, correlation_id)

        # Story 4.4: Apply website status detection
        apply_website_status(lab, correlation_id)

        return lab


def calculate_update_frequency(snapshots: list[datetime]) -> str:
    """Calculate website update frequency from snapshot dates.

    Analyzes intervals between snapshots to determine update frequency.

    Args:
        snapshots: List of snapshot datetime objects (sorted chronologically)

    Returns:
        Frequency category: "weekly", "monthly", "quarterly", "yearly", "stale", or "unknown"

    Story 4.2: Task 8
    """
    if len(snapshots) < 2:
        return "unknown"

    # Calculate intervals between consecutive snapshots
    intervals = []
    for i in range(1, len(snapshots)):
        delta = (snapshots[i] - snapshots[i - 1]).days
        intervals.append(delta)

    # Calculate average interval
    avg_interval = sum(intervals) / len(intervals)

    # Classify based on average interval
    if avg_interval < 30:
        return "weekly"
    elif avg_interval < 90:
        return "monthly"
    elif avg_interval < 180:
        return "quarterly"
    elif avg_interval < 545:
        return "yearly"
    else:
        return "stale"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
)
async def query_wayback_snapshots(
    url: str, correlation_id: str, years: int = 3
) -> list[dict[str, Any]]:
    """Query Wayback Machine API for snapshot history.

    Args:
        url: Website URL to query
        correlation_id: Correlation ID for logging
        years: Number of years to look back (default: 3)

    Returns:
        List of snapshot dictionaries with 'datetime' and 'archive_url' keys

    Raises:
        Exception: If API query fails after retries

    Story 4.2: Task 5
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="phase-4-labs",
        component="archive-integration",
    )

    # Apply rate limiting before API request (Task 3)
    await rate_limiter.acquire("https://web.archive.org/cdx/search")
    logger.debug("Rate limit applied for Archive.org")

    try:
        # Initialize Wayback Machine CDX API
        cdx = WaybackMachineCDXServerAPI(
            url=url, user_agent="LabFinder/1.0 (Research Lab Discovery)"
        )

        # Get snapshots from past N years
        from_date = datetime.now().replace(year=datetime.now().year - years)

        snapshots_list = []
        for snapshot in cdx.snapshots():
            # Filter to requested time range
            if snapshot.datetime_timestamp >= from_date:
                snapshots_list.append(
                    {
                        "datetime": snapshot.datetime_timestamp,
                        "archive_url": snapshot.archive_url,
                        "original_url": snapshot.original,
                    }
                )

        logger.info(
            "Archive.org query successful", url=url, snapshots_found=len(snapshots_list)
        )
        return snapshots_list

    except NoCDXRecordFound:
        # No archived versions found (Task 4: Handle Missing Archive Data)
        logger.info("No Archive.org snapshots found", url=url)
        return []

    except Exception as e:
        logger.error("Archive.org API query failed", url=url, error=str(e))
        raise  # Will trigger retry via @retry decorator


async def enrich_with_archive_data(lab: Lab, correlation_id: str) -> Lab:
    """Enrich lab record with Archive.org website history data.

    Queries Wayback Machine for:
    - Most recent snapshot date
    - Snapshot history over past 3 years
    - Calculated update frequency

    Args:
        lab: Lab record to enrich
        correlation_id: Correlation ID for logging

    Returns:
        Lab record with archive fields populated

    Story 4.2: Task 9
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="phase-4-labs",
        component="archive-integration",
    )

    # Skip if lab has no website
    if not lab.lab_url:
        return lab

    try:
        # Query Wayback snapshots (Tasks 5, 6, 7)
        snapshots = await query_wayback_snapshots(
            url=lab.lab_url, correlation_id=correlation_id, years=3
        )

        # Handle case with no archive data (Task 4)
        if not snapshots:
            lab.data_quality_flags.append("no_archive_data")
            logger.info(
                "No archive data available", lab_url=lab.lab_url, lab_name=lab.lab_name
            )
            return lab

        # Extract snapshot dates
        snapshot_dates = [s["datetime"] for s in snapshots]
        snapshot_dates.sort()  # Ensure chronological order

        # Task 6: Find most recent snapshot
        lab.last_wayback_snapshot = snapshot_dates[-1] if snapshot_dates else None

        # Task 7: Store 3-year snapshot history
        lab.wayback_snapshots = snapshot_dates

        # Task 8: Calculate update frequency
        lab.update_frequency = calculate_update_frequency(snapshot_dates)

        logger.info(
            "Archive data enrichment complete",
            lab_url=lab.lab_url,
            lab_name=lab.lab_name,
            snapshots_count=len(snapshot_dates),
            update_frequency=lab.update_frequency,
            last_snapshot=lab.last_wayback_snapshot.isoformat()
            if lab.last_wayback_snapshot
            else None,
        )

        return lab

    except Exception as e:
        # Task 4: Handle API failures gracefully
        lab.data_quality_flags.append("archive_query_failed")
        logger.error(
            "Archive.org query failed for lab",
            lab_url=lab.lab_url,
            lab_name=lab.lab_name,
            error=str(e),
        )
        # Return lab with failure flag, don't block processing
        return lab


def determine_website_status(lab: Lab) -> str:
    """Determine website status based on update dates.

    Args:
        lab: Lab record to analyze

    Returns:
        Status string: "missing", "unavailable", "stale", "aging", "active", or "unknown"

    Story 4.4: Tasks 2-3
    """
    # Task 2: Check for missing website
    if not lab.lab_url:
        return "missing"

    # Task 2: Check if scraping failed (reuses Story 4.1 flag)
    if "scraping_failed" in lab.data_quality_flags:
        return "unavailable"

    # Task 3: Identify stale websites
    # Prefer actual update date, fallback to Archive.org
    last_update = lab.last_updated or lab.last_wayback_snapshot

    if not last_update:
        return "unknown"

    # Use timezone-aware datetime for safe comparison
    now = datetime.now(timezone.utc)

    # Ensure last_update is timezone-aware; if naive, assume UTC
    if last_update.tzinfo is None:
        last_update = last_update.replace(tzinfo=timezone.utc)

    age_days = (now - last_update).days

    # Task 3: Classify based on age
    if age_days > 730:  # >2 years
        return "stale"
    elif age_days > 365:  # 1-2 years
        return "aging"
    else:  # <1 year
        return "active"


def apply_alternative_data_strategy(lab: Lab) -> None:
    """Configure lab to use alternative data sources.

    Modifies lab record in-place to flag for publication-based analysis
    when website data is missing, stale, or unavailable.

    Args:
        lab: Lab record to update

    Story 4.4: Task 4
    """
    if lab.website_status in ["missing", "stale", "unavailable"]:
        # Flag for publication-based analysis (Epic 5)
        if "using_publication_data" not in lab.data_quality_flags:
            lab.data_quality_flags.append("using_publication_data")

        # Flag for member inference from co-authorship (Story 5.5)
        if "members_will_be_inferred" not in lab.data_quality_flags:
            lab.data_quality_flags.append("members_will_be_inferred")


def apply_website_status(lab: Lab, correlation_id: str) -> None:
    """Apply website status detection and alternative data strategy.

    Wraps status detection with error handling (Task 5).

    Args:
        lab: Lab record to process (modified in-place)
        correlation_id: Correlation ID for logging

    Story 4.4: Tasks 2-5
    """
    logger = get_logger(
        correlation_id=correlation_id, phase="phase-4-labs", component="website-status"
    )

    try:
        # Task 2-3: Determine website status
        status = determine_website_status(lab)
        lab.website_status = status

        # Add appropriate data quality flags
        if status == "stale":
            if "stale_website" not in lab.data_quality_flags:
                lab.data_quality_flags.append("stale_website")
        elif status == "aging":
            if "aging_website" not in lab.data_quality_flags:
                lab.data_quality_flags.append("aging_website")

        # Task 4: Apply alternative data strategy
        apply_alternative_data_strategy(lab)

        logger.info(
            "Website status applied",
            lab_name=lab.lab_name,
            website_status=status,
            using_alternative_data="using_publication_data" in lab.data_quality_flags,
        )

    except Exception as e:
        # Task 5: Graceful error handling - default to unknown
        logger.error(
            "Website status detection failed", lab_name=lab.lab_name, error=str(e)
        )
        lab.website_status = "unknown"
        if "status_detection_failed" not in lab.data_quality_flags:
            lab.data_quality_flags.append("status_detection_failed")


def generate_missing_website_report(
    labs: list[Lab], output_path: str = "output/missing-websites.md"
) -> None:
    """Generate report for labs with missing or stale websites.

    Args:
        labs: List of Lab records
        output_path: Path to output markdown file

    Story 4.4: Task 6
    """

    # Calculate statistics
    total_labs = len(labs)
    active_labs = [lab for lab in labs if lab.website_status == "active"]
    aging_labs = [lab for lab in labs if lab.website_status == "aging"]
    stale_labs = [lab for lab in labs if lab.website_status == "stale"]
    missing_labs = [lab for lab in labs if lab.website_status == "missing"]
    unavailable_labs = [lab for lab in labs if lab.website_status == "unavailable"]

    # Build report content
    report = ["# Labs with Missing or Stale Websites\n"]
    report.append("## Summary\n")
    report.append(f"- Total labs analyzed: {total_labs}\n")
    report.append(
        f"- Labs with active websites (<1 year): {len(active_labs)} ({len(active_labs) / total_labs * 100:.1f}%)\n"
    )
    report.append(
        f"- Labs with aging websites (1-2 years): {len(aging_labs)} ({len(aging_labs) / total_labs * 100:.1f}%)\n"
    )
    report.append(
        f"- Labs with stale websites (>2 years): {len(stale_labs)} ({len(stale_labs) / total_labs * 100:.1f}%)\n"
    )
    report.append(
        f"- Labs with missing websites: {len(missing_labs)} ({len(missing_labs) / total_labs * 100:.1f}%)\n"
    )
    report.append(
        f"- Labs with unavailable websites: {len(unavailable_labs)} ({len(unavailable_labs) / total_labs * 100:.1f}%)\n"
    )
    report.append("\n")

    # Missing websites section
    if missing_labs:
        report.append("## Missing Websites\n\n")
        report.append("| Lab | Professor | Department | Alternative Data | Flags |\n")
        report.append("|-----|-----------|------------|------------------|-------|\n")
        for lab in missing_labs:
            using_pubs = (
                "✅ Publications"
                if "using_publication_data" in lab.data_quality_flags
                else "❌ No data"
            )
            members_inferred = (
                ", ⚠️ Members inferred"
                if "members_will_be_inferred" in lab.data_quality_flags
                else ""
            )
            alt_data = f"{using_pubs}{members_inferred}"
            flags = ", ".join(
                [
                    f
                    for f in lab.data_quality_flags
                    if f
                    in [
                        "no_website",
                        "using_publication_data",
                        "members_will_be_inferred",
                    ]
                ]
            )
            report.append(
                f"| {lab.lab_name} | {lab.professor_name} | {lab.department} | {alt_data} | `{flags}` |\n"
            )
        report.append("\n")

    # Stale websites section
    if stale_labs:
        report.append("## Stale Websites (>2 years old)\n\n")
        report.append("| Lab | Professor | Last Updated | Alternative Data | Flags |\n")
        report.append("|-----|-----------|--------------|------------------|-------|\n")
        for lab in stale_labs:
            last_update = lab.last_updated or lab.last_wayback_snapshot
            last_update_str = (
                last_update.strftime("%Y-%m-%d") if last_update else "Unknown"
            )
            using_pubs = (
                "✅ Publications"
                if "using_publication_data" in lab.data_quality_flags
                else "❌ No data"
            )
            members_inferred = (
                ", ⚠️ Members inferred"
                if "members_will_be_inferred" in lab.data_quality_flags
                else ""
            )
            alt_data = f"{using_pubs}{members_inferred}"
            flags = ", ".join(
                [
                    f
                    for f in lab.data_quality_flags
                    if f
                    in [
                        "stale_website",
                        "using_publication_data",
                        "members_will_be_inferred",
                    ]
                ]
            )
            report.append(
                f"| {lab.lab_name} | {lab.professor_name} | {last_update_str} | {alt_data} | `{flags}` |\n"
            )
        report.append("\n")

    # Aging websites section
    if aging_labs:
        report.append("## Aging Websites (1-2 years old)\n\n")
        report.append("| Lab | Professor | Last Updated | Status | Notes |\n")
        report.append("|-----|-----------|--------------|--------|-------|\n")
        for lab in aging_labs:
            last_update = lab.last_updated or lab.last_wayback_snapshot
            last_update_str = (
                last_update.strftime("%Y-%m-%d") if last_update else "Unknown"
            )
            report.append(
                f"| {lab.lab_name} | {lab.professor_name} | {last_update_str} | ⚠️ Monitor | May need alternative data soon |\n"
            )
        report.append("\n")

    # Unavailable websites section
    if unavailable_labs:
        report.append("## Unavailable Websites (URL exists but scraping failed)\n\n")
        report.append("| Lab | Professor | URL | Alternative Data | Flags |\n")
        report.append("|-----|-----------|-----|------------------|-------|\n")
        for lab in unavailable_labs:
            using_pubs = (
                "✅ Publications"
                if "using_publication_data" in lab.data_quality_flags
                else "❌ No data"
            )
            members_inferred = (
                ", ⚠️ Members inferred"
                if "members_will_be_inferred" in lab.data_quality_flags
                else ""
            )
            alt_data = f"{using_pubs}{members_inferred}"
            flags = ", ".join(
                [
                    f
                    for f in lab.data_quality_flags
                    if f
                    in [
                        "scraping_failed",
                        "using_publication_data",
                        "members_will_be_inferred",
                    ]
                ]
            )
            report.append(
                f"| {lab.lab_name} | {lab.professor_name} | {lab.lab_url or 'N/A'} | {alt_data} | `{flags}` |\n"
            )
        report.append("\n")

    # Footer note
    report.append(
        "**Note:** Labs with missing/stale/unavailable websites will rely on publication data and co-authorship inference for analysis. These labs are NOT excluded from fitness scoring.\n"
    )

    # Write report to file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("".join(report))


async def discover_and_scrape_labs_batch() -> list[Lab]:
    """Discover and scrape lab websites for all filtered professors.

    Main orchestrator function that:
    1. Loads filtered professors from Epic 3 checkpoints
    2. Checks for resume point
    3. Processes labs in batches
    4. Saves checkpoints after each batch
    5. Returns all lab records

    Returns:
        List of Lab records

    Story 4.1: Task 10
    """
    import uuid
    from src.models.professor import Professor
    from src.utils.progress_tracker import ProgressTracker

    # Generate orchestrator correlation ID
    orchestrator_id = f"lab-discovery-orchestrator-{uuid.uuid4()}"
    logger = get_logger(
        correlation_id=orchestrator_id,
        phase="phase-4-labs",
        component="lab-research-agent",
    )

    logger.info("Starting lab discovery and scraping batch process")

    # Load system parameters for batch size
    system_params = SystemParams.load()
    batch_size = system_params.batch_config.lab_discovery_batch_size

    # Initialize checkpoint manager
    checkpoint_manager = CheckpointManager()

    # Task 1: Check for resume point
    resume_batch_id = checkpoint_manager.get_resume_point("phase-4-labs")
    existing_labs: list[Lab] = []

    if resume_batch_id > 1:
        # Load existing labs from completed batches
        logger.info("Resuming from checkpoint", resume_batch_id=resume_batch_id)
        existing_lab_batches = checkpoint_manager.load_batches("phase-4-labs")
        for batch in existing_lab_batches:
            for lab_data in batch:
                if isinstance(lab_data, dict):
                    existing_labs.append(Lab(**lab_data))
    else:
        logger.info("Starting fresh (no checkpoints found)")

    # Load filtered professors from Epic 3 (Story 3.5)
    logger.info("Loading filtered professors from Epic 3")
    try:
        professor_batches = checkpoint_manager.load_batches("phase-2-filter")
    except FileNotFoundError:
        logger.warning(
            "No filtered professors found in checkpoints. "
            "Epic 3 (Professor Filtering) must be completed first."
        )
        return []

    # Flatten batches into single list
    all_professors: list[Professor] = []
    for batch in professor_batches:
        for prof_data in batch:
            if isinstance(prof_data, dict):
                all_professors.append(Professor(**prof_data))

    logger.info("Loaded professors", total_professors=len(all_professors))

    if not all_professors:
        logger.warning("No professors to process")
        return existing_labs

    # Initialize progress tracker (Task 11)
    tracker = ProgressTracker()
    tracker.start_phase(
        "Phase 4: Lab Website Discovery", total_items=len(all_professors)
    )

    # Divide into batches
    total_batches = (len(all_professors) + batch_size - 1) // batch_size

    all_labs = existing_labs.copy()
    processed_count = (resume_batch_id - 1) * batch_size

    for batch_num in range(resume_batch_id, total_batches + 1):
        start_idx = (batch_num - 1) * batch_size
        end_idx = min(start_idx + batch_size, len(all_professors))
        batch_professors = all_professors[start_idx:end_idx]

        # Generate batch correlation ID
        batch_correlation_id = f"lab-discovery-batch-{batch_num}-{uuid.uuid4()}"

        logger.info(
            "Processing batch",
            batch_num=batch_num,
            total_batches=total_batches,
            professors_in_batch=len(batch_professors),
        )

        # Update progress tracker
        tracker.update_batch(
            batch_num=batch_num,
            total_batches=total_batches,
            batch_desc=f"Labs {start_idx + 1}-{end_idx}",
        )

        # Process each professor in batch
        batch_labs = []
        for professor in batch_professors:
            try:
                lab = await process_single_lab(professor, batch_correlation_id)
                batch_labs.append(lab)
                processed_count += 1
                tracker.update(completed=processed_count)

            except Exception as e:
                logger.error(
                    "Failed to process lab for professor",
                    professor_name=professor.name,
                    error=str(e),
                )
                # Create minimal lab record with failure flag
                lab = Lab(
                    id=Lab.generate_id(professor.id, professor.name + "'s Lab"),
                    professor_id=professor.id,
                    professor_name=professor.name,
                    department=professor.department_name,
                    lab_name=professor.name + "'s Lab",
                    lab_url=None,
                    last_updated=None,
                    data_quality_flags=["scraping_failed"],
                    last_wayback_snapshot=None,
                    wayback_snapshots=[],
                    update_frequency="unknown",
                    contact_emails=[],
                    contact_form_url=None,
                    application_url=None,
                )
                # Story 4.4: Apply website status detection
                apply_website_status(lab, batch_correlation_id)
                batch_labs.append(lab)
                processed_count += 1
                tracker.update(completed=processed_count)

        # Save batch checkpoint
        try:
            checkpoint_manager.save_batch(
                phase="phase-4-labs", batch_id=batch_num, data=batch_labs
            )
            logger.info(
                "Batch checkpoint saved",
                batch_num=batch_num,
                labs_count=len(batch_labs),
            )
        except Exception as e:
            logger.error(
                "Failed to save batch checkpoint", batch_num=batch_num, error=str(e)
            )
            raise  # Re-raise to maintain data consistency

        all_labs.extend(batch_labs)

        # Count missing websites for logging
        missing_count = sum(
            1 for lab in batch_labs if "no_website" in lab.data_quality_flags
        )
        logger.info(
            "Batch complete",
            batch_num=batch_num,
            labs_discovered=len(batch_labs),
            missing_websites=missing_count,
        )

    # Complete phase tracking
    tracker.complete_phase()

    logger.info(
        "Lab discovery complete",
        total_labs=len(all_labs),
        total_missing_websites=sum(
            1 for lab in all_labs if "no_website" in lab.data_quality_flags
        ),
    )

    # Story 4.4: Generate missing website report (Task 6)
    try:
        generate_missing_website_report(all_labs)
        logger.info("Missing website report generated")
    except Exception as e:
        logger.error("Failed to generate missing website report", error=str(e))

    return all_labs
