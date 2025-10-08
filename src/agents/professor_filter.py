"""Professor Discovery & Filter Agent.

Combined agent for professor discovery and filtering operations.
- Story 3.1a: Discovery functions (this implementation)
- Story 3.1b: Parallel processing functions (this implementation)
- Story 3.1c: Deduplication, rate limiting, and checkpointing (this implementation)
- Story 3.2: Filtering functions (to be added)
"""

import asyncio
import hashlib
import json
import re
import uuid
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

from src.models.department import Department
from src.models.professor import Professor
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.llm_helpers import match_names
from src.utils.logger import get_logger

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
    elements: list, department: Department
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
                    list(p.get("research_areas", []))  # type: ignore[arg-type, call-overload]
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
                        list(research_areas_val)  # type: ignore[arg-type]
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
                f"Processing department {index+1}/{len(departments)}",
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
    tasks = [
        process_with_semaphore(dept, i) for i, dept in enumerate(departments)
    ]

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
