"""Multi-stage web scraping utilities with Puppeteer MCP fallback.

This module provides robust web scraping with automatic escalation from WebFetch
to Puppeteer MCP when data is insufficient, along with sufficiency evaluation,
rate limiting, and robots.txt compliance.

Pattern: WebFetch → Sufficiency → Puppeteer MCP → Re-evaluate (max 3 attempts)
"""

import json
import re
from pathlib import Path
from typing import Any, TypedDict, cast
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from aiolimiter import AsyncLimiter
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

from src.utils.logger import get_logger


class ScrapingResult(TypedDict):
    """Result from multi-stage web scraping."""
    data: dict[str, Any]
    sufficient: bool
    missing_fields: list[str]
    attempts: int


async def scrape_with_sufficiency(
    url: str,
    required_fields: list[str],
    max_attempts: int = 3,
    correlation_id: str = ""
) -> ScrapingResult:
    """Multi-stage web scraping with sufficiency evaluation.

    Stages:
    1. WebFetch Attempt → Extract data using built-in tools
    2. Sufficiency Evaluation → LLM determines if data complete
    3. Puppeteer MCP Fallback → Use browser automation if insufficient
    4. Re-evaluate → Check completeness again
    5. Retry or Return → Loop up to max_attempts, then return best effort

    Args:
        url: Target URL to scrape
        required_fields: List of required data fields
        max_attempts: Maximum scraping attempts (default: 3)
        correlation_id: Correlation ID for logging

    Returns:
        ScrapingResult with data, sufficiency flag, missing fields, attempts

    Data Quality Flags:
        - insufficient_webfetch: WebFetch didn't extract all required fields
        - puppeteer_mcp_used: Escalated to Puppeteer MCP fallback
        - sufficiency_evaluation_failed: Could not determine completeness
    """
    logger = get_logger(correlation_id=correlation_id, component="web-scraping")
    attempt = 0
    scraped_data = {}
    sufficiency_result = {"sufficient": False, "missing_fields": required_fields}

    while attempt < max_attempts:
        attempt += 1
        logger.info("Starting scraping attempt", url=url, attempt=attempt, max_attempts=max_attempts)

        # Stage 1 or 3: Scrape with appropriate tool
        if attempt == 1:
            # Use WebFetch (fast, simple)
            logger.debug("Stage 1: Using WebFetch", url=url)
            try:
                scraped_data = await _scrape_with_webfetch(url, required_fields, correlation_id)
            except Exception as e:
                logger.warning("WebFetch failed", url=url, error=str(e))
                scraped_data = {}
        else:
            # Use Puppeteer MCP (handles JS-rendered content)
            logger.debug("Stage 3: Using Puppeteer MCP", url=url)
            try:
                scraped_data = await _scrape_with_puppeteer_mcp(url, required_fields, correlation_id)
            except Exception as e:
                logger.error("Puppeteer MCP failed", url=url, error=str(e))
                # Continue with existing scraped_data (may be partial)

        # Stage 2 or 4: Evaluate sufficiency
        logger.debug("Evaluating sufficiency", url=url, attempt=attempt)
        sufficiency_result = await evaluate_sufficiency(
            scraped_data, required_fields, correlation_id
        )

        if sufficiency_result["sufficient"]:
            logger.info("Scraping sufficient", url=url, attempt=attempt)
            return ScrapingResult(
                data=scraped_data,
                sufficient=True,
                missing_fields=[],
                attempts=attempt
            )

        logger.warning(
            "Scraping insufficient, retrying",
            url=url,
            attempt=attempt,
            missing=sufficiency_result["missing_fields"]
        )

    # Max attempts reached - return best effort
    logger.error("Max scraping attempts reached", url=url, attempts=max_attempts)
    return ScrapingResult(
        data=scraped_data,
        sufficient=False,
        missing_fields=cast(list[str], sufficiency_result.get("missing_fields", required_fields)),
        attempts=max_attempts
    )


async def _scrape_with_webfetch(
    url: str,
    required_fields: list[str],
    correlation_id: str
) -> dict[str, Any]:
    """Scrape URL using WebFetch tool."""
    options = ClaudeAgentOptions(
        cwd=Path(__file__).parent.parent.parent / "claude",
        setting_sources=None,  # Isolated context
        allowed_tools=["WebFetch"],
        max_turns=2,
        system_prompt="You are a web scraping assistant. Extract the requested data fields from the provided URL."
    )

    prompt = f"""Scrape the following URL and extract these data fields:
URL: {url}
Required fields: {', '.join(required_fields)}

Return the extracted data as a JSON object with the field names as keys.
"""

    response_text = ""
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        async for message in client.receive_response():
            if hasattr(message, "content") and message.content:
                for block in message.content:
                    if hasattr(block, "text"):
                        response_text += block.text

    # Parse JSON from response
    return _parse_json_from_text(response_text)


async def _scrape_with_puppeteer_mcp(
    url: str,
    required_fields: list[str],
    correlation_id: str
) -> dict[str, Any]:
    """Scrape URL using Puppeteer MCP tools."""
    options = ClaudeAgentOptions(
        cwd=Path(__file__).parent.parent.parent / "claude",
        setting_sources=["project"],  # Loads .mcp.json
        allowed_tools=["mcp__puppeteer__navigate", "mcp__puppeteer__evaluate"],
        max_turns=5,
        system_prompt="You are a web scraping assistant using Puppeteer MCP. Navigate to the URL and extract the requested data."
    )

    prompt = f"""Use Puppeteer MCP to scrape the following URL:
URL: {url}
Required fields: {', '.join(required_fields)}

Steps:
1. Use mcp__puppeteer__navigate to load the page
2. Use mcp__puppeteer__evaluate to execute JavaScript and extract data
3. Return the extracted data as a JSON object

Return the extracted data as a JSON object with the field names as keys.
"""

    response_text = ""
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        async for message in client.receive_response():
            if hasattr(message, "content") and message.content:
                for block in message.content:
                    if hasattr(block, "text"):
                        response_text += block.text

    # Parse JSON from response
    return _parse_json_from_text(response_text)


def _parse_json_from_text(text: str) -> dict[str, Any]:
    """Parse JSON from various text formats.

    Handles 4 formats:
    1. Markdown JSON codeblock: ```json { ... } ```
    2. Generic codeblock: ``` { ... } ```
    3. Raw JSON object: { ... }
    4. Plain text fallback

    Args:
        text: Text containing JSON data

    Returns:
        Parsed JSON dict, or empty dict if parsing fails
    """
    # Try 4 formats
    patterns = [
        r'```json\s*(.*?)\s*```',  # Markdown JSON codeblock
        r'```\s*(.*?)\s*```',       # Generic codeblock
        r'\{.*\}',                   # Raw JSON object
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                json_text = match.group(1) if '```' in pattern else match.group(0)
                return cast(dict[str, Any], json.loads(json_text))
            except json.JSONDecodeError:
                continue

    # Fallback: try parsing entire text
    try:
        return cast(dict[str, Any], json.loads(text))
    except json.JSONDecodeError:
        return {}


async def evaluate_sufficiency(
    data: dict[str, Any],
    required_fields: list[str],
    correlation_id: str
) -> dict[str, Any]:
    """Evaluate if scraped data is sufficient.

    NOTE: thinking parameter NOT supported in SDK v0.1.1.
    Uses strong system_prompt instructions instead.

    Args:
        data: Scraped data to evaluate
        required_fields: List of required fields
        correlation_id: Correlation ID for logging

    Returns:
        Dict with 'sufficient' (bool) and 'missing_fields' (list)
    """
    logger = get_logger(correlation_id=correlation_id, component="sufficiency-eval")

    options = ClaudeAgentOptions(
        cwd=Path(__file__).parent.parent.parent / "claude",
        setting_sources=None,  # Isolated context
        allowed_tools=[],
        max_turns=1,
        system_prompt=(
            "You are a data quality evaluator. Analyze scraped data and determine "
            "if it contains all required fields. Think through your analysis step-by-step:\n"
            "1. Check each required field for presence\n"
            "2. Verify field values are non-empty\n"
            "3. Determine overall sufficiency\n\n"
            "Output ONLY a JSON object with 'sufficient' (boolean) and 'missing_fields' (array). "
            "Do not include any explanatory text outside the JSON."
        )
    )

    prompt = f"""Evaluate this scraped data:
{json.dumps(data, indent=2)}

Required fields: {required_fields}

Output format (JSON only):
{{
  "sufficient": true/false,
  "missing_fields": ["field1", "field2"]
}}
"""

    # Retry JSON parsing up to 3 times
    for retry in range(3):
        try:
            response_text = ""
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)

                async for message in client.receive_response():
                    if hasattr(message, "content") and message.content:
                        for block in message.content:
                            if hasattr(block, "text"):
                                response_text += block.text

            result = _parse_json_from_text(response_text)

            # Validate result structure
            if "sufficient" in result and "missing_fields" in result:
                logger.info("Sufficiency evaluation complete", sufficient=result["sufficient"], missing=result["missing_fields"])
                return result

        except json.JSONDecodeError:
            logger.warning(f"JSON parse failed, retry {retry+1}/3", correlation_id=correlation_id)
            continue

    # Failed to parse - conservative fallback: assume insufficient
    logger.error("Sufficiency evaluation failed after 3 retries", correlation_id=correlation_id)
    return {"sufficient": False, "missing_fields": required_fields}


class DomainRateLimiter:
    """Per-domain rate limiting to prevent blocking."""

    def __init__(self, default_rate: int = 1):
        """Initialize rate limiter.

        Args:
            default_rate: Default requests per second per domain (default: 1)
        """
        self.limiters: dict[str, AsyncLimiter] = {}
        self.default_rate = default_rate

    async def acquire(self, url: str) -> None:
        """Acquire rate limit token for URL's domain.

        Args:
            url: Target URL (domain extracted from URL)
        """
        domain = urlparse(url).netloc

        if domain not in self.limiters:
            # Create limiter for new domain
            self.limiters[domain] = AsyncLimiter(
                max_rate=self.default_rate,
                time_period=1.0  # per second
            )

        await self.limiters[domain].acquire()


async def check_robots_txt(url: str, user_agent: str = "LabFinder/1.0") -> bool:
    """Check if URL is allowed by robots.txt.

    Args:
        url: Target URL to check
        user_agent: User agent string (default: "LabFinder/1.0")

    Returns:
        True if allowed, False if disallowed
    """
    logger = get_logger(component="robots-txt-checker")

    try:
        parser = RobotFileParser()
        robots_url = urljoin(url, "/robots.txt")

        # Fetch robots.txt
        async with httpx.AsyncClient() as client:
            response = await client.get(robots_url, timeout=5.0)
            robots_content = response.text

        parser.parse(robots_content.splitlines())

        # Check if URL is allowed
        allowed = parser.can_fetch(user_agent, url)

        if not allowed:
            logger.warning("robots.txt disallows scraping", url=url)

        return allowed

    except Exception as e:
        logger.debug("Could not check robots.txt, assuming allowed", url=url, error=str(e))
        # If robots.txt unavailable, assume allowed
        return True
