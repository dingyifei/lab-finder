"""
Lab Research Agent

Discovers and scrapes lab websites for content and metadata.
Story 4.1: Epic 4 (Lab Intelligence)
"""

import json
import re
from datetime import datetime
from typing import Optional, Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, TextBlock
from playwright.async_api import async_playwright
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
)

from src.models.lab import Lab
from src.models.professor import Professor
from src.models.config import SystemParams
from src.utils.logger import get_logger
from src.utils.checkpoint_manager import CheckpointManager


# Data quality flags for lab records
LAB_DATA_QUALITY_FLAGS = {
    "no_website",  # No lab URL found
    "scraping_failed",  # Web scraping failed
    "playwright_fallback",  # Used Playwright instead of built-in tools
    "missing_last_updated",  # No last updated date found
    "missing_description",  # No description extracted
    "missing_research_focus",  # No research focus found
    "missing_news",  # No news/updates found
}


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
    """Scrape lab website for content and metadata.

    Uses built-in web tools first, falls back to Playwright if needed.

    Args:
        lab_url: Lab website URL
        correlation_id: Correlation ID for logging

    Returns:
        Dictionary with extracted content:
        - description: Lab overview/description
        - research_focus: List of research areas
        - news_updates: List of recent news items
        - website_content: Full page text
        - last_updated: Last update date (if found)
        - data_quality_flags: List of quality issues

    Raises:
        Exception: If scraping fails after retries

    Story 4.1: Task 4
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="phase-4-labs",
        component="lab-research-agent"
    )

    # Configure Claude Agent SDK with web scraping tools
    options = ClaudeAgentOptions(
        allowed_tools=["WebFetch"],
        max_turns=2,
        system_prompt=(
            "You are a web scraping assistant specialized in extracting "
            "research lab website content and metadata."
        ),
        setting_sources=None,  # CRITICAL: Prevents codebase context injection
    )

    prompt = f"""
Scrape the lab website at: {lab_url}

Extract the following information:
1. Lab description/overview - main description of the lab's purpose and focus
2. Research focus areas - list of research topics/areas/themes
3. Recent news/updates - headlines or summaries of recent news items (last 5-10)
4. Last updated date - if available in metadata, footer, or "last modified" text
5. Full page text content - all visible text for analysis

Return results as a JSON object with this format:
{{
  "description": "Lab overview text here",
  "research_focus": ["Area 1", "Area 2", "Area 3"],
  "news_updates": ["News 1", "News 2", "News 3"],
  "last_updated": "2025-10-01" or null if not found,
  "website_content": "Full page text content"
}}

Look for common selectors:
- Description: .lab-overview, #about, .description, section.about
- Research: .research-areas, #research, .focus, .topics
- News: .news, .updates, #latest, section.news
- Last Updated: meta[name='last-modified'], .last-updated, footer
"""

    try:
        # Use ClaudeSDKClient for web scraping
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            full_response = ""
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_response += block.text

        # Parse JSON response
        parsed_data = parse_lab_content(full_response)

        # Extract last_updated if present
        last_updated = None
        if parsed_data.get("last_updated"):
            last_updated = parse_date_string(str(parsed_data["last_updated"]))

        data_quality_flags: list[str] = []

        # Add quality flags for missing data
        description = str(parsed_data.get("description", ""))
        research_focus = (
            parsed_data.get("research_focus", [])
            if isinstance(parsed_data.get("research_focus"), list)
            else []
        )
        news_updates = (
            parsed_data.get("news_updates", [])
            if isinstance(parsed_data.get("news_updates"), list)
            else []
        )
        website_content = str(parsed_data.get("website_content", ""))

        if not description:
            data_quality_flags.append("missing_description")
        if not research_focus:
            data_quality_flags.append("missing_research_focus")
        if not news_updates:
            data_quality_flags.append("missing_news")
        if not last_updated:
            data_quality_flags.append("missing_last_updated")

        result = {
            "description": description,
            "research_focus": research_focus,
            "news_updates": news_updates,
            "website_content": website_content,
            "last_updated": last_updated,
            "data_quality_flags": data_quality_flags,
        }

        logger.info("Lab website scraped successfully", lab_url=lab_url)
        return result

    except Exception as e:
        logger.warning("WebFetch failed, falling back to Playwright", error=str(e))
        return await scrape_with_playwright_fallback(lab_url, correlation_id)


def parse_lab_content(response_text: str) -> dict[str, Any]:
    """Parse JSON from Claude's response text.

    Extracts JSON object from response, handling markdown code blocks.

    Args:
        response_text: Response text from Claude

    Returns:
        Parsed data dictionary

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
        return json.loads(json_str)
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


async def scrape_with_playwright_fallback(
    lab_url: str, correlation_id: str
) -> dict[str, Any]:
    """Fallback to Playwright when WebFetch fails.

    Args:
        lab_url: Lab website URL
        correlation_id: Correlation ID for logging

    Returns:
        Dictionary with scraped content and playwright_fallback flag

    Raises:
        Exception: If Playwright also fails
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="phase-4-labs",
        component="lab-research-agent"
    )
    logger.info("Using Playwright fallback", lab_url=lab_url)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Set timeout to 30 seconds
            await page.goto(lab_url, timeout=30000, wait_until="networkidle")
            html_content = await page.content()
            text_content = await page.inner_text("body")

            await browser.close()

            # Extract content from HTML
            description = extract_lab_description(html_content)
            research_focus = extract_research_focus(html_content)
            news_updates = extract_news_updates(html_content)
            last_updated = extract_last_updated(html_content)

            data_quality_flags = ["playwright_fallback"]

            # Add quality flags for missing data
            if not description:
                data_quality_flags.append("missing_description")
            if not research_focus:
                data_quality_flags.append("missing_research_focus")
            if not news_updates:
                data_quality_flags.append("missing_news")
            if not last_updated:
                data_quality_flags.append("missing_last_updated")

            result = {
                "description": description,
                "research_focus": research_focus,
                "news_updates": news_updates,
                "website_content": text_content,
                "last_updated": last_updated,
                "data_quality_flags": data_quality_flags,
            }

            logger.info("Playwright fallback successful", lab_url=lab_url)
            return result

    except Exception as e:
        logger.error("Playwright fallback failed", lab_url=lab_url, error=str(e))
        return {
            "description": "",
            "research_focus": [],
            "news_updates": [],
            "website_content": "",
            "last_updated": None,
            "data_quality_flags": ["scraping_failed"],
        }


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


async def process_single_lab(
    professor: Professor, correlation_id: str
) -> Lab:
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
        component="lab-research-agent"
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
            lab_name=lab_name
        )
        data_quality_flags.append("no_website")

        return Lab(
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
            website_content="",
            data_quality_flags=data_quality_flags,
        )

    # Scrape lab website
    try:
        scraped_data = await scrape_lab_website(lab_url, correlation_id)
        data_quality_flags.extend(scraped_data["data_quality_flags"])

        logger.info(
            "Lab website scraped successfully",
            professor_name=professor.name,
            lab_url=lab_url
        )

        return Lab(
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
            website_content=scraped_data["website_content"],
            data_quality_flags=data_quality_flags,
        )

    except Exception as e:
        logger.error(
            "Lab website scraping failed",
            professor_name=professor.name,
            lab_url=lab_url,
            error=str(e)
        )
        data_quality_flags.append("scraping_failed")

        return Lab(
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
            website_content="",
            data_quality_flags=data_quality_flags,
        )


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
        component="lab-research-agent"
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
        logger.info(
            "Resuming from checkpoint",
            resume_batch_id=resume_batch_id
        )
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

    logger.info(
        "Loaded professors",
        total_professors=len(all_professors)
    )

    if not all_professors:
        logger.warning("No professors to process")
        return existing_labs

    # Initialize progress tracker (Task 11)
    tracker = ProgressTracker()
    tracker.start_phase(
        "Phase 4: Lab Website Discovery",
        total_items=len(all_professors)
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
            professors_in_batch=len(batch_professors)
        )

        # Update progress tracker
        tracker.update_batch(
            batch_num=batch_num,
            total_batches=total_batches,
            batch_desc=f"Labs {start_idx + 1}-{end_idx}"
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
                    error=str(e)
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
                )
                batch_labs.append(lab)
                processed_count += 1
                tracker.update(completed=processed_count)

        # Save batch checkpoint
        try:
            checkpoint_manager.save_batch(
                phase="phase-4-labs",
                batch_id=batch_num,
                data=batch_labs
            )
            logger.info(
                "Batch checkpoint saved",
                batch_num=batch_num,
                labs_count=len(batch_labs)
            )
        except Exception as e:
            logger.error(
                "Failed to save batch checkpoint",
                batch_num=batch_num,
                error=str(e)
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
            missing_websites=missing_count
        )

    # Complete phase tracking
    tracker.complete_phase()

    logger.info(
        "Lab discovery complete",
        total_labs=len(all_labs),
        total_missing_websites=sum(
            1 for lab in all_labs if "no_website" in lab.data_quality_flags
        )
    )

    return all_labs
