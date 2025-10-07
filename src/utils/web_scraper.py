"""Web scraping utilities with tiered fallback pattern.

Implements: httpx → Playwright → Skip with flag
"""

from typing import Optional, Any
from bs4 import BeautifulSoup
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.utils.logger import get_logger


class WebScraperError(Exception):
    """Base exception for web scraping errors."""

    pass


class WebScraper:
    """Web scraper with built-in retry logic and fallback patterns."""

    def __init__(self, correlation_id: str, timeout: int = 30):
        """Initialize web scraper.

        Args:
            correlation_id: Unique ID for tracing scraping session
            timeout: Request timeout in seconds (default: 30)
        """
        self.correlation_id = correlation_id
        self.timeout = timeout
        self.logger: Any = get_logger(
            correlation_id=correlation_id,
            phase="web_scraping",
            component="web_scraper",
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def fetch_html(self, url: str) -> str:
        """Fetch HTML content with retry logic.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string

        Raises:
            httpx.HTTPStatusError: For non-retryable errors (404, 403, etc.)
            httpx.TimeoutException: After max retries exceeded
            httpx.NetworkError: After max retries exceeded
        """
        self.logger.info("Fetching HTML", url=url, method="httpx")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            self.logger.info(
                "HTML fetched successfully",
                url=url,
                status_code=response.status_code,
                content_length=len(response.text),
            )

            return response.text

    async def fetch_with_playwright(self, url: str) -> str:
        """Fetch HTML using Playwright for JS-heavy pages.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string

        Raises:
            WebScraperError: If Playwright scraping fails
        """
        self.logger.info("Fetching HTML with Playwright", url=url, method="playwright")

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Navigate and wait for page load
                await page.goto(
                    url, wait_until="networkidle", timeout=self.timeout * 1000
                )

                # Get page content
                html_content = await page.content()

                await browser.close()

                self.logger.info(
                    "HTML fetched with Playwright",
                    url=url,
                    content_length=len(html_content),
                )

                return html_content

        except Exception as e:
            self.logger.error(
                "Playwright scraping failed",
                url=url,
                error_type=type(e).__name__,
                error=str(e),
            )
            raise WebScraperError(f"Playwright failed for {url}: {str(e)}") from e

    async def fetch_with_fallback(
        self, url: str, use_playwright: bool = False
    ) -> tuple[Optional[str], str]:
        """Fetch HTML with tiered fallback pattern.

        Tries: httpx → Playwright → None

        Args:
            url: URL to fetch
            use_playwright: If True, skip httpx and go directly to Playwright

        Returns:
            Tuple of (html_content, method_used)
            - html_content: HTML string or None if all methods failed
            - method_used: "httpx", "playwright", or "failed"
        """
        if not use_playwright:
            # Try httpx first
            try:
                html = await self.fetch_html(url)
                return (html, "httpx")
            except httpx.HTTPStatusError as e:
                self.logger.warning(
                    "HTTP error, trying Playwright fallback",
                    url=url,
                    status_code=e.response.status_code,
                )
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                self.logger.warning(
                    "Network error after retries, trying Playwright fallback",
                    url=url,
                    error=str(e),
                )

        # Try Playwright fallback
        try:
            html = await self.fetch_with_playwright(url)
            return (html, "playwright")
        except WebScraperError:
            self.logger.error(
                "All scraping methods failed",
                url=url,
                methods_tried=["httpx", "playwright"]
                if not use_playwright
                else ["playwright"],
            )
            return (None, "failed")

    def parse_html(self, html_content: str) -> BeautifulSoup:
        """Parse HTML content with BeautifulSoup.

        Args:
            html_content: HTML string

        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html_content, "html.parser")
