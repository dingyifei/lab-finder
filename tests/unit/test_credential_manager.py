"""
Unit tests for Credential Manager Module
"""

import os

import pytest

from src.utils.credential_manager import CredentialManager


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables before each test."""
    # Remove any existing credential-related env vars
    for key in [
        "LINKEDIN_EMAIL",
        "LINKEDIN_PASSWORD",
        "UNIVERSITY_USERNAME",
        "UNIVERSITY_PASSWORD",
    ]:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def sample_env_file(tmp_path):
    """Create a sample .env file for testing."""
    env_file = tmp_path / ".env"
    env_content = """LINKEDIN_EMAIL=test@example.com
LINKEDIN_PASSWORD=test_password
LOG_LEVEL=INFO
"""
    env_file.write_text(env_content, encoding="utf-8")
    return env_file


@pytest.fixture
def example_file(tmp_path):
    """Create a .env.example file for testing."""
    example_file = tmp_path / ".env.example"
    example_content = """LINKEDIN_EMAIL=your-email@example.com
LINKEDIN_PASSWORD=your-password
LOG_LEVEL=INFO
"""
    example_file.write_text(example_content, encoding="utf-8")
    return example_file


class TestCredentialManagerInit:
    """Test CredentialManager initialization."""

    def test_init_with_existing_env_file(self, sample_env_file, clean_env):
        """Test initialization when .env file exists."""
        cred_manager = CredentialManager(env_file=sample_env_file)

        assert cred_manager.env_file == sample_env_file
        assert os.getenv("LINKEDIN_EMAIL") == "test@example.com"
        assert os.getenv("LINKEDIN_PASSWORD") == "test_password"

    def test_init_without_env_file(self, tmp_path, clean_env, monkeypatch):
        """Test initialization when .env file doesn't exist and no .env.example."""
        # Change to tmp_path directory to isolate from project .env.example
        monkeypatch.chdir(tmp_path)

        env_file = tmp_path / ".env"
        cred_manager = CredentialManager(env_file=env_file)

        assert cred_manager.env_file == env_file
        # Should not raise error
        # .env won't exist without .env.example
        assert not env_file.exists()

    def test_init_creates_env_from_example(
        self, tmp_path, example_file, clean_env, monkeypatch
    ):
        """Test that .env is created from .env.example if it doesn't exist."""
        # Change to tmp_path directory so .env.example can be found
        monkeypatch.chdir(tmp_path)

        env_file = tmp_path / ".env"
        cred_manager = CredentialManager(env_file=env_file)

        assert cred_manager.env_file == env_file
        assert env_file.exists()
        assert "LINKEDIN_EMAIL=your-email@example.com" in env_file.read_text()


class TestGetCredential:
    """Test get_credential method."""

    def test_get_existing_credential(self, sample_env_file, clean_env):
        """Test getting credential that already exists in environment."""
        cred_manager = CredentialManager(env_file=sample_env_file)

        result = cred_manager.get_credential(
            "LINKEDIN_EMAIL", "LinkedIn email", is_password=False, required=True
        )

        assert result == "test@example.com"

    def test_get_credential_prompts_when_missing(self, tmp_path, clean_env, mocker):
        """Test that credential prompts when missing."""
        env_file = tmp_path / ".env"
        env_file.touch()  # Create empty .env
        cred_manager = CredentialManager(env_file=env_file)

        # Mock user input
        mocker.patch("rich.prompt.Prompt.ask", return_value="new@example.com")

        result = cred_manager.get_credential(
            "NEW_CREDENTIAL", "New credential", is_password=False, required=True
        )

        assert result == "new@example.com"
        # Note: set_key adds quotes around values
        env_content = env_file.read_text()
        assert "NEW_CREDENTIAL" in env_content
        assert "new@example.com" in env_content

    def test_get_password_credential_masked(self, tmp_path, clean_env, mocker):
        """Test that password credential is prompted with masking."""
        env_file = tmp_path / ".env"
        env_file.touch()
        cred_manager = CredentialManager(env_file=env_file)

        # Mock password input
        mock_ask = mocker.patch(
            "rich.prompt.Prompt.ask", return_value="secret_password"
        )

        result = cred_manager.get_credential(
            "NEW_PASSWORD", "New password", is_password=True, required=True
        )

        assert result == "secret_password"
        # Verify password=True was passed to Prompt.ask
        mock_ask.assert_called_once_with("   Enter value", password=True)

    def test_required_credential_not_provided_raises_error(
        self, tmp_path, clean_env, mocker
    ):
        """Test that missing required credential raises ValueError."""
        env_file = tmp_path / ".env"
        env_file.touch()
        cred_manager = CredentialManager(env_file=env_file)

        # Mock empty user input
        mocker.patch("rich.prompt.Prompt.ask", return_value="")

        with pytest.raises(ValueError) as exc_info:
            cred_manager.get_credential(
                "REQUIRED_CRED", "Required credential", is_password=False, required=True
            )

        assert "Required credential not provided: REQUIRED_CRED" in str(exc_info.value)

    def test_optional_credential_not_provided_returns_none(
        self, tmp_path, clean_env, mocker
    ):
        """Test that optional credential returns None when not provided."""
        env_file = tmp_path / ".env"
        env_file.touch()
        cred_manager = CredentialManager(env_file=env_file)

        # Mock empty user input
        mocker.patch("rich.prompt.Prompt.ask", return_value="")

        result = cred_manager.get_credential(
            "OPTIONAL_CRED", "Optional credential", is_password=False, required=False
        )

        assert result is None


class TestCheckRequiredCredentials:
    """Test check_required_credentials method."""

    def test_check_credentials_linkedin_required(self, tmp_path, clean_env, mocker):
        """Test checking credentials when LinkedIn is required."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "LINKEDIN_EMAIL=test@example.com\nLINKEDIN_PASSWORD=test_pass",
            encoding="utf-8",
        )
        cred_manager = CredentialManager(env_file=env_file)

        # Mock university auth confirmation
        mocker.patch("rich.prompt.Confirm.ask", return_value=False)

        credentials = cred_manager.check_required_credentials(require_linkedin=True)

        assert "LINKEDIN_EMAIL" in credentials
        assert credentials["LINKEDIN_EMAIL"] == "test@example.com"
        assert "LINKEDIN_PASSWORD" in credentials
        assert credentials["LINKEDIN_PASSWORD"] == "test_pass"

    def test_check_credentials_linkedin_not_required(self, tmp_path, clean_env, mocker):
        """Test checking credentials when LinkedIn is not required."""
        env_file = tmp_path / ".env"
        env_file.touch()
        cred_manager = CredentialManager(env_file=env_file)

        # Mock university auth confirmation
        mocker.patch("rich.prompt.Confirm.ask", return_value=False)

        credentials = cred_manager.check_required_credentials(require_linkedin=False)

        assert "LINKEDIN_EMAIL" not in credentials
        assert "LINKEDIN_PASSWORD" not in credentials

    def test_check_credentials_with_university_auth(self, tmp_path, clean_env, mocker):
        """Test checking credentials when university authentication is needed."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "UNIVERSITY_USERNAME=testuser\nUNIVERSITY_PASSWORD=testpass",
            encoding="utf-8",
        )
        cred_manager = CredentialManager(env_file=env_file)

        # Mock confirming university auth is needed
        mocker.patch("rich.prompt.Confirm.ask", return_value=True)

        credentials = cred_manager.check_required_credentials(require_linkedin=False)

        assert "UNIVERSITY_USERNAME" in credentials
        assert credentials["UNIVERSITY_USERNAME"] == "testuser"
        assert "UNIVERSITY_PASSWORD" in credentials
        assert credentials["UNIVERSITY_PASSWORD"] == "testpass"


class TestUpdateCredentials:
    """Test update_credentials method."""

    def test_update_linkedin_credentials(self, tmp_path, clean_env, mocker):
        """Test updating LinkedIn credentials."""
        env_file = tmp_path / ".env"
        env_file.touch()
        cred_manager = CredentialManager(env_file=env_file)

        # Mock confirmations and inputs
        mocker.patch(
            "rich.prompt.Confirm.ask", side_effect=[True, False]
        )  # Update LinkedIn, not university
        mocker.patch(
            "rich.prompt.Prompt.ask", side_effect=["new@example.com", "new_password"]
        )

        cred_manager.update_credentials()

        env_content = env_file.read_text()
        # Note: set_key adds quotes around values
        assert "LINKEDIN_EMAIL" in env_content
        assert "new@example.com" in env_content
        assert "LINKEDIN_PASSWORD" in env_content
        assert "new_password" in env_content

    def test_update_university_credentials(self, tmp_path, clean_env, mocker):
        """Test updating university credentials."""
        env_file = tmp_path / ".env"
        env_file.touch()
        cred_manager = CredentialManager(env_file=env_file)

        # Mock confirmations and inputs
        mocker.patch(
            "rich.prompt.Confirm.ask", side_effect=[False, True]
        )  # Not LinkedIn, update university
        mocker.patch("rich.prompt.Prompt.ask", side_effect=["newuser", "newpass"])

        cred_manager.update_credentials()

        env_content = env_file.read_text()
        # Note: set_key adds quotes around values
        assert "UNIVERSITY_USERNAME" in env_content
        assert "newuser" in env_content
        assert "UNIVERSITY_PASSWORD" in env_content
        assert "newpass" in env_content

    def test_update_no_credentials(self, tmp_path, clean_env, mocker):
        """Test update when user doesn't want to update anything."""
        env_file = tmp_path / ".env"
        env_file.touch()
        cred_manager = CredentialManager(env_file=env_file)

        # Mock user declining all updates
        mocker.patch("rich.prompt.Confirm.ask", side_effect=[False, False])

        # Should not raise error
        cred_manager.update_credentials()


class TestMaskCredential:
    """Test mask_credential static method."""

    def test_mask_credential_normal_string(self):
        """Test masking a normal credential string."""
        result = CredentialManager.mask_credential("password123", show_chars=3)
        assert result == "pas********"

    def test_mask_credential_short_string(self):
        """Test masking a very short string."""
        result = CredentialManager.mask_credential("abc", show_chars=3)
        assert result == "***"

    def test_mask_credential_empty_string(self):
        """Test masking an empty string."""
        result = CredentialManager.mask_credential("", show_chars=3)
        assert result == "***"

    def test_mask_credential_custom_show_chars(self):
        """Test masking with custom number of visible characters."""
        result = CredentialManager.mask_credential("secretpassword", show_chars=5)
        assert result == "secre*********"

    def test_mask_credential_length_calculation(self):
        """Test that mask length is correct."""
        credential = "test@example.com"
        result = CredentialManager.mask_credential(credential, show_chars=4)
        assert result == "test************"
        assert len(result) == len(credential)


class TestFilePermissions:
    """Test file permission setting (Unix only)."""

    @pytest.mark.skipif(
        os.name == "nt", reason="File permissions not applicable on Windows"
    )
    def test_secure_permissions_set_on_unix(self, tmp_path, clean_env):
        """Test that .env file gets 600 permissions on Unix."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST=value", encoding="utf-8")

        cred_manager = CredentialManager(env_file=env_file)

        # Check file permissions (should be 0o600 = -rw-------)
        assert cred_manager.env_file == env_file
        stat_info = env_file.stat()
        permissions = stat_info.st_mode & 0o777
        assert permissions == 0o600

    def test_windows_permissions_skipped(self, tmp_path, clean_env, monkeypatch):
        """Test that permission setting is skipped on Windows."""
        monkeypatch.setattr(os, "name", "nt")

        env_file = tmp_path / ".env"
        env_file.write_text("TEST=value", encoding="utf-8")

        # Should not raise error on Windows
        cred_manager = CredentialManager(env_file=env_file)
        assert cred_manager.env_file == env_file


class TestSaveCredential:
    """Test _save_credential private method."""

    def test_save_credential_creates_or_updates_env(self, tmp_path, clean_env):
        """Test that saving credential creates/updates .env file."""
        env_file = tmp_path / ".env"
        env_file.touch()
        cred_manager = CredentialManager(env_file=env_file)

        cred_manager._save_credential("TEST_KEY", "test_value")

        assert env_file.exists()
        env_content = env_file.read_text()
        # Note: set_key adds quotes around values
        assert "TEST_KEY" in env_content
        assert "test_value" in env_content
        assert os.getenv("TEST_KEY") == "test_value"

    def test_save_credential_updates_environment(self, tmp_path, clean_env):
        """Test that saving credential updates current environment."""
        env_file = tmp_path / ".env"
        env_file.touch()
        cred_manager = CredentialManager(env_file=env_file)

        cred_manager._save_credential("ENV_VAR", "env_value")

        assert os.getenv("ENV_VAR") == "env_value"
