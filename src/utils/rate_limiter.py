"""Per-domain rate limiting utility.

Story 3.1c: Task 1 - DomainRateLimiter class for respectful web scraping.
"""

from urllib.parse import urlparse

from aiolimiter import AsyncLimiter


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
