"""Unit tests for MCP server configuration helper.

Tests the get_mcp_server_config() and validate_mcp_config() functions
that provide STDIO configuration for Claude Agent SDK.
"""

import os
from unittest.mock import patch


from src.utils.mcp_client import get_mcp_server_config, validate_mcp_config


class TestGetMCPServerConfig:
    """Test suite for get_mcp_server_config() function."""

    def test_returns_dict_with_correct_keys(self, monkeypatch):
        """Test that config dict contains 'papers' and 'linkedin' keys."""
        # Arrange
        monkeypatch.setenv("LINKEDIN_EMAIL", "test@example.com")
        monkeypatch.setenv("LINKEDIN_PASSWORD", "testpass123")

        # Act
        config = get_mcp_server_config()

        # Assert
        assert "papers" in config
        assert "linkedin" in config
        assert len(config) == 2

    def test_paper_search_mcp_config_structure(self, monkeypatch):
        """Test paper-search-mcp configuration has correct STDIO structure."""
        # Arrange
        import sys

        monkeypatch.setenv("LINKEDIN_EMAIL", "test@example.com")
        monkeypatch.setenv("LINKEDIN_PASSWORD", "testpass123")

        # Act
        config = get_mcp_server_config()

        # Assert
        papers_config = config["papers"]
        assert papers_config["type"] == "stdio"
        assert papers_config["command"] == sys.executable
        assert papers_config["args"] == ["-m", "paper_search_mcp.server"]
        assert papers_config["env"] is None

    def test_mcp_linkedin_config_structure(self, monkeypatch):
        """Test mcp-linkedin configuration has correct STDIO structure."""
        # Arrange
        test_email = "linkedin@example.com"
        test_password = "secure_password"
        monkeypatch.setenv("LINKEDIN_EMAIL", test_email)
        monkeypatch.setenv("LINKEDIN_PASSWORD", test_password)

        # Act
        config = get_mcp_server_config()

        # Assert
        linkedin_config = config["linkedin"]
        assert linkedin_config["type"] == "stdio"
        assert linkedin_config["command"] == "uvx"
        assert linkedin_config["args"] == [
            "--from",
            "git+https://github.com/adhikasp/mcp-linkedin",
            "mcp-linkedin",
        ]

    def test_linkedin_credentials_loaded_from_env(self, monkeypatch):
        """Test that LinkedIn credentials are loaded from environment variables."""
        # Arrange
        test_email = "user@linkedin.com"
        test_password = "mypassword123"
        monkeypatch.setenv("LINKEDIN_EMAIL", test_email)
        monkeypatch.setenv("LINKEDIN_PASSWORD", test_password)

        # Act
        config = get_mcp_server_config()

        # Assert
        linkedin_env = config["linkedin"]["env"]
        assert linkedin_env is not None
        assert linkedin_env["LINKEDIN_EMAIL"] == test_email
        assert linkedin_env["LINKEDIN_PASSWORD"] == test_password

    def test_missing_linkedin_credentials_returns_empty_strings(self, monkeypatch):
        """Test that missing credentials result in empty strings, not errors."""
        # Arrange
        monkeypatch.delenv("LINKEDIN_EMAIL", raising=False)
        monkeypatch.delenv("LINKEDIN_PASSWORD", raising=False)

        # Act
        config = get_mcp_server_config()

        # Assert
        linkedin_env = config["linkedin"]["env"]
        assert linkedin_env is not None
        assert linkedin_env["LINKEDIN_EMAIL"] == ""
        assert linkedin_env["LINKEDIN_PASSWORD"] == ""

    @patch.dict(os.environ, {}, clear=True)
    def test_config_generated_without_dotenv_file(self):
        """Test that config can be generated even without .env file."""
        # Act
        config = get_mcp_server_config()

        # Assert
        assert "papers" in config
        assert "linkedin" in config
        # Should have empty credentials but valid structure
        assert config["linkedin"]["env"]["LINKEDIN_EMAIL"] == ""
        assert config["linkedin"]["env"]["LINKEDIN_PASSWORD"] == ""


class TestValidateMCPConfig:
    """Test suite for validate_mcp_config() function."""

    def test_valid_config_returns_true(self, monkeypatch):
        """Test validation passes when all credentials are set."""
        # Arrange
        monkeypatch.setenv("LINKEDIN_EMAIL", "test@example.com")
        monkeypatch.setenv("LINKEDIN_PASSWORD", "testpass123")

        # Act
        is_valid, errors = validate_mcp_config()

        # Assert
        assert is_valid is True
        assert errors == []

    def test_missing_linkedin_email_returns_error(self, monkeypatch):
        """Test validation fails when LINKEDIN_EMAIL is missing."""
        # Arrange
        monkeypatch.delenv("LINKEDIN_EMAIL", raising=False)
        monkeypatch.setenv("LINKEDIN_PASSWORD", "testpass123")

        # Act
        is_valid, errors = validate_mcp_config()

        # Assert
        assert is_valid is False
        assert len(errors) == 1
        assert "LINKEDIN_EMAIL not set in .env file" in errors

    def test_missing_linkedin_password_returns_error(self, monkeypatch):
        """Test validation fails when LINKEDIN_PASSWORD is missing."""
        # Arrange
        monkeypatch.setenv("LINKEDIN_EMAIL", "test@example.com")
        monkeypatch.delenv("LINKEDIN_PASSWORD", raising=False)

        # Act
        is_valid, errors = validate_mcp_config()

        # Assert
        assert is_valid is False
        assert len(errors) == 1
        assert "LINKEDIN_PASSWORD not set in .env file" in errors

    def test_missing_all_credentials_returns_multiple_errors(self, monkeypatch):
        """Test validation returns all errors when multiple credentials missing."""
        # Arrange
        monkeypatch.delenv("LINKEDIN_EMAIL", raising=False)
        monkeypatch.delenv("LINKEDIN_PASSWORD", raising=False)

        # Act
        is_valid, errors = validate_mcp_config()

        # Assert
        assert is_valid is False
        assert len(errors) == 2
        assert "LINKEDIN_EMAIL not set in .env file" in errors
        assert "LINKEDIN_PASSWORD not set in .env file" in errors

    def test_empty_credentials_treated_as_missing(self, monkeypatch):
        """Test that empty string credentials are treated as missing."""
        # Arrange - set to empty strings
        monkeypatch.setenv("LINKEDIN_EMAIL", "")
        monkeypatch.setenv("LINKEDIN_PASSWORD", "")

        # Act
        is_valid, errors = validate_mcp_config()

        # Assert
        assert is_valid is False
        assert len(errors) == 2
