"""
Credential Manager Module
Handles secure credential storage and retrieval with CLI prompts.
"""

import os
from pathlib import Path
from typing import Dict, Optional

import structlog
from dotenv import load_dotenv, set_key
from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console()
logger = structlog.get_logger(__name__)


class CredentialManager:
    """Manages credentials with secure storage and CLI prompting."""

    def __init__(self, env_file: Path = Path(".env")):
        """
        Initialize credential manager.

        Args:
            env_file: Path to .env file for credential storage
        """
        self.env_file = env_file
        logger.info("credential_manager_initialized", env_file=str(env_file))
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Load existing credentials from .env file."""
        if self.env_file.exists():
            load_dotenv(self.env_file)
            logger.info("credentials_loaded_from_env", env_file=str(self.env_file))
            self._set_secure_permissions()
        else:
            # Create .env from .env.example if it doesn't exist
            example_file = Path(".env.example")
            if example_file.exists():
                console.print(
                    "[yellow][i] No .env file found. Creating from .env.example...[/yellow]"
                )
                logger.info("creating_env_from_example")
                self.env_file.write_text(example_file.read_text(encoding="utf-8"))
                self._set_secure_permissions()
            else:
                logger.warning("no_env_file_or_example_found")

    def _set_secure_permissions(self) -> None:
        """Set secure file permissions on .env file (Unix only)."""
        if os.name != "nt":  # Not Windows
            try:
                os.chmod(self.env_file, 0o600)  # rw------- (owner read/write only)
                logger.info(
                    "secure_permissions_set", env_file=str(self.env_file), mode="0600"
                )
            except Exception as e:
                console.print(
                    f"[yellow][!] Could not set secure permissions on .env: {e}[/yellow]"
                )
                logger.warning(
                    "failed_to_set_permissions",
                    env_file=str(self.env_file),
                    error=str(e),
                )
        else:
            logger.debug("skipping_permissions_windows", env_file=str(self.env_file))

    def get_credential(
        self,
        key: str,
        prompt_message: str,
        is_password: bool = False,
        required: bool = True,
    ) -> Optional[str]:
        """
        Get credential from environment or prompt user.

        Args:
            key: Environment variable name (e.g., "LINKEDIN_EMAIL")
            prompt_message: Message to display when prompting
            is_password: Whether to mask input (for passwords)
            required: Whether credential is required

        Returns:
            Credential value or None if optional and not provided

        Raises:
            ValueError: If required credential not provided
        """
        # Check if credential already exists
        value = os.getenv(key)
        if value:
            logger.debug("credential_found_in_env", key=key, is_password=is_password)
            return value

        # Prompt user for credential
        logger.info(
            "prompting_for_credential",
            key=key,
            is_password=is_password,
            required=required,
        )
        console.print(f"\n[yellow][*] Credential Required: {key}[/yellow]")
        console.print(f"   {prompt_message}\n")

        if is_password:
            value = Prompt.ask("   Enter value", password=True)
        else:
            value = Prompt.ask("   Enter value")

        if not value and required:
            logger.error("required_credential_not_provided", key=key)
            raise ValueError(f"Required credential not provided: {key}")

        if value:
            # Save to .env file
            self._save_credential(key, value)

        return value or None

    def _save_credential(self, key: str, value: str) -> None:
        """
        Save credential to .env file.

        Args:
            key: Environment variable name
            value: Credential value
        """
        try:
            set_key(self.env_file, key, value)
            os.environ[key] = value  # Update current environment
            console.print(f"   [green][+] Saved {key} to .env[/green]\n")
            logger.info("credential_saved", key=key, env_file=str(self.env_file))
        except Exception as e:
            console.print(f"   [red][X] Failed to save credential: {e}[/red]\n")
            logger.error("failed_to_save_credential", key=key, error=str(e))
            raise

    def check_required_credentials(
        self, require_linkedin: bool = False
    ) -> Dict[str, Optional[str]]:
        """
        Check for required credentials and prompt if missing.

        Args:
            require_linkedin: Whether LinkedIn credentials are required
                             (True for Epic 6, False for earlier epics)

        Returns:
            Dictionary of all credentials (values may be None if optional)

        Raises:
            ValueError: If required credentials are missing after prompting
        """
        logger.info("checking_credentials", require_linkedin=require_linkedin)
        console.print("\n[*] Checking credentials...\n")

        credentials = {}

        # LinkedIn credentials (required for Epic 6)
        if require_linkedin:
            credentials["LINKEDIN_EMAIL"] = self.get_credential(
                "LINKEDIN_EMAIL",
                "LinkedIn email address for profile matching (Epic 6)",
                is_password=False,
                required=True,
            )
            credentials["LINKEDIN_PASSWORD"] = self.get_credential(
                "LINKEDIN_PASSWORD",
                "LinkedIn password (stored securely in .env)",
                is_password=True,
                required=True,
            )
        else:
            console.print(
                "[dim][i] LinkedIn credentials not required for this epic[/dim]\n"
            )
            logger.debug("linkedin_credentials_not_required")

        # Optional university portal credentials
        needs_university_auth = Confirm.ask(
            "Does your target university require authentication for directory access?",
            default=False,
        )
        logger.info(
            "university_auth_requirement_checked", needs_auth=needs_university_auth
        )

        if needs_university_auth:
            credentials["UNIVERSITY_USERNAME"] = self.get_credential(
                "UNIVERSITY_USERNAME",
                "University portal username",
                is_password=False,
                required=True,
            )
            credentials["UNIVERSITY_PASSWORD"] = self.get_credential(
                "UNIVERSITY_PASSWORD",
                "University portal password",
                is_password=True,
                required=True,
            )

        console.print("[green][+] All required credentials present[/green]\n")
        logger.info("all_credentials_present", credential_count=len(credentials))
        return credentials

    def update_credentials(self) -> None:
        """Prompt user to update all credentials."""
        logger.info("updating_credentials")
        console.print("\n[*] Update Credentials\n")

        # LinkedIn
        if Confirm.ask("Update LinkedIn credentials?", default=False):
            logger.info("updating_linkedin_credentials")
            self.get_credential(
                "LINKEDIN_EMAIL", "New LinkedIn email", is_password=False, required=True
            )
            self.get_credential(
                "LINKEDIN_PASSWORD",
                "New LinkedIn password",
                is_password=True,
                required=True,
            )

        # University
        if Confirm.ask("Update university portal credentials?", default=False):
            logger.info("updating_university_credentials")
            self.get_credential(
                "UNIVERSITY_USERNAME",
                "New university username",
                is_password=False,
                required=False,
            )
            self.get_credential(
                "UNIVERSITY_PASSWORD",
                "New university password",
                is_password=True,
                required=False,
            )

        console.print("[green][+] Credentials updated[/green]\n")
        logger.info("credentials_update_complete")

    @staticmethod
    def mask_credential(value: str, show_chars: int = 3) -> str:
        """
        Mask credential for display in logs.

        Args:
            value: Credential value to mask
            show_chars: Number of characters to show at start

        Returns:
            Masked credential (e.g., "abc***")
        """
        if not value or len(value) <= show_chars:
            return "***"
        return f"{value[:show_chars]}{'*' * (len(value) - show_chars)}"
