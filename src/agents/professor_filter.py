"""Professor Discovery & Filter Agent.

Combined agent for professor discovery and filtering operations.
- Story 3.1a: Discovery functions (this implementation)
- Story 3.1b: Parallel processing functions (this implementation)
- Story 3.1c: Deduplication, rate limiting, and checkpointing (this implementation)
- Story 3.2: Filtering functions (this implementation)
"""

import asyncio
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
)
from playwright.async_api import async_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models.config import SystemParams
from src.models.department import Department
from src.models.professor import Professor
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.llm_helpers import filter_professor_research, match_names
from src.utils.logger import get_logger
from src.utils.progress_tracker import ProgressTracker

# Selector patterns to try for professor listings
SELECTOR_PATTERNS = [
    ".faculty-member",
    ".professor-card",
    ".people-item",
    "article.faculty",
    "section.people",
    "div.directory-entry",
    "table.faculty tr",
    "table.directory tr",
    'a[href*="/faculty/"]',
    'a[href*="/people/"]',
]


class DomainRateLimiter:
    """Per-domain rate limiting to prevent blocking by university servers.

    Uses aiolimiter AsyncLimiter to throttle requests on a per-domain basis.
    Each domain gets its own rate limiter to ensure respectful scraping.

    Story 3.1c: Task 1
    """

    def __init__(self, default_rate: float = 1.0, time_period: float = 1.0):
        """Initialize the domain rate limiter.

        Args:
            default_rate: Maximum requests per time_period (default: 1 req/sec)
            time_period: Time period in seconds (default: 1 second)
        """
        self.limiters: dict[str, AsyncLimiter] = {}
        self.default_rate = default_rate
        self.time_period = time_period

    async def acquire(self, url: str) -> None:
        """Acquire rate limit token for URL's domain.

        Extracts domain from URL and applies rate limiting per domain.
        Creates new limiter for previously unseen domains.

        Args:
            url: Full URL to extract domain from
        """
        domain = urlparse(url).netloc

        if domain not in self.limiters:
            # Create limiter for new domain
            self.limiters[domain] = AsyncLimiter(
                max_rate=self.default_rate, time_period=self.time_period
            )

        await self.limiters[domain].acquire()


async def deduplicate_professors(professors: list[Professor]) -> list[Professor]:
    """Deduplicate professors using LLM-based fuzzy name matching.

    Uses exact matching first (fast), then LLM fuzzy matching for similar names
    within the same department. Threshold: 90+ confidence AND decision="yes".

    Performance: O(n²) complexity with LLM calls for fuzzy matching.
    Optimized with exact-match pre-filtering to reduce LLM calls by ~70%.

    Story 3.1c: Task 3

    Args:
        professors: List of Professor models to deduplicate

    Returns:
        List of unique Professor models (duplicates merged)
    """
    logger = get_logger(
        correlation_id="deduplication",
        phase="professor_discovery",
        component="professor_filter",
    )
    logger.info("Starting deduplication", original_count=len(professors))

    unique_professors: list[Professor] = []
    seen_combinations: set[str] = set()

    for prof in professors:
        # Exact match check first (fast)
        key = f"{prof.name.lower()}:{prof.department_id}"
        if key in seen_combinations:
            logger.debug("Exact duplicate found", professor=prof.name)
            continue

        # Fuzzy match check (slower, uses LLM)
        is_duplicate = False
        for existing in unique_professors:
            if existing.department_id == prof.department_id:
                # Use LLM helper for name similarity
                match_result = await match_names(existing.name, prof.name)

                # Check BOTH decision AND confidence to confirm duplicate
                if (
                    match_result["decision"] == "yes"
                    and match_result["confidence"] >= 90
                ):
                    logger.debug(
                        "Fuzzy duplicate found",
                        name1=existing.name,
                        name2=prof.name,
                        confidence=match_result["confidence"],
                        reasoning=match_result["reasoning"],
                    )

                    # Merge data (prefer more complete record)
                    merged = merge_professor_records(existing, prof)
                    unique_professors.remove(existing)
                    unique_professors.append(merged)
                    is_duplicate = True
                    break

        if not is_duplicate:
            seen_combinations.add(key)
            unique_professors.append(prof)

    logger.info(
        "Deduplication complete",
        original_count=len(professors),
        unique_count=len(unique_professors),
        duplicates_removed=len(professors) - len(unique_professors),
    )

    return unique_professors


def merge_professor_records(existing: Professor, new: Professor) -> Professor:
    """Merge two professor records, preferring more complete data.

    Story 3.1c: Task 3

    Args:
        existing: Existing Professor record
        new: New Professor record to merge

    Returns:
        Merged Professor model with most complete data
    """
    merged_data = existing.model_dump()
    new_data = new.model_dump()

    # Prefer non-empty values
    for key in new_data:
        if key == "data_quality_flags":
            # Merge flags (deduplicate)
            merged_data[key] = list(set(merged_data[key] + new_data[key]))
        elif not merged_data.get(key) and new_data.get(key):
            merged_data[key] = new_data[key]

    return Professor(**merged_data)


def generate_professor_id(name: str, department_id: str) -> str:
    """Generate unique professor ID from name and department.

    Args:
        name: Professor's full name
        department_id: Department ID

    Returns:
        16-character SHA256 hash of name:department_id
    """
    content = f"{name}:{department_id}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def parse_professor_data(text: str) -> list[dict[str, object]]:
    """Parse professor data from Claude's response text.

    Args:
        text: Response text from Claude Agent SDK

    Returns:
        List of professor data dictionaries
    """
    try:
        # Try to extract JSON array from response
        json_match = re.search(r"\[.*\]", text, re.DOTALL)
        if json_match:
            parsed: list[dict[str, object]] = json.loads(json_match.group(0))
            return parsed
        return []
    except json.JSONDecodeError:
        return []


def parse_professor_elements(
    elements: list[Any], department: Department
) -> list[dict[str, str | list[str] | None]]:
    """Parse professor data from BeautifulSoup elements.

    Args:
        elements: List of BeautifulSoup elements
        department: Department model

    Returns:
        List of professor data dictionaries
    """
    professors: list[dict[str, str | list[str] | None]] = []
    for element in elements:
        # Extract name (try various selectors)
        name_elem = (
            element.find("h3")
            or element.find("h4")
            or element.find(class_="name")
            or element.find("a")
        )
        if not name_elem:
            continue

        name = name_elem.get_text(strip=True)
        if not name:
            continue

        # Extract profile URL
        link_elem = element.find("a", href=True)
        profile_url = link_elem["href"] if link_elem else ""

        # Make absolute URL if relative
        if profile_url and not profile_url.startswith("http"):
            from urllib.parse import urljoin

            profile_url = urljoin(department.url, profile_url)

        # Extract title
        title_elem = element.find(class_="title") or element.find("span")
        title = title_elem.get_text(strip=True) if title_elem else "Unknown"

        # Extract email
        email_elem = element.find("a", href=re.compile(r"^mailto:"))
        email = email_elem["href"].replace("mailto:", "") if email_elem else None

        # Extract research areas (look for keywords)
        text_content = element.get_text()
        research_areas = []
        # Simple keyword extraction - can be enhanced
        keywords = re.findall(
            r"\b(?:machine learning|AI|bioinformatics|genomics|"
            r"computational biology|systems biology)\b",
            text_content,
            re.IGNORECASE,
        )
        research_areas = list(set(keywords))

        professors.append(
            {
                "name": name,
                "title": title,
                "profile_url": profile_url,
                "email": email,
                "research_areas": research_areas,
                "lab_name": None,
                "lab_url": None,
            }
        )

    return professors


async def discover_professors_for_department(
    department: Department, correlation_id: str
) -> list[Professor]:
    """Discover professors for a single department using Claude Agent SDK.

    Args:
        department: Department model to discover professors for
        correlation_id: Correlation ID for logging

    Returns:
        List of Professor models discovered

    Raises:
        Exception: If discovery fails completely (after retries)
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_discovery",
        component="professor_filter",
    )
    logger.info(
        "Starting professor discovery",
        department=department.name,
        url=department.url,
    )

    # Validate department URL
    if not department.url or not department.url.startswith("http"):
        logger.error(
            "Invalid department URL",
            url=department.url,
            department=department.name,
        )
        return []

    # Configure Claude Agent SDK with built-in web scraping tools
    options = ClaudeAgentOptions(
        allowed_tools=["WebFetch", "WebSearch"],
        max_turns=3,
        system_prompt=(
            "You are a web scraping assistant specialized in extracting "
            "professor information from university department pages."
        ),
        setting_sources=None,  # CRITICAL: Prevents codebase context injection
    )

    prompt = f"""
Scrape the professor directory at: {department.url}

Extract ALL professors with the following information:
- Full name
- Title (Professor, Associate Professor, Assistant Professor, etc.)
- Research areas/interests
- Lab name and URL (if available)
- Email address
- Profile page URL

Try multiple selector patterns to find professor listings:
- Common selectors: .faculty-member, .professor-card, table.faculty
- Semantic HTML: <article>, <section class="people">
- Link patterns: <a href="*/faculty/*">, <a href="*/people/*">

If structured directory not found, search for "faculty" or "people" links.

Return results as a JSON array of professor objects.
Example format:
[
  {{
    "name": "Dr. Jane Smith",
    "title": "Professor",
    "research_areas": ["Machine Learning", "Computer Vision"],
    "lab_name": "Vision Lab",
    "lab_url": "https://visionlab.example.edu",
    "email": "jsmith@example.edu",
    "profile_url": "https://cs.example.edu/faculty/jsmith"
  }}
]
"""

    professors_data = []
    try:
        # Use ClaudeSDKClient class (stateless mode)
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            # Parse JSON response from Claude
                            parsed_data = parse_professor_data(block.text)
                            professors_data.extend(parsed_data)

        # Convert to Professor Pydantic models
        professor_models = []
        for p in professors_data:
            prof = Professor(
                id=generate_professor_id(str(p["name"]), department.id),
                name=str(p["name"]),
                title=str(p.get("title", "Unknown")),
                department_id=department.id,
                department_name=department.name,
                school=department.school,
                lab_name=str(p["lab_name"]) if p.get("lab_name") else None,
                lab_url=str(p["lab_url"]) if p.get("lab_url") else None,
                research_areas=(
                    cast(list[str], p.get("research_areas", []))
                    if isinstance(p.get("research_areas"), list)
                    else []
                ),
                profile_url=str(p.get("profile_url", "")),
                email=str(p["email"]) if p.get("email") else None,
                data_quality_flags=[],
            )

            # Add quality flags
            if not prof.email:
                prof.add_quality_flag("missing_email")
            if not prof.research_areas:
                prof.add_quality_flag("missing_research_areas")
            if not prof.lab_name:
                prof.add_quality_flag("missing_lab_affiliation")

            professor_models.append(prof)

        logger.info("Discovery successful", professors_count=len(professor_models))
        return professor_models

    except Exception as e:
        logger.warning("WebFetch failed, falling back to Playwright", error=str(e))
        return await discover_with_playwright_fallback(department, correlation_id)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def discover_with_playwright_fallback(
    department: Department, correlation_id: str
) -> list[Professor]:
    """Fallback to Playwright when Claude SDK WebFetch fails.

    Args:
        department: Department model to discover professors for
        correlation_id: Correlation ID for logging

    Returns:
        List of Professor models with playwright_fallback flag

    Raises:
        Exception: If Playwright scraping also fails after retries
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_discovery",
        component="professor_filter",
    )
    logger.info("Using Playwright fallback", department=department.name)

    # Handle invalid/missing department URL
    if not department.url or not department.url.startswith("http"):
        logger.error(
            "Invalid department URL",
            url=department.url,
            department=department.name,
        )
        return []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Set timeout to prevent hanging
            await page.goto(department.url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            content = await page.content()
            await browser.close()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")

            # Try multiple selector patterns
            professors_data = []
            for selector in SELECTOR_PATTERNS:
                elements = soup.select(selector)
                if elements:
                    logger.debug(
                        f"Found {len(elements)} professors with selector: {selector}"
                    )
                    professors_data = parse_professor_elements(elements, department)
                    break

            # No professors found - flag but don't fail
            if not professors_data:
                logger.warning(
                    "No professors found with any selector",
                    department=department.name,
                    url=department.url,
                )
                return []

            # Convert to Professor models with playwright flag
            professor_models = []
            for p_data in professors_data:
                # Extract and cast values from dict
                name_val = p_data.get("name", "")
                title_val = p_data.get("title", "Unknown")
                lab_name_val = p_data.get("lab_name")
                lab_url_val = p_data.get("lab_url")
                research_areas_val = p_data.get("research_areas", [])
                profile_url_val = p_data.get("profile_url", "")
                email_val = p_data.get("email")

                prof = Professor(
                    id=generate_professor_id(
                        str(name_val) if name_val else "", department.id
                    ),
                    name=str(name_val) if name_val else "",
                    title=str(title_val) if title_val else "Unknown",
                    department_id=department.id,
                    department_name=department.name,
                    school=department.school,
                    lab_name=str(lab_name_val) if lab_name_val else None,
                    lab_url=str(lab_url_val) if lab_url_val else None,
                    research_areas=(
                        list(research_areas_val)
                        if isinstance(research_areas_val, list)
                        else []
                    ),
                    profile_url=str(profile_url_val) if profile_url_val else "",
                    email=str(email_val) if email_val else None,
                    data_quality_flags=["scraped_with_playwright_fallback"],
                )

                # Add additional quality flags
                if not prof.email:
                    prof.add_quality_flag("missing_email")
                if not prof.research_areas:
                    prof.add_quality_flag("missing_research_areas")
                if not prof.lab_name:
                    prof.add_quality_flag("missing_lab_affiliation")

                professor_models.append(prof)

            logger.info(
                "Playwright fallback successful",
                professors_count=len(professor_models),
            )
            return professor_models

    except Exception as e:
        logger.error(
            "Playwright fallback also failed",
            error=str(e),
            department=department.name,
        )
        return []


def load_relevant_departments(correlation_id: str) -> list[Department]:
    """Load relevant departments from Epic 2 checkpoint.

    Args:
        correlation_id: Correlation ID for logging

    Returns:
        List of Department models from Epic 2

    Raises:
        IOError: If checkpoint loading fails
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_discovery",
        component="professor_filter",
    )

    checkpoint_manager = CheckpointManager()
    departments_data = checkpoint_manager.load_batches("phase-1-relevant-departments")

    # Convert to Department models and filter for relevant only
    departments = [
        Department(**dept_data)
        for dept_data in departments_data
        if dept_data.get("is_relevant", False)
    ]

    # Verify all departments have required fields
    valid_departments = []
    for dept in departments:
        if not dept.name or not dept.url:
            logger.warning(
                "Department missing required fields",
                department_id=dept.id,
                has_name=bool(dept.name),
                has_url=bool(dept.url),
            )
            continue
        valid_departments.append(dept)

    logger.info(
        "Loaded relevant departments for professor discovery",
        total_departments=len(valid_departments),
    )

    return valid_departments


async def discover_professors_parallel(
    departments: list[Department], max_concurrent: int = 5
) -> list[Professor]:
    """Discover professors across multiple departments in parallel using asyncio.

    This is APPLICATION-LEVEL parallel execution, NOT a Claude Agent SDK feature.
    Uses asyncio.Semaphore to control concurrency and rate limiting per domain.

    Story 3.1b: Parallel processing
    Story 3.1c: Rate limiting integration

    Args:
        departments: List of Department models to discover professors for
        max_concurrent: Maximum number of concurrent department processing tasks

    Returns:
        Aggregated list of Professor models from all departments

    Raises:
        None - Failed departments are logged but don't block processing
    """
    from src.utils.progress_tracker import ProgressTracker

    logger = get_logger(
        correlation_id="prof-discovery-coordinator",
        phase="professor_discovery",
        component="professor_filter",
    )
    logger.info(
        "Starting parallel discovery with rate limiting",
        departments_count=len(departments),
        max_concurrent=max_concurrent,
    )

    # Handle edge case: empty department list
    if not departments:
        logger.warning("No departments provided for parallel discovery")
        return []

    # Initialize progress tracker
    tracker = ProgressTracker()
    tracker.start_phase("Phase 2: Professor Discovery", total_items=len(departments))

    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrent)

    # Create rate limiter (Story 3.1c: Task 2)
    rate_limiter = DomainRateLimiter(default_rate=1.0, time_period=1.0)

    completed_count = 0
    failed_count = 0

    async def process_with_semaphore(dept: Department, index: int) -> list[Professor]:
        """Process single department with semaphore control, rate limiting, and progress tracking."""
        nonlocal completed_count, failed_count

        async with semaphore:
            # Generate unique correlation ID for this department's processing
            correlation_id = f"prof-disc-{dept.id}-{uuid.uuid4().hex[:8]}"

            logger.info(
                f"Processing department {index + 1}/{len(departments)}",
                department=dept.name,
                correlation_id=correlation_id,
            )

            try:
                # Apply rate limiting before processing (Story 3.1c: Task 2)
                domain = urlparse(dept.url).netloc if dept.url else "unknown"
                logger.debug(
                    "Acquiring rate limit",
                    domain=domain,
                    department=dept.name,
                    correlation_id=correlation_id,
                )
                await rate_limiter.acquire(dept.url)

                # discover_professors_for_department() from Story 3.1a
                # Returns: list[Professor] | Raises: Exception on scraping/network failures
                professors = await discover_professors_for_department(
                    dept, correlation_id
                )

                logger.info(
                    "Department processing successful",
                    department=dept.name,
                    professors_found=len(professors),
                    correlation_id=correlation_id,
                )

                return professors

            except Exception as e:
                logger.error(
                    "Department processing failed",
                    department=dept.name,
                    error=str(e),
                    correlation_id=correlation_id,
                )

                failed_count += 1
                return []  # Return empty list, continue with others

            finally:
                # Always update progress, even if exception occurs
                completed_count += 1
                tracker.update(completed=completed_count)

    # Create tasks for all departments
    tasks = [process_with_semaphore(dept, i) for i, dept in enumerate(departments)]

    # Execute in parallel with asyncio.gather
    # return_exceptions=True ensures one failure doesn't stop others
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Flatten results and track failures
    all_professors: list[Professor] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failed_count += 1
            logger.error(
                "Task failed with exception",
                department=departments[i].name,
                error=str(result),
            )
            continue
        if isinstance(result, list):
            all_professors.extend(result)

    # Complete progress tracking
    tracker.complete_phase()

    logger.info(
        "Parallel discovery complete",
        total_professors=len(all_professors),
        successful_departments=len(departments) - failed_count,
        failed_departments=failed_count,
    )

    return all_professors


async def discover_and_save_professors(
    departments: list[Department] | None = None,
    max_concurrent: int = 5,
    batch_id: int = 1,
) -> list[Professor]:
    """Orchestrator: Discover, deduplicate, and save professors to checkpoint.

    Complete workflow for Story 3.1c:
    1. Discover professors in parallel with rate limiting
    2. Deduplicate using LLM-based fuzzy matching
    3. Save deduplicated list to checkpoint

    Story 3.1c: Task 4

    Args:
        departments: List of departments (loads from checkpoint if None)
        max_concurrent: Maximum concurrent department processing
        batch_id: Batch ID for checkpoint (default: 1 for single batch)

    Returns:
        List of deduplicated Professor models
    """
    logger = get_logger(
        correlation_id="prof-discovery-main",
        phase="professor_discovery",
        component="professor_filter",
    )
    logger.info("Starting professor discovery workflow")

    # Load departments if not provided
    if departments is None:
        logger.info("Loading departments from checkpoint")
        departments = load_relevant_departments("prof-discovery-main")

    # Step 1: Discover professors in parallel with rate limiting
    logger.info("Step 1: Parallel discovery with rate limiting")
    all_professors = await discover_professors_parallel(
        departments, max_concurrent=max_concurrent
    )

    # Step 2: Deduplicate professors
    logger.info("Step 2: Deduplication", total_professors=len(all_professors))
    unique_professors = await deduplicate_professors(all_professors)

    # Step 3: Save to checkpoint
    logger.info(
        "Step 3: Saving to checkpoint",
        unique_professors=len(unique_professors),
        batch_id=batch_id,
    )
    checkpoint_manager = CheckpointManager()
    checkpoint_manager.save_batch(
        phase="phase-2-professors", batch_id=batch_id, data=unique_professors
    )

    logger.info(
        "Professor discovery workflow complete",
        discovered=len(all_professors),
        unique=len(unique_professors),
        duplicates_removed=len(all_professors) - len(unique_professors),
        departments_processed=len(departments),
        checkpoint_file=f"checkpoints/phase-2-professors-batch-{batch_id}.jsonl",
    )

    return unique_professors


# ============================================================================
# Story 3.2: Professor Filtering Functions
# ============================================================================


def load_user_profile() -> dict[str, str]:
    """Load consolidated user profile from Story 1.7 output.

    Story 3.2: Task 1 - Load User Research Profile

    Reads output/user_profile.md and extracts structured data for filtering.
    For filtering, we need research interests and degree.

    Returns:
        Dict with research_interests and current_degree fields

    Raises:
        FileNotFoundError: If user profile doesn't exist
        ValueError: If research interests are missing (required field)
    """
    logger = get_logger(
        correlation_id="profile-loading",
        phase="professor_filtering",
        component="professor_filter",
    )

    profile_path = Path("output/user_profile.md")

    if not profile_path.exists():
        logger.error("User profile not found", path=str(profile_path))
        raise FileNotFoundError(
            "User profile must be generated via Story 1.7 first. "
            "Run profile consolidation before filtering."
        )

    content = profile_path.read_text(encoding="utf-8")

    # Extract research interests from "Streamlined Research Focus" section
    interests_match = re.search(
        r"### Streamlined Research Focus\s+(.+?)(?=\n#|\n---|\Z)", content, re.DOTALL
    )
    interests = interests_match.group(1).strip() if interests_match else ""

    # Extract current position/degree
    degree_match = re.search(r"\*\*Current Position:\*\* (.+)", content)
    degree = degree_match.group(1).strip() if degree_match else ""

    # Critical field validation
    if not interests:
        logger.error("Research interests missing from user profile")
        raise ValueError(
            "Cannot filter professors without research interests. "
            "User profile is incomplete."
        )

    # Optional field fallback
    if not degree:
        logger.warning("Current degree missing, using 'General' as fallback")
        degree = "General"

    logger.info(
        "User profile loaded successfully",
        interests_length=len(interests),
        degree=degree,
    )

    return {"research_interests": interests, "current_degree": degree}


def format_profile_for_llm(profile_dict: dict[str, str]) -> str:
    """Format profile dict as string for llm_helpers.filter_professor_research().

    Story 3.2: Task 3.1 - Prepare profile for LLM

    Args:
        profile_dict: Dict with research_interests and current_degree

    Returns:
        Formatted profile string for LLM prompt
    """
    return f"""Research Interests: {profile_dict["research_interests"]}
Degree Program: {profile_dict["current_degree"]}"""


def validate_confidence_score(
    raw_confidence: Any, professor_name: str, correlation_id: str
) -> tuple[int, list[str]]:
    """Validate and normalize confidence score from LLM response.

    Story 3.3: Task 4 - Parse and Validate Confidence Scores

    Handles multiple types (int, float, string) and validates range (0-100).
    Applies clamping for out-of-range values and neutral default for invalid values.

    Args:
        raw_confidence: Confidence value from LLM (any type)
        professor_name: Professor name for logging
        correlation_id: Correlation ID for logging

    Returns:
        Tuple of (validated_confidence: int, flags: list[str])
        - validated_confidence: Integer in range 0-100
        - flags: List of data quality flags to add
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_filtering",
        component="professor_filter",
    )

    flags: list[str] = []

    # Type conversion: handle int, float, string
    try:
        if isinstance(raw_confidence, bool):
            # bool is subclass of int, handle explicitly
            raise ValueError("Boolean type not valid for confidence")

        if isinstance(raw_confidence, (int, float)):
            confidence = int(round(float(raw_confidence)))
        elif isinstance(raw_confidence, str):
            # Attempt string to float to int conversion
            confidence = int(round(float(raw_confidence)))
        else:
            raise ValueError(f"Unsupported type: {type(raw_confidence)}")

    except (ValueError, TypeError) as e:
        # Non-numeric or invalid type - set to neutral 50
        logger.warning(
            "Invalid confidence type, using neutral default",
            professor=professor_name,
            raw_value=str(raw_confidence)[:50],
            error=str(e),
        )
        flags.append("llm_response_error")
        return 50, flags

    # Range validation and clamping
    if confidence < 0:
        logger.error(
            "Negative confidence returned, clamping to 0",
            confidence=confidence,
            professor=professor_name,
        )
        flags.append("confidence_out_of_range")
        return 0, flags

    if confidence > 100:
        logger.error(
            "Confidence exceeds 100, clamping to 100",
            confidence=confidence,
            professor=professor_name,
        )
        flags.append("confidence_out_of_range")
        return 100, flags

    # Valid confidence in range 0-100
    return confidence, flags


async def filter_professor_single(
    professor: Professor, profile_dict: dict[str, str], correlation_id: str
) -> dict[str, Any]:
    """Filter single professor using LLM-based research alignment analysis.

    Story 3.2: Task 3 - Core LLM Filtering Function

    Calls llm_helpers.filter_professor_research() and maps confidence score
    to include/exclude decision using threshold from system_params.json.

    Decision Logic:
    - confidence >= 70 → "include"
    - confidence < 70 → "exclude"

    Edge Cases Handled:
    - Interdisciplinary researchers: ANY research overlap → include
    - Emerging fields: Conceptually related → include
    - Missing research areas: Include by default (investigate later)
    - LLM failures: Inclusive fallback with data quality flag

    Args:
        professor: Professor model to filter
        profile_dict: User profile dict from load_user_profile()
        correlation_id: Correlation ID for logging

    Returns:
        Dict with decision ("include"/"exclude"), confidence (0-100), and reasoning (str)
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_filtering",
        component="professor_filter",
    )

    # Load configuration
    system_params = SystemParams.load()
    threshold = system_params.confidence_thresholds.professor_filter

    # Format inputs for LLM helper
    research_areas_str = (
        ", ".join(professor.research_areas)
        if professor.research_areas
        else "Not specified"
    )
    user_profile_str = format_profile_for_llm(profile_dict)

    logger.debug(
        "Filtering professor",
        professor=professor.name,
        research_areas=research_areas_str,
    )

    try:
        # Call existing LLM helper (returns {"confidence": 0-100, "reasoning": "..."})
        llm_result = await filter_professor_research(
            professor_name=professor.name,
            research_areas=research_areas_str,
            user_profile=user_profile_str,
            bio="",  # Bio not available at this phase
            correlation_id=correlation_id,
        )

        # Story 3.3 Task 4: Validate confidence score
        raw_confidence = llm_result.get("confidence")

        # Handle missing confidence field
        if raw_confidence is None:
            logger.warning(
                "Missing confidence field in LLM response",
                professor=professor.name,
            )
            confidence = 50
            confidence_flags = ["llm_response_error"]
        else:
            # Validate and normalize confidence
            confidence, confidence_flags = validate_confidence_score(
                raw_confidence, professor.name, correlation_id
            )

        reasoning = llm_result.get("reasoning", "")

        # Map confidence to decision using threshold
        decision = "include" if confidence >= threshold else "exclude"

        # Story 3.3 Task 5: Identify low-confidence decisions
        system_params = SystemParams.load()
        low_threshold = system_params.filtering_config.low_confidence_threshold

        if confidence < low_threshold:
            confidence_flags.append("low_confidence_filter")
            logger.warning(
                "Low confidence decision flagged for review",
                professor=professor.name,
                confidence=confidence,
                decision=decision,
                reasoning=reasoning[:100],
            )

        # Log interdisciplinary cases (high confidence, multiple research areas)
        if decision == "include" and len(professor.research_areas) >= 3:
            logger.info(
                "Interdisciplinary professor included",
                professor=professor.name,
                research_areas=professor.research_areas,
                confidence=confidence,
            )

        # Log edge cases (missing research areas but included)
        if decision == "include" and not professor.research_areas:
            logger.warning(
                "Professor with missing research areas included by default",
                professor=professor.name,
                confidence=confidence,
            )

        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": reasoning,
            "flags": confidence_flags,
        }

    except Exception as e:
        logger.error(
            "LLM filtering failed, using inclusive fallback",
            professor=professor.name,
            error=str(e),
        )
        # Inclusive fallback: include by default when LLM fails
        return {
            "decision": "include",
            "confidence": 0,
            "reasoning": f"LLM call failed ({str(e)[:50]}...) - included by default for human review",
            "flags": [],
        }


async def filter_professor_batch_parallel(
    batch: list[Professor],
    profile_dict: dict[str, str],
    correlation_id: str,
    max_concurrent: int = 5,
) -> list[Professor]:
    """Filter batch of professors in parallel with semaphore rate limiting.

    Story 3.5: Task 7 - Parallel LLM calls within batch

    Uses asyncio.Semaphore to limit concurrent LLM calls and prevent API throttling.
    All professors in batch are processed simultaneously (up to semaphore limit).

    Args:
        batch: List of Professor models to filter
        profile_dict: User profile dict from load_user_profile()
        correlation_id: Correlation ID for logging
        max_concurrent: Maximum concurrent LLM calls (default: 5)

    Returns:
        List of Professor models with filter results applied
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_filtering",
        component="professor_filter",
    )

    # Create semaphore for rate limiting (Story 3.5 Task 7)
    semaphore = asyncio.Semaphore(max_concurrent)

    logger.debug(
        f"Processing batch with {len(batch)} professors (max {max_concurrent} concurrent)"
    )

    async def filter_with_limit(professor: Professor) -> Professor:
        """Filter single professor with semaphore rate limiting."""
        async with semaphore:
            # Generate unique correlation ID for this professor
            prof_correlation_id = f"{correlation_id}-{professor.id}"

            try:
                # Call filtering function (Story 3.2)
                filter_result = await filter_professor_single(
                    professor, profile_dict, prof_correlation_id
                )

                # Update professor model fields
                professor.is_relevant = filter_result["decision"] == "include"
                professor.relevance_confidence = filter_result["confidence"]
                professor.relevance_reasoning = filter_result["reasoning"]

                # Add confidence validation flags (Story 3.3)
                for flag in filter_result.get("flags", []):
                    professor.add_quality_flag(flag)

                # Add data quality flags
                if filter_result["confidence"] == 0:
                    professor.add_quality_flag("llm_filtering_failed")

                return professor

            except Exception as e:
                # Story 3.5 Task 8: Individual professor failure handling
                logger.error(
                    "Failed to filter professor in batch",
                    professor=professor.name,
                    error=str(e),
                )
                # Inclusive fallback
                professor.is_relevant = True
                professor.relevance_confidence = 0
                professor.relevance_reasoning = f"Filter error: {str(e)[:100]}"
                professor.add_quality_flag("llm_filtering_failed")
                return professor

    # Launch all LLM filter calls in parallel (Story 3.5 Task 7)
    tasks = [filter_with_limit(p) for p in batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results (handle any exceptions that weren't caught)
    filtered_batch: list[Professor] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # Unexpected exception from gather - apply inclusive fallback
            logger.error(
                "Unexpected exception in batch processing",
                professor=batch[i].name,
                error=str(result),
            )
            batch[i].is_relevant = True
            batch[i].relevance_confidence = 0
            batch[i].relevance_reasoning = f"Unexpected error: {str(result)[:100]}"
            batch[i].add_quality_flag("llm_filtering_failed")
            filtered_batch.append(batch[i])
        elif isinstance(result, Professor):
            # Normal case: result is a Professor
            filtered_batch.append(result)

    return filtered_batch


async def filter_professors(correlation_id: str) -> list[Professor]:
    """Main orchestration function for professor filtering workflow.

    Story 3.2: Task 4 - Batch Orchestration

    Complete filtering workflow:
    1. Load user profile from output/user_profile.md
    2. Load system params for batch size and confidence threshold
    3. Load professors from Story 3.1b checkpoints (phase-2-professors-batch-*.jsonl)
    4. Filter each professor using LLM
    5. Save ALL professors (relevant + filtered) to new checkpoints
    6. Update progress tracking
    7. Return complete list

    Resumability: Uses checkpoint_manager.get_resume_point() to resume from last completed batch.

    Args:
        correlation_id: Correlation ID for logging

    Returns:
        List of ALL professors with is_relevant field updated
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_filtering",
        component="professor_filter",
    )
    logger.info("Starting professor filtering workflow")

    # Task 1: Load user profile
    logger.info("Step 1: Loading user profile")
    profile_dict = load_user_profile()

    # Load system parameters
    logger.info("Step 2: Loading system parameters")
    system_params = SystemParams.load()
    batch_size = system_params.batch_config.professor_filtering_batch_size

    # Log loaded batch configuration (Story 3.5 Task 1)
    logger.info(
        "Loaded batch configuration",
        professor_filtering_batch_size=batch_size,
        max_concurrent_llm_calls=system_params.rate_limiting.max_concurrent_llm_calls,
    )

    # Load checkpoint manager
    checkpoint_manager = CheckpointManager()

    # Load all professors from Story 3.1b checkpoints
    logger.info("Step 3: Loading professors from checkpoints")
    professor_batches = checkpoint_manager.load_batches("phase-2-professors")

    # Flatten batches into single list
    all_professors: list[Professor] = []
    for batch_data in professor_batches:
        # Convert dict to Professor model
        if isinstance(batch_data, dict):
            all_professors.append(Professor(**batch_data))
        else:
            all_professors.append(batch_data)

    logger.info("Professors loaded", total_count=len(all_professors))

    # Initialize progress tracker (Task 5)
    tracker = ProgressTracker()
    tracker.start_phase("Phase 2: Professor Filtering", total_items=len(all_professors))

    # Process professors in batches
    processed_count = 0
    included_count = 0
    excluded_count = 0
    failed_count = 0

    # Determine resume point
    resume_batch = checkpoint_manager.get_resume_point("phase-2-filter")
    total_batches = (len(all_professors) + batch_size - 1) // batch_size

    logger.info(
        "Starting batch processing",
        total_batches=total_batches,
        batch_size=batch_size,
        resume_from_batch=resume_batch,
    )

    # Get max concurrent LLM calls from config (Story 3.5 Task 7)
    max_concurrent = system_params.rate_limiting.max_concurrent_llm_calls

    for batch_num in range(resume_batch, total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(all_professors))
        batch_professors = all_professors[start_idx:end_idx]

        logger.info(
            f"Processing batch {batch_num + 1}/{total_batches} with {len(batch_professors)} parallel LLM calls (max {max_concurrent} concurrent)",
            batch_size=len(batch_professors),
        )

        # Update batch progress (Story 3.5 Task 6)
        tracker.update_batch(
            batch_num=batch_num + 1,
            total_batches=total_batches,
            batch_desc=f"Professors {start_idx + 1}-{end_idx}",
        )

        # Story 3.5 Task 7: Filter batch in parallel with semaphore
        try:
            filtered_batch = await filter_professor_batch_parallel(
                batch=batch_professors,
                profile_dict=profile_dict,
                correlation_id=f"{correlation_id}-batch-{batch_num + 1}",
                max_concurrent=max_concurrent,
            )

            # Count results
            for professor in filtered_batch:
                if professor.is_relevant:
                    included_count += 1
                else:
                    excluded_count += 1

                # Count failures
                if "llm_filtering_failed" in professor.data_quality_flags:
                    failed_count += 1

            processed_count += len(filtered_batch)
            tracker.update(completed=processed_count)

            # Story 3.5 Task 5: Save batch checkpoint
            logger.info(
                f"Saving batch {batch_num + 1} checkpoint",
                batch_size=len(filtered_batch),
                included=sum(1 for p in filtered_batch if p.is_relevant),
                excluded=sum(1 for p in filtered_batch if not p.is_relevant),
            )
            checkpoint_manager.save_batch(
                phase="phase-2-filter",
                batch_id=batch_num + 1,
                data=filtered_batch,
            )

        except Exception as e:
            # Story 3.5 Task 8: Batch infrastructure failure handling
            logger.error(
                f"Batch {batch_num + 1} processing infrastructure failed",
                error=str(e),
                correlation_id=correlation_id,
            )
            # Re-raise to prevent data consistency issues
            raise

    # Complete progress tracking
    tracker.complete_phase()

    # Story 3.3 Task 9: Apply manual overrides (after LLM filtering)
    override_count = apply_manual_overrides(all_professors)

    # Recalculate included/excluded counts after overrides
    if override_count > 0:
        included_count = sum(1 for p in all_professors if p.is_relevant)
        excluded_count = len(all_professors) - included_count

    # Calculate match rate
    match_rate = (included_count / len(all_professors) * 100) if all_professors else 0

    # Story 3.3 Task 7: Calculate confidence statistics
    confidence_stats = calculate_confidence_stats(all_professors)

    # Story 3.3 Task 8: Save confidence stats to JSON
    save_confidence_stats_report(confidence_stats)

    # Display confidence distribution summary
    included_stats = confidence_stats["included"]
    logger.info(
        "Filtering complete with confidence breakdown",
        total_professors=len(all_professors),
        included=included_count,
        excluded=excluded_count,
        failed=failed_count,
        match_rate=f"{match_rate:.1f}%",
        high_conf=included_stats["high"],
        med_conf=included_stats["medium"],
        low_conf=included_stats["low"],
        quality=confidence_stats["distribution_analysis"]["quality_assessment"],
    )

    return all_professors


def generate_borderline_report(professors: list[Professor]) -> None:
    """Generate borderline professor review report.

    Story 3.3: Task 6 - Generate Borderline Cases Review Report

    Creates output/borderline-professors.md with:
    - Summary statistics
    - Professors with low confidence scores
    - Grouped by decision (included vs. excluded)
    - Actionable recommendations

    Args:
        professors: List of all professors with filtering results
    """
    logger = get_logger(
        correlation_id="borderline-report",
        phase="professor_filtering",
        component="professor_filter",
    )

    # Load configuration
    system_params = SystemParams.load()
    low_threshold = system_params.filtering_config.low_confidence_threshold

    # Filter borderline cases (confidence < threshold)
    borderline_professors = [
        p for p in professors if p.relevance_confidence < low_threshold
    ]

    if not borderline_professors:
        logger.info("No borderline cases found, skipping report generation")
        return

    # Split by decision
    included_borderline = [p for p in borderline_professors if p.is_relevant]
    excluded_borderline = [p for p in borderline_professors if not p.is_relevant]

    # Calculate statistics
    total_borderline = len(borderline_professors)
    borderline_percentage = (
        (total_borderline / len(professors) * 100) if professors else 0
    )

    # Create output directory if needed
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Generate report
    report_path = output_dir / "borderline-professors.md"

    with open(report_path, "w", encoding="utf-8") as f:
        # Header
        f.write("# Borderline Professor Filtering Cases\n\n")
        f.write(f"**Low Confidence Threshold:** {low_threshold}\n")
        f.write(
            f"**Total Borderline Cases:** {total_borderline} ({borderline_percentage:.1f}% of total professors)\n"
        )
        f.write(
            f"**Breakdown:** {len(included_borderline)} included (low confidence), {len(excluded_borderline)} excluded (low confidence)\n\n"
        )
        f.write("---\n\n")

        # Included professors section
        f.write(
            f"## Included Professors (Low Confidence) - {len(included_borderline)} cases\n\n"
        )
        f.write(
            "These professors were **included** despite low confidence. Consider if they should be excluded.\n\n"
        )

        if included_borderline:
            f.write(
                "| Professor | Department | Research Areas | Confidence | Reasoning | Profile Link | Recommend Override? |\n"
            )
            f.write(
                "|-----------|------------|----------------|------------|-----------|--------------|---------------------|\n"
            )

            for prof in included_borderline:
                research_areas = ", ".join(
                    prof.research_areas[:3]
                )  # Limit to 3 for readability
                if len(prof.research_areas) > 3:
                    research_areas += "..."

                reasoning_short = (
                    prof.relevance_reasoning[:80] + "..."
                    if len(prof.relevance_reasoning) > 80
                    else prof.relevance_reasoning
                )

                # Recommend override logic based on reasoning keywords
                recommend = _get_override_recommendation(
                    prof.relevance_reasoning, prof.is_relevant
                )

                f.write(
                    f"| [{prof.name}]({prof.profile_url}) | {prof.department_name} | {research_areas} | {prof.relevance_confidence} | {reasoning_short} | [View Profile]({prof.profile_url}) | {recommend} |\n"
                )
        else:
            f.write("*No included professors with low confidence.*\n")

        f.write(
            "\n## Excluded Professors (Low Confidence) - "
            + str(len(excluded_borderline))
            + " cases\n\n"
        )
        f.write(
            "These professors were **excluded** due to low confidence. Consider if they should be included.\n\n"
        )

        if excluded_borderline:
            f.write(
                "| Professor | Department | Research Areas | Confidence | Reasoning | Profile Link | Recommend Override? |\n"
            )
            f.write(
                "|-----------|------------|----------------|------------|-----------|--------------|---------------------|\n"
            )

            for prof in excluded_borderline:
                research_areas = ", ".join(prof.research_areas[:3])
                if len(prof.research_areas) > 3:
                    research_areas += "..."

                reasoning_short = (
                    prof.relevance_reasoning[:80] + "..."
                    if len(prof.relevance_reasoning) > 80
                    else prof.relevance_reasoning
                )

                recommend = _get_override_recommendation(
                    prof.relevance_reasoning, prof.is_relevant
                )

                f.write(
                    f"| [{prof.name}]({prof.profile_url}) | {prof.department_name} | {research_areas} | {prof.relevance_confidence} | {reasoning_short} | [View Profile]({prof.profile_url}) | {recommend} |\n"
                )
        else:
            f.write("*No excluded professors with low confidence.*\n")

        # Action instructions
        f.write("\n---\n\n")
        f.write(
            "**Action Required:** Review these borderline cases manually. To override decisions, add entries to `config/manual-overrides.json`:\n\n"
        )
        f.write("```json\n")
        f.write("{\n")
        f.write('  "professor_overrides": [\n')
        f.write("    {\n")
        f.write('      "professor_id": "prof-id-here",\n')
        f.write('      "decision": "include",\n')
        f.write('      "reason": "Your reasoning here",\n')
        f.write('      "timestamp": "2025-10-08T14:30:00Z",\n')
        f.write('      "original_confidence": 65,\n')
        f.write('      "original_decision": "exclude"\n')
        f.write("    }\n")
        f.write("  ]\n")
        f.write("}\n")
        f.write("```\n")

    logger.info(
        "Borderline report generated",
        report_path=str(report_path),
        total_borderline=total_borderline,
        included_borderline=len(included_borderline),
        excluded_borderline=len(excluded_borderline),
    )


def _get_override_recommendation(reasoning: str, is_relevant: bool) -> str:
    """Determine override recommendation based on reasoning keywords.

    Args:
        reasoning: LLM reasoning text
        is_relevant: Current decision

    Returns:
        Recommendation string for override column
    """
    reasoning_lower = reasoning.lower()

    # Keywords suggesting reconsideration
    interdisciplinary_keywords = ["interdisciplinary", "cross-field"]
    emerging_keywords = ["emerging", "new field", "cutting-edge", "innovative", "novel"]
    tangential_keywords = ["tangential", "weak", "minimal", "indirect"]

    if any(kw in reasoning_lower for kw in interdisciplinary_keywords):
        return "Review - interdisciplinary"
    elif any(kw in reasoning_lower for kw in emerging_keywords):
        return "Consider - emerging field"
    elif any(kw in reasoning_lower for kw in tangential_keywords):
        if is_relevant:
            return "Review - tangential match"
        else:
            return "Likely correct"
    else:
        return "Review manually"


def calculate_confidence_stats(professors: list[Professor]) -> dict[str, Any]:
    """Calculate confidence distribution statistics for filtering results.

    Story 3.3: Task 7 - Implement Confidence-Based Statistics

    Categorizes professors by confidence level:
    - High confidence (>=90): Strong match certainty
    - Medium confidence (70-89): Moderate match certainty
    - Low confidence (<70): Requires review

    Calculates for both included and excluded professors, and provides
    quality validation warnings if distribution is outside expected ranges.

    Args:
        professors: List of professors with filtering results

    Returns:
        Dict with confidence distribution statistics and quality assessment
    """
    logger = get_logger(
        correlation_id="confidence-stats",
        phase="professor_filtering",
        component="professor_filter",
    )

    # Load thresholds
    system_params = SystemParams.load()
    low_threshold = system_params.filtering_config.low_confidence_threshold
    high_threshold = system_params.filtering_config.high_confidence_threshold

    # Split by decision
    included = [p for p in professors if p.is_relevant]
    excluded = [p for p in professors if not p.is_relevant]

    # Calculate distributions
    def categorize(profs: list[Professor]) -> dict[str, int]:
        high = sum(1 for p in profs if p.relevance_confidence >= high_threshold)
        medium = sum(
            1 for p in profs if low_threshold <= p.relevance_confidence < high_threshold
        )
        low = sum(1 for p in profs if p.relevance_confidence < low_threshold)
        return {"high": high, "medium": medium, "low": low, "total": len(profs)}

    included_dist = categorize(included)
    excluded_dist = categorize(excluded)

    # Overall low-confidence percentage
    total_low = included_dist["low"] + excluded_dist["low"]
    low_percentage = (total_low / len(professors) * 100) if professors else 0

    # Quality validation (expected: 10-20% low-confidence)
    deviation_msg = ""
    quality_assessment = ""

    if low_percentage > 30:
        logger.warning(
            "High proportion of low-confidence decisions detected",
            low_confidence_percentage=f"{low_percentage:.1f}%",
            expected_range="10-20%",
            message="Consider reviewing prompt or research profile specificity",
        )
        deviation_msg = f"High ({low_percentage:.1f}% vs expected 10-20%)"
        quality_assessment = "Warning - High low-confidence rate suggests prompt issues"
    elif low_percentage < 10:
        deviation_msg = f"Low ({low_percentage:.1f}% vs expected 10-20%)"
        quality_assessment = "Good - Low ambiguity in filtering decisions"
    else:
        deviation_msg = "Within expected range"
        quality_assessment = "Good - Distribution matches expectations"

    stats = {
        "total_professors": len(professors),
        "included": included_dist,
        "excluded": excluded_dist,
        "distribution_analysis": {
            "low_confidence_percentage": round(low_percentage, 1),
            "expected_range": "10-20%",
            "deviation_from_expected": deviation_msg,
            "quality_assessment": quality_assessment,
        },
    }

    logger.info(
        "Confidence distribution calculated",
        total=len(professors),
        included_high=included_dist["high"],
        included_medium=included_dist["medium"],
        included_low=included_dist["low"],
        excluded_high=excluded_dist["high"],
        excluded_medium=excluded_dist["medium"],
        excluded_low=excluded_dist["low"],
        low_percentage=f"{low_percentage:.1f}%",
        quality=quality_assessment,
    )

    return stats


def save_confidence_stats_report(stats: dict[str, Any]) -> None:
    """Save confidence statistics to JSON file for visualization.

    Story 3.3: Task 8 - Add Confidence Visualization to Reports

    Creates output/filter-confidence-stats.json with:
    - Total professor counts
    - Confidence distribution for included/excluded
    - Distribution quality analysis

    Args:
        stats: Confidence statistics dict from calculate_confidence_stats()
    """
    logger = get_logger(
        correlation_id="confidence-stats-report",
        phase="professor_filtering",
        component="professor_filter",
    )

    # Create output directory if needed
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Save to JSON
    stats_path = output_dir / "filter-confidence-stats.json"

    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    logger.info(
        "Confidence statistics report saved",
        report_path=str(stats_path),
        total_professors=stats["total_professors"],
        quality_assessment=stats["distribution_analysis"]["quality_assessment"],
    )


def apply_manual_overrides(professors: list[Professor]) -> int:
    """Apply manual overrides from config/manual-overrides.json.

    Story 3.3: Task 9 - Enable Manual Override of Low-Confidence Cases

    Loads manual override decisions and applies them to professor records.
    Adds audit trail to professor records for transparency.

    Args:
        professors: List of professors to apply overrides to

    Returns:
        Number of overrides applied
    """
    logger = get_logger(
        correlation_id="manual-overrides",
        phase="professor_filtering",
        component="professor_filter",
    )

    # Check if override file exists
    overrides_path = Path("config/manual-overrides.json")
    if not overrides_path.exists():
        logger.debug("No manual overrides file found, skipping")
        return 0

    # Load overrides
    try:
        with open(overrides_path, "r", encoding="utf-8") as f:
            overrides_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse manual overrides file", error=str(e))
        return 0

    # Get professor overrides list
    professor_overrides = overrides_data.get("professor_overrides", [])

    if not professor_overrides:
        logger.debug("No professor overrides found in file")
        return 0

    # Create professor ID lookup
    professors_by_id = {p.id: p for p in professors}

    # Apply overrides
    override_count = 0
    for override in professor_overrides:
        prof_id = override.get("professor_id")
        new_decision = override.get("decision")
        reason = override.get("reason", "Manual override")
        timestamp = override.get("timestamp", "")
        original_confidence = override.get("original_confidence")
        original_decision = override.get("original_decision")

        # Validate override fields
        if not prof_id or not new_decision:
            logger.warning(
                "Invalid override entry, skipping",
                professor_id=prof_id,
                decision=new_decision,
            )
            continue

        # Find professor
        professor = professors_by_id.get(prof_id)
        if not professor:
            logger.warning(
                "Professor ID not found in filtered list, skipping override",
                professor_id=prof_id,
            )
            continue

        # Apply override
        old_decision = "include" if professor.is_relevant else "exclude"
        professor.is_relevant = new_decision == "include"

        # Add manual override flag
        professor.add_quality_flag("manual_override")

        # Update reasoning with audit trail
        professor.relevance_reasoning = (
            f"MANUAL OVERRIDE ({timestamp}): {reason} | "
            f"Original: {original_decision} (confidence: {original_confidence}) | "
            f"LLM reasoning: {professor.relevance_reasoning}"
        )

        logger.info(
            "Applied manual override",
            professor_id=prof_id,
            professor_name=professor.name,
            old_decision=old_decision,
            new_decision=new_decision,
            reason=reason[:100],
        )

        override_count += 1

    logger.info(
        "Manual overrides applied",
        total_overrides=override_count,
        total_professors=len(professors),
    )

    return override_count


# ============================================================================
# Story 3.4: Filtered Professor Logging & Transparency Functions
# ============================================================================


def log_filter_decision(professor: Professor, correlation_id: str) -> None:
    """Log single filter decision to structured logger.

    Story 3.4: Task 1 - Log All Filter Decisions

    Logs professor filtering decision with all relevant context for transparency.
    Uses professor.is_relevant, relevance_confidence, relevance_reasoning fields.

    Args:
        professor: Professor model with filter decision fields populated
        correlation_id: Correlation ID for logging
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_filtering",
        component="professor_filter",
    )

    # Determine decision string
    decision = "exclude" if not professor.is_relevant else "include"

    logger.info(
        "Filter decision logged",
        component="professor_filter",
        professor_id=professor.id,
        professor_name=professor.name,
        department=professor.department_name,
        school=professor.school or "N/A",
        research_areas=professor.research_areas,
        decision=decision,
        is_relevant=professor.is_relevant,
        relevance_confidence=professor.relevance_confidence,
        relevance_reasoning=professor.relevance_reasoning,
    )


def calculate_filter_statistics(professors: list[Professor]) -> dict[str, Any]:
    """Calculate filtering statistics with edge case handling.

    Story 3.4: Task 4 - Add Filtering Statistics

    Handles edge cases:
    - Empty professor list (total=0)
    - All professors included
    - All professors excluded

    Args:
        professors: List of Professor models with filter decisions

    Returns:
        Dict with total, included, and excluded statistics
    """
    total = len(professors)

    # Edge case: no professors
    if total == 0:
        return {
            "total": 0,
            "included": {
                "count": 0,
                "percentage": 0.0,
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
            },
            "excluded": {
                "count": 0,
                "percentage": 0.0,
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
            },
        }

    included = [p for p in professors if p.is_relevant]
    excluded = [p for p in professors if not p.is_relevant]

    return {
        "total": total,
        "included": {
            "count": len(included),
            "percentage": len(included) / total * 100,
            "high_confidence": len(
                [p for p in included if p.relevance_confidence >= 90]
            ),
            "medium_confidence": len(
                [p for p in included if 70 <= p.relevance_confidence < 90]
            ),
            "low_confidence": len([p for p in included if p.relevance_confidence < 70]),
        },
        "excluded": {
            "count": len(excluded),
            "percentage": len(excluded) / total * 100,
            "high_confidence": len(
                [p for p in excluded if p.relevance_confidence >= 90]
            ),
            "medium_confidence": len(
                [p for p in excluded if 70 <= p.relevance_confidence < 90]
            ),
            "low_confidence": len([p for p in excluded if p.relevance_confidence < 70]),
        },
    }


async def generate_filter_report(
    professors: list[Professor], output_dir: str, correlation_id: str
) -> None:
    """Generate filtered-professors.md report from filtered professor list.

    Story 3.4: Tasks 2, 3, 4, 6, 7 - Complete Transparency Report

    Creates comprehensive markdown report with:
    - Executive summary with statistics
    - Department-level statistics
    - Excluded professors (high/medium/low confidence)
    - Included professors summary
    - Cross-reference to borderline-professors.md
    - Manual override instructions

    Args:
        professors: List of Professor models with filter decisions
        output_dir: Output directory path
        correlation_id: Correlation ID for logging
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_filtering",
        component="professor_filter",
    )

    logger.info("Generating filtered professors report", total_professors=len(professors))

    # Calculate statistics
    stats = calculate_filter_statistics(professors)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Log all filter decisions
    for prof in professors:
        log_filter_decision(prof, correlation_id)

    # Calculate department-level stats
    dept_stats: dict[str, dict[str, int]] = {}
    for prof in professors:
        dept_name = prof.department_name
        if dept_name not in dept_stats:
            dept_stats[dept_name] = {"total": 0, "included": 0, "excluded": 0}
        dept_stats[dept_name]["total"] += 1
        if prof.is_relevant:
            dept_stats[dept_name]["included"] += 1
        else:
            dept_stats[dept_name]["excluded"] += 1

    # Sort departments by inclusion rate
    sorted_depts = sorted(
        dept_stats.items(),
        key=lambda x: (
            (x[1]["included"] / x[1]["total"] * 100) if x[1]["total"] > 0 else 0
        ),
        reverse=True,
    )

    # Check for borderline report
    borderline_report_exists = (Path(output_dir) / "borderline-professors.md").exists()

    # Split professors by decision and confidence
    included = [p for p in professors if p.is_relevant]
    excluded = [p for p in professors if not p.is_relevant]

    # Categorize by confidence
    high_conf_excluded = [p for p in excluded if p.relevance_confidence >= 90]
    med_conf_excluded = [
        p for p in excluded if 70 <= p.relevance_confidence < 90
    ]
    low_conf_excluded = [p for p in excluded if p.relevance_confidence < 70]

    high_conf_included = [p for p in included if p.relevance_confidence >= 90]

    # Generate report
    report_path = output_path / "filtered-professors.md"

    with open(report_path, "w", encoding="utf-8") as f:
        # Header
        f.write("# Filtered Professors Report\n\n")

        # Executive Summary
        f.write("## Executive Summary\n\n")
        f.write(f"- **Total Professors Evaluated:** {stats['total']}\n")
        f.write(
            f"- **Included for Analysis:** {stats['included']['count']} "
            f"({stats['included']['percentage']:.1f}%)\n"
        )
        f.write(
            f"- **Excluded:** {stats['excluded']['count']} "
            f"({stats['excluded']['percentage']:.1f}%)\n"
        )

        # Cross-reference to borderline report if exists
        if borderline_report_exists:
            low_conf_total = (
                stats["included"]["low_confidence"]
                + stats["excluded"]["low_confidence"]
            )
            f.write(
                f"- **Low-Confidence Decisions:** {low_conf_total} "
                f"(see [borderline-professors.md](borderline-professors.md))\n"
            )

        f.write("\n---\n\n")

        # Department-level statistics
        f.write("## Filtering Statistics by Department\n\n")

        if sorted_depts:
            f.write(
                "| Department | Total | Included | Excluded | Inclusion Rate |\n"
            )
            f.write("|------------|-------|----------|----------|----------------|\n")

            for dept_name, dept_data in sorted_depts:
                inclusion_rate = (
                    (dept_data["included"] / dept_data["total"] * 100)
                    if dept_data["total"] > 0
                    else 0
                )
                f.write(
                    f"| {dept_name} | {dept_data['total']} | {dept_data['included']} | "
                    f"{dept_data['excluded']} | {inclusion_rate:.0f}% |\n"
                )
        else:
            f.write("*No department data available.*\n")

        f.write("\n---\n\n")

        # Excluded Professors
        f.write("## Excluded Professors\n\n")

        # High Confidence Exclusions
        f.write(f"### High Confidence Exclusions (≥90) - {len(high_conf_excluded)} professors\n\n")

        if high_conf_excluded:
            f.write(
                "| Professor | Department | Research Areas | Confidence | Reason |\n"
            )
            f.write("|-----------|------------|----------------|------------|--------|\n")

            for prof in high_conf_excluded[:50]:  # Limit to 50 for readability
                research_str = ", ".join(prof.research_areas[:3])
                if len(prof.research_areas) > 3:
                    research_str += "..."
                reason_short = (
                    prof.relevance_reasoning[:100] + "..."
                    if len(prof.relevance_reasoning) > 100
                    else prof.relevance_reasoning
                )
                f.write(
                    f"| [{prof.name}]({prof.profile_url}) | {prof.department_name} | "
                    f"{research_str} | {prof.relevance_confidence} | {reason_short} |\n"
                )

            if len(high_conf_excluded) > 50:
                f.write(f"\n*...and {len(high_conf_excluded) - 50} more.*\n")
        else:
            f.write("*No high-confidence exclusions.*\n")

        f.write("\n")

        # Medium Confidence Exclusions
        f.write(f"### Medium Confidence Exclusions (70-89) - {len(med_conf_excluded)} professors\n\n")

        if med_conf_excluded:
            f.write(
                "| Professor | Department | Research Areas | Confidence | Reason |\n"
            )
            f.write("|-----------|------------|----------------|------------|--------|\n")

            for prof in med_conf_excluded[:20]:
                research_str = ", ".join(prof.research_areas[:3])
                if len(prof.research_areas) > 3:
                    research_str += "..."
                reason_short = (
                    prof.relevance_reasoning[:100] + "..."
                    if len(prof.relevance_reasoning) > 100
                    else prof.relevance_reasoning
                )
                f.write(
                    f"| [{prof.name}]({prof.profile_url}) | {prof.department_name} | "
                    f"{research_str} | {prof.relevance_confidence} | {reason_short} |\n"
                )

            if len(med_conf_excluded) > 20:
                f.write(f"\n*...and {len(med_conf_excluded) - 20} more.*\n")
        else:
            f.write("*No medium-confidence exclusions.*\n")

        f.write("\n")

        # Low Confidence Exclusions
        f.write(f"### Low Confidence Exclusions (<70) - {len(low_conf_excluded)} professors\n\n")
        f.write("**⚠️ Review Recommended**")

        if borderline_report_exists:
            f.write(" - See [borderline-professors.md](borderline-professors.md)\n\n")
        else:
            f.write("\n\n")

        if low_conf_excluded:
            f.write(
                "| Professor | Department | Research Areas | Confidence | Reason |\n"
            )
            f.write("|-----------|------------|----------------|------------|--------|\n")

            for prof in low_conf_excluded[:20]:
                research_str = ", ".join(prof.research_areas[:3])
                if len(prof.research_areas) > 3:
                    research_str += "..."
                reason_short = (
                    prof.relevance_reasoning[:100] + "..."
                    if len(prof.relevance_reasoning) > 100
                    else prof.relevance_reasoning
                )
                f.write(
                    f"| [{prof.name}]({prof.profile_url}) | {prof.department_name} | "
                    f"{research_str} | {prof.relevance_confidence} | {reason_short} |\n"
                )

            if len(low_conf_excluded) > 20:
                f.write(f"\n*...and {len(low_conf_excluded) - 20} more.*\n")
        else:
            f.write("*No low-confidence exclusions.*\n")

        f.write("\n---\n\n")

        # Included Professors Summary (Task 3)
        f.write("## Included Professors Summary\n\n")
        f.write(f"### High Confidence Inclusions (≥90) - {len(high_conf_included)} professors\n\n")

        if high_conf_included:
            f.write(
                "| Professor | Department | Research Areas | Confidence | Matching Reason |\n"
            )
            f.write(
                "|-----------|------------|----------------|------------|------------------|\n"
            )

            for prof in high_conf_included[:20]:
                research_str = ", ".join(prof.research_areas[:3])
                if len(prof.research_areas) > 3:
                    research_str += "..."
                reason_short = (
                    prof.relevance_reasoning[:100] + "..."
                    if len(prof.relevance_reasoning) > 100
                    else prof.relevance_reasoning
                )
                f.write(
                    f"| [{prof.name}]({prof.profile_url}) | {prof.department_name} | "
                    f"{research_str} | {prof.relevance_confidence} | {reason_short} |\n"
                )

            if len(high_conf_included) > 20:
                f.write(
                    f"\n*Top 20 shown. Total high-confidence inclusions: {len(high_conf_included)}*\n"
                )
        else:
            f.write("*No high-confidence inclusions.*\n")

        f.write("\n---\n\n")

        # Detailed Exclusion Reasoning section
        f.write("## Detailed Exclusion Reasoning\n\n")

        # Show top 10 excluded with full reasoning
        for i, prof in enumerate(excluded[:10], 1):
            f.write(f"### {i}. {prof.name} (Excluded)\n\n")
            f.write(f"- **Department:** {prof.department_name}\n")
            if prof.school:
                f.write(f"- **School:** {prof.school}\n")
            f.write(f"- **Research Areas:** {', '.join(prof.research_areas) if prof.research_areas else 'Not specified'}\n")
            f.write(f"- **Confidence:** {prof.relevance_confidence}\n")
            f.write(f"- **Reasoning:** {prof.relevance_reasoning}\n")
            f.write(f"- **Profile:** [{prof.profile_url}]({prof.profile_url})\n\n")

        if len(excluded) > 10:
            f.write(f"*...and {len(excluded) - 10} more excluded professors.*\n\n")

        f.write("---\n\n")

        # How to Override Filter Decisions (Task 6)
        f.write("## How to Override Filter Decisions\n\n")
        f.write("If you believe a professor was incorrectly filtered:\n\n")
        f.write("1. Create/edit `config/manual-professor-additions.json`\n")
        f.write("2. Add professor ID to \"additions\" list\n")
        f.write("3. Re-run the pipeline from Phase 3\n\n")
        f.write("The professor will be included in subsequent analysis.\n\n")
        f.write("**Example format:**\n\n")
        f.write("```json\n")
        f.write("{\n")
        f.write('  "additions": [\n')
        f.write("    {\n")
        f.write('      "professor_id": "prof-456",\n')
        f.write('      "reason": "User identified as relevant despite filter"\n')
        f.write("    }\n")
        f.write("  ]\n")
        f.write("}\n")
        f.write("```\n\n")

        # Cross-reference note (Task 7)
        if borderline_report_exists:
            f.write("---\n\n")
            f.write("**Note:** See `borderline-professors.md` for low-confidence\n")
            f.write("decisions that may require manual review.\n")

    logger.info(
        "Filtered professors report generated",
        report_path=str(report_path),
        total_professors=len(professors),
        included=stats["included"]["count"],
        excluded=stats["excluded"]["count"],
    )


async def load_manual_additions(config_path: str = "config/manual-professor-additions.json") -> dict[str, Any]:
    """Load manual professor additions from config file.

    Story 3.4: Task 5 - Enable Manual Professor Addition

    Loads JSON file with manual professor additions. File is optional -
    returns empty dict if not found.

    Args:
        config_path: Path to manual additions JSON file

    Returns:
        Dict with "additions" list or empty dict if file doesn't exist
    """
    logger = get_logger(
        correlation_id="manual-additions",
        phase="professor_filtering",
        component="professor_filter",
    )

    additions_path = Path(config_path)

    if not additions_path.exists():
        logger.debug("Manual additions file not found, no additions to apply", path=config_path)
        return {"additions": []}

    try:
        with open(additions_path, "r", encoding="utf-8") as f:
            additions_data = json.load(f)

        logger.info(
            "Manual additions loaded",
            path=config_path,
            additions_count=len(additions_data.get("additions", [])),
        )

        return additions_data

    except json.JSONDecodeError as e:
        logger.error("Failed to parse manual additions file", path=config_path, error=str(e))
        return {"additions": []}
    except Exception as e:
        logger.error("Failed to load manual additions", path=config_path, error=str(e))
        return {"additions": []}


async def apply_manual_additions(
    professors: list[Professor], additions: dict[str, Any], correlation_id: str
) -> list[Professor]:
    """Apply manual overrides to professor list.

    Story 3.4: Task 5 - Enable Manual Professor Addition

    Matches professor IDs from additions to filtered professors.
    Sets is_relevant = True and adds "manual_addition" flag.

    EXECUTION TIMING: Must execute BEFORE report generation to include
    overridden professors in reports.

    Args:
        professors: List of Professor models to apply additions to
        additions: Dict from load_manual_additions()
        correlation_id: Correlation ID for logging

    Returns:
        Updated list of Professor models with manual additions applied
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="professor_filtering",
        component="professor_filter",
    )

    additions_list = additions.get("additions", [])

    if not additions_list:
        logger.debug("No manual additions to apply")
        return professors

    # Create professor ID lookup
    professors_by_id = {p.id: p for p in professors}

    addition_count = 0

    for addition in additions_list:
        prof_id = addition.get("professor_id")
        reason = addition.get("reason", "User manually added despite filter")

        if not prof_id:
            logger.warning("Invalid addition entry, missing professor_id", addition=addition)
            continue

        # Find professor
        professor = professors_by_id.get(prof_id)

        if not professor:
            logger.warning(
                "Professor ID not found in filtered list, cannot apply addition",
                professor_id=prof_id,
            )
            continue

        # Apply manual addition
        old_decision = "include" if professor.is_relevant else "exclude"

        # Override to include
        professor.is_relevant = True

        # Add manual_addition flag
        professor.add_quality_flag("manual_addition")

        # Update reasoning with manual addition note
        professor.relevance_reasoning = (
            f"MANUAL ADDITION: {reason} | "
            f"Original decision: {old_decision} (confidence: {professor.relevance_confidence}) | "
            f"Original reasoning: {professor.relevance_reasoning}"
        )

        logger.info(
            "Applied manual addition",
            professor_id=prof_id,
            professor_name=professor.name,
            old_decision=old_decision,
            new_decision="include",
            reason=reason[:100],
        )

        addition_count += 1

    logger.info(
        "Manual additions applied",
        total_additions=addition_count,
        total_professors=len(professors),
    )

    # Save updated professors to checkpoint
    if addition_count > 0:
        checkpoint_manager = CheckpointManager()
        checkpoint_manager.save_batch(
            phase="phase-2-professors-with-manual-additions",
            batch_id=1,
            data=professors,
        )
        logger.info(
            "Saved professors with manual additions to checkpoint",
            checkpoint_file="checkpoints/phase-2-professors-with-manual-additions-batch-1.jsonl",
        )

    return professors
