"""Unit tests for multi-stage web scraping utilities.

Tests cover:
- Multi-stage pattern progression (WebFetch → Puppeteer MCP)
- Sufficiency evaluation
- Rate limiting
- robots.txt compliance
- JSON parsing
- Graceful degradation
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.utils.web_scraping import (
    DomainRateLimiter,
    ScrapingResult,
    _parse_json_from_text,
    check_robots_txt,
    evaluate_sufficiency,
    scrape_with_sufficiency,
)


class TestMultiStagePattern:
    """Test multi-stage scraping pattern."""

    @pytest.mark.asyncio
    async def test_webfetch_sufficient_returns_immediately(self, mocker):
        """Test Stage 1 (WebFetch) succeeds with sufficient data."""
        # Arrange
        mock_webfetch = mocker.patch('src.utils.web_scraping._scrape_with_webfetch')
        mock_webfetch.return_value = {
            "lab_information": "AI Research Lab",
            "contact": "contact@example.edu",
            "people": ["Dr. Smith", "Dr. Jones"],
            "research_focus": "Machine Learning",
            "publications": ["Paper 1", "Paper 2"]
        }

        mock_evaluate = mocker.patch('src.utils.web_scraping.evaluate_sufficiency')
        mock_evaluate.return_value = {"sufficient": True, "missing_fields": []}

        mock_puppeteer = mocker.patch('src.utils.web_scraping._scrape_with_puppeteer_mcp')

        # Act
        result = await scrape_with_sufficiency(
            url="https://test.edu/lab",
            required_fields=["lab_information", "contact", "people", "research_focus", "publications"],
            max_attempts=3,
            correlation_id="test-corr-id"
        )

        # Assert
        assert result["sufficient"] is True
        assert result["attempts"] == 1
        assert len(result["missing_fields"]) == 0
        assert "lab_information" in result["data"]
        mock_webfetch.assert_called_once()
        mock_puppeteer.assert_not_called()

    @pytest.mark.asyncio
    async def test_escalates_to_puppeteer_when_webfetch_insufficient(self, mocker):
        """Test escalation to Puppeteer MCP when WebFetch insufficient."""
        # Arrange
        mock_webfetch = mocker.patch('src.utils.web_scraping._scrape_with_webfetch')
        mock_webfetch.return_value = {"lab_information": "AI Lab"}  # Incomplete

        mock_puppeteer = mocker.patch('src.utils.web_scraping._scrape_with_puppeteer_mcp')
        mock_puppeteer.return_value = {
            "lab_information": "AI Lab",
            "contact": "contact@example.edu",
            "people": ["Dr. Smith"],
            "research_focus": "ML",
            "publications": ["Paper 1"]
        }

        mock_evaluate = mocker.patch('src.utils.web_scraping.evaluate_sufficiency')
        mock_evaluate.side_effect = [
            {"sufficient": False, "missing_fields": ["contact", "people", "research_focus", "publications"]},
            {"sufficient": True, "missing_fields": []}
        ]

        # Act
        result = await scrape_with_sufficiency(
            url="https://test.edu/lab",
            required_fields=["lab_information", "contact", "people", "research_focus", "publications"],
            max_attempts=3,
            correlation_id="test-corr-id"
        )

        # Assert
        assert result["sufficient"] is True
        assert result["attempts"] == 2  # WebFetch + Puppeteer
        mock_webfetch.assert_called_once()
        mock_puppeteer.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_attempts_returns_partial_data(self, mocker):
        """Test max attempts reached returns partial data with flags."""
        # Arrange
        mock_webfetch = mocker.patch('src.utils.web_scraping._scrape_with_webfetch')
        mock_webfetch.return_value = {"lab_information": "AI Lab"}

        mock_puppeteer = mocker.patch('src.utils.web_scraping._scrape_with_puppeteer_mcp')
        mock_puppeteer.return_value = {"lab_information": "AI Lab", "contact": "test@edu"}

        mock_evaluate = mocker.patch('src.utils.web_scraping.evaluate_sufficiency')
        mock_evaluate.return_value = {"sufficient": False, "missing_fields": ["people", "research_focus"]}

        # Act
        result = await scrape_with_sufficiency(
            url="https://test.edu/lab",
            required_fields=["lab_information", "contact", "people", "research_focus"],
            max_attempts=3,
            correlation_id="test-corr-id"
        )

        # Assert
        assert result["sufficient"] is False
        assert result["attempts"] == 3
        assert "people" in result["missing_fields"]
        assert "research_focus" in result["missing_fields"]
        assert result["data"]["lab_information"] == "AI Lab"  # Partial data returned

    @pytest.mark.asyncio
    async def test_webfetch_failure_continues_to_puppeteer(self, mocker):
        """Test WebFetch exception triggers Puppeteer MCP fallback."""
        # Arrange
        mock_webfetch = mocker.patch('src.utils.web_scraping._scrape_with_webfetch')
        mock_webfetch.side_effect = Exception("Network error")

        mock_puppeteer = mocker.patch('src.utils.web_scraping._scrape_with_puppeteer_mcp')
        mock_puppeteer.return_value = {"lab_information": "AI Lab", "contact": "test@edu"}

        mock_evaluate = mocker.patch('src.utils.web_scraping.evaluate_sufficiency')
        mock_evaluate.side_effect = [
            {"sufficient": False, "missing_fields": ["lab_information", "contact"]},  # After WebFetch failure
            {"sufficient": True, "missing_fields": []}  # After Puppeteer success
        ]

        # Act
        result = await scrape_with_sufficiency(
            url="https://test.edu/lab",
            required_fields=["lab_information", "contact"],
            max_attempts=3,
            correlation_id="test-corr-id"
        )

        # Assert
        assert result["sufficient"] is True
        assert result["attempts"] == 2
        mock_puppeteer.assert_called_once()


class TestSufficiencyEvaluation:
    """Test sufficiency evaluation logic."""

    @pytest.mark.asyncio
    async def test_evaluates_complete_data_as_sufficient(self, mocker):
        """Test complete data evaluated as sufficient."""
        # Arrange
        mock_message = MagicMock()
        mock_block = MagicMock()
        mock_block.text = '{"sufficient": true, "missing_fields": []}'
        mock_message.content = [mock_block]

        async def mock_receive():
            yield mock_message

        mock_client_instance = mocker.MagicMock()
        mock_client_instance.receive_response = mock_receive
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.query = AsyncMock()

        mocker.patch('src.utils.web_scraping.ClaudeSDKClient', return_value=mock_client_instance)

        # Act
        result = await evaluate_sufficiency(
            data={"field1": "value1", "field2": "value2"},
            required_fields=["field1", "field2"],
            correlation_id="test-corr-id"
        )

        # Assert
        assert result["sufficient"] is True
        assert len(result["missing_fields"]) == 0

    @pytest.mark.asyncio
    async def test_evaluates_partial_data_as_insufficient(self, mocker):
        """Test partial data evaluated as insufficient with missing fields."""
        # Arrange
        mock_message = MagicMock()
        mock_block = MagicMock()
        mock_block.text = '{"sufficient": false, "missing_fields": ["field2", "field3"]}'
        mock_message.content = [mock_block]

        async def mock_receive():
            yield mock_message

        mock_client_instance = mocker.MagicMock()
        mock_client_instance.receive_response = mock_receive
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.query = AsyncMock()

        mocker.patch('src.utils.web_scraping.ClaudeSDKClient', return_value=mock_client_instance)

        # Act
        result = await evaluate_sufficiency(
            data={"field1": "value1"},
            required_fields=["field1", "field2", "field3"],
            correlation_id="test-corr-id"
        )

        # Assert
        assert result["sufficient"] is False
        assert "field2" in result["missing_fields"]
        assert "field3" in result["missing_fields"]

    @pytest.mark.asyncio
    async def test_malformed_json_retries_then_assumes_insufficient(self, mocker):
        """Test malformed JSON triggers retries then conservative fallback."""
        # Arrange
        mock_message = MagicMock()
        mock_block = MagicMock()
        mock_block.text = 'This is not JSON at all'
        mock_message.content = [mock_block]

        async def mock_receive():
            yield mock_message

        mock_client_instance = mocker.MagicMock()
        mock_client_instance.receive_response = mock_receive
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.query = AsyncMock()

        mocker.patch('src.utils.web_scraping.ClaudeSDKClient', return_value=mock_client_instance)

        # Act
        result = await evaluate_sufficiency(
            data={"field1": "value1"},
            required_fields=["field1", "field2"],
            correlation_id="test-corr-id"
        )

        # Assert - conservative fallback: assume insufficient
        assert result["sufficient"] is False
        assert result["missing_fields"] == ["field1", "field2"]


class TestJSONParsing:
    """Test JSON parsing from various formats."""

    def test_parse_markdown_json_codeblock(self):
        """Test parsing markdown JSON codeblock format."""
        text = '```json\n{"field1": "value1", "field2": "value2"}\n```'
        result = _parse_json_from_text(text)
        assert result == {"field1": "value1", "field2": "value2"}

    def test_parse_generic_codeblock(self):
        """Test parsing generic codeblock format."""
        text = '```\n{"field1": "value1", "field2": "value2"}\n```'
        result = _parse_json_from_text(text)
        assert result == {"field1": "value1", "field2": "value2"}

    def test_parse_raw_json(self):
        """Test parsing raw JSON object."""
        text = '{"field1": "value1", "field2": "value2"}'
        result = _parse_json_from_text(text)
        assert result == {"field1": "value1", "field2": "value2"}

    def test_parse_json_with_surrounding_text(self):
        """Test parsing JSON object within surrounding text."""
        text = 'Here is the data: {"field1": "value1", "field2": "value2"} and some more text'
        result = _parse_json_from_text(text)
        assert result == {"field1": "value1", "field2": "value2"}

    def test_parse_invalid_json_returns_empty_dict(self):
        """Test invalid JSON returns empty dict."""
        text = 'This is not JSON'
        result = _parse_json_from_text(text)
        assert result == {}

    def test_parse_empty_string_returns_empty_dict(self):
        """Test empty string returns empty dict."""
        text = ''
        result = _parse_json_from_text(text)
        assert result == {}


class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_creates_limiter_per_domain(self):
        """Test rate limiter creates separate limiters per domain."""
        limiter = DomainRateLimiter(default_rate=2)

        # Should create separate limiters for different domains
        await limiter.acquire("https://domain1.edu/page1")
        await limiter.acquire("https://domain2.edu/page1")

        assert len(limiter.limiters) == 2
        assert "domain1.edu" in limiter.limiters
        assert "domain2.edu" in limiter.limiters

    @pytest.mark.asyncio
    async def test_reuses_limiter_for_same_domain(self):
        """Test rate limiter reuses limiter for same domain."""
        limiter = DomainRateLimiter(default_rate=2)

        await limiter.acquire("https://example.edu/page1")
        await limiter.acquire("https://example.edu/page2")

        assert len(limiter.limiters) == 1
        assert "example.edu" in limiter.limiters

    @pytest.mark.asyncio
    async def test_default_rate_applied(self):
        """Test default rate is applied to new limiters."""
        limiter = DomainRateLimiter(default_rate=5)

        await limiter.acquire("https://test.edu/page")

        assert limiter.limiters["test.edu"].max_rate == 5


class TestRobotsTxt:
    """Test robots.txt compliance checking."""

    @pytest.mark.asyncio
    async def test_allowed_by_robots_txt(self, mocker):
        """Test URL allowed by robots.txt."""
        # Mock httpx.AsyncClient.get
        mock_response = MagicMock()
        mock_response.text = "User-agent: *\nAllow: /"

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mocker.patch('httpx.AsyncClient', return_value=mock_client)

        allowed = await check_robots_txt("https://test.edu/lab")
        assert allowed is True

    @pytest.mark.asyncio
    async def test_disallowed_by_robots_txt(self, mocker):
        """Test URL disallowed by robots.txt."""
        # Mock httpx.AsyncClient.get
        mock_response = MagicMock()
        mock_response.text = "User-agent: *\nDisallow: /private/"

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mocker.patch('httpx.AsyncClient', return_value=mock_client)

        allowed = await check_robots_txt("https://test.edu/private/lab")
        assert allowed is False

    @pytest.mark.asyncio
    async def test_missing_robots_txt_assumes_allowed(self, mocker):
        """Test missing robots.txt assumes allowed."""
        # Mock httpx.AsyncClient.get to raise exception
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("404 Not Found"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mocker.patch('httpx.AsyncClient', return_value=mock_client)

        allowed = await check_robots_txt("https://test.edu/lab")
        assert allowed is True

    @pytest.mark.asyncio
    async def test_custom_user_agent(self, mocker):
        """Test custom user agent respected."""
        # Mock httpx.AsyncClient.get
        mock_response = MagicMock()
        mock_response.text = "User-agent: CustomBot\nDisallow: /\n\nUser-agent: *\nAllow: /"

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mocker.patch('httpx.AsyncClient', return_value=mock_client)

        allowed = await check_robots_txt("https://test.edu/lab", user_agent="CustomBot")
        assert allowed is False


class TestScrapingResultType:
    """Test ScrapingResult TypedDict."""

    def test_scraping_result_structure(self):
        """Test ScrapingResult has correct structure."""
        result: ScrapingResult = {
            "data": {"field1": "value1"},
            "sufficient": True,
            "missing_fields": [],
            "attempts": 1
        }

        assert "data" in result
        assert "sufficient" in result
        assert "missing_fields" in result
        assert "attempts" in result
        assert isinstance(result["data"], dict)
        assert isinstance(result["sufficient"], bool)
        assert isinstance(result["missing_fields"], list)
        assert isinstance(result["attempts"], int)
