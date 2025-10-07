"""
Configuration Validator Module
Validates JSON configuration files against schemas.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from jsonschema import Draft7Validator, FormatChecker, ValidationError
from rich.console import Console

console = Console()
logger = structlog.get_logger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""

    pass


class ConfigValidator:
    """Validates configuration files against JSON schemas."""

    def __init__(self, schema_dir: Path = Path("src/schemas")):
        """
        Initialize validator with schema directory.

        Args:
            schema_dir: Path to directory containing JSON schemas
        """
        self.schema_dir = schema_dir
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def load_schema(self, schema_name: str) -> Dict[str, Any]:
        """
        Load JSON schema from file.

        Args:
            schema_name: Schema filename (e.g., "user_profile_schema.json")

        Returns:
            Loaded schema dictionary

        Raises:
            ConfigurationError: If schema file not found or invalid
        """
        if schema_name in self._schemas:
            logger.debug("schema_loaded_from_cache", schema_name=schema_name)
            return self._schemas[schema_name]

        schema_path = self.schema_dir / schema_name
        if not schema_path.exists():
            logger.error(
                "schema_not_found",
                schema_name=schema_name,
                schema_path=str(schema_path),
            )
            raise ConfigurationError(f"Schema file not found: {schema_path}")

        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            self._schemas[schema_name] = schema
            logger.info(
                "schema_loaded", schema_name=schema_name, schema_path=str(schema_path)
            )
            return schema
        except json.JSONDecodeError as e:
            logger.error("schema_invalid_json", schema_name=schema_name, error=str(e))
            raise ConfigurationError(f"Invalid JSON in schema {schema_name}: {e}")

    def validate(self, config: Dict[str, Any], schema_name: str) -> None:
        """
        Validate configuration against schema.

        Args:
            config: Configuration dictionary to validate
            schema_name: Schema filename to validate against

        Raises:
            ConfigurationError: If validation fails with detailed error messages
        """
        logger.debug("validating_config", schema_name=schema_name)
        schema = self.load_schema(schema_name)
        validator = Draft7Validator(schema, format_checker=FormatChecker())

        errors = list(validator.iter_errors(config))
        if not errors:
            logger.info("validation_passed", schema_name=schema_name)
            return

        # Format error messages
        logger.warning(
            "validation_failed", schema_name=schema_name, error_count=len(errors)
        )
        error_messages = self._format_validation_errors(errors, schema_name)
        raise ConfigurationError("\n".join(error_messages))

    def validate_file(self, config_path: Path, schema_name: str) -> Dict[str, Any]:
        """
        Load and validate configuration file.

        Args:
            config_path: Path to configuration JSON file
            schema_name: Schema filename to validate against

        Returns:
            Validated configuration dictionary

        Raises:
            ConfigurationError: If file not found or validation fails
        """
        logger.debug(
            "validating_file", config_path=str(config_path), schema_name=schema_name
        )

        if not config_path.exists():
            logger.error("config_file_not_found", config_path=str(config_path))
            raise ConfigurationError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(
                "config_invalid_json", config_path=str(config_path), error=str(e)
            )
            raise ConfigurationError(
                f"Invalid JSON in {config_path.name}: {e}\n"
                f"Check for trailing commas, missing quotes, or invalid syntax."
            )

        self.validate(config, schema_name)
        logger.info(
            "file_validation_complete",
            config_path=str(config_path),
            schema_name=schema_name,
        )
        return config

    def _format_validation_errors(
        self, errors: List[ValidationError], schema_name: str
    ) -> List[str]:
        """
        Format validation errors into user-friendly messages.

        Args:
            errors: List of validation errors from jsonschema
            schema_name: Schema name for context

        Returns:
            List of formatted error messages
        """
        messages = [f"\n[X] Configuration validation failed for {schema_name}:\n"]

        for error in errors:
            # Build path to error location
            path = " -> ".join([str(p) for p in error.absolute_path]) or "(root)"

            # Format specific error types
            if error.validator == "required":
                missing_field = error.message.split("'")[1]
                messages.append(
                    f"  * Missing required field: '{missing_field}' at {path}\n"
                    f"    -> Add this field to your configuration file"
                )
            elif error.validator == "type":
                messages.append(
                    f"  * Type mismatch at '{path}': {error.message}\n"
                    f"    -> Expected type: {error.validator_value}"
                )
            elif error.validator == "minLength":
                messages.append(f"  * Value too short at '{path}': {error.message}")
            elif error.validator == "format":
                messages.append(
                    f"  * Invalid format at '{path}': {error.message}\n"
                    f"    -> Expected format: {error.validator_value} (e.g., valid URL)"
                )
            elif error.validator == "minimum":
                messages.append(f"  * Value too small at '{path}': {error.message}")
            elif error.validator == "maximum":
                messages.append(f"  * Value too large at '{path}': {error.message}")
            elif error.validator == "enum":
                messages.append(
                    f"  * Invalid value at '{path}': {error.message}\n"
                    f"    -> Allowed values: {error.validator_value}"
                )
            else:
                messages.append(f"  * Validation error at '{path}': {error.message}")

        messages.append("\n[!] Fix the errors above and try again.\n")
        return messages

    def validate_all_configs(
        self,
        user_profile_path: Path,
        university_config_path: Path,
        system_params_path: Optional[Path] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Validate all required configuration files.

        Args:
            user_profile_path: Path to user profile JSON
            university_config_path: Path to university config JSON
            system_params_path: Optional path to system parameters JSON

        Returns:
            Dictionary with validated configs: {"user_profile": {...}, "university": {...}, "system_params": {...}}

        Raises:
            ConfigurationError: If any validation fails
        """
        console.print("\n[*] Validating configuration files...\n")

        configs = {}

        # Validate user profile
        console.print("  Validating user profile...")
        configs["user_profile"] = self.validate_file(
            user_profile_path, "user_profile_schema.json"
        )
        console.print("  [+] User profile valid\n")

        # Validate university config
        console.print("  Validating university configuration...")
        configs["university"] = self.validate_file(
            university_config_path, "university_config_schema.json"
        )
        console.print("  [+] University configuration valid\n")

        # Validate system parameters (optional, use defaults if not provided)
        if system_params_path and system_params_path.exists():
            console.print("  Validating system parameters...")
            configs["system_params"] = self.validate_file(
                system_params_path, "system_params_schema.json"
            )
            console.print("  [+] System parameters valid\n")
        else:
            console.print("  [i] No system parameters file provided, using defaults\n")
            configs["system_params"] = {}

        console.print("[+] All configuration files validated successfully!\n")
        return configs
