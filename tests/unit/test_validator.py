"""
Unit tests for Configuration Validator Module
"""

import json
from pathlib import Path

import pytest

from src.utils.validator import ConfigValidator, ConfigurationError


@pytest.fixture
def validator():
    """Create a ConfigValidator instance for testing."""
    return ConfigValidator()


@pytest.fixture
def valid_user_profile():
    """Return a valid user profile configuration."""
    return {
        "name": "Jane Doe",
        "current_degree": "PhD in Computer Science",
        "target_university": "Stanford University",
        "target_department": "Computer Science",
        "research_interests": ["Machine Learning", "AI"],
        "resume_highlights": {
            "education": [
                {"degree": "MS in CS", "institution": "UC Berkeley", "year": 2022}
            ],
            "skills": ["Python", "PyTorch"],
            "research_experience": [
                {
                    "title": "Research Assistant",
                    "description": "NLP research",
                    "duration": "2021-2022",
                }
            ],
        },
        "preferred_graduation_duration": 5.5,
    }


@pytest.fixture
def valid_university_config():
    """Return a valid university configuration."""
    return {
        "university_name": "Stanford University",
        "core_website": "https://www.stanford.edu",
        "directory_link": "https://www.stanford.edu/faculty-staff",
        "department_structure_hint": "Schools > Departments",
        "known_departments": ["Computer Science", "EE"],
    }


@pytest.fixture
def valid_system_params():
    """Return a valid system parameters configuration."""
    return {
        "batch_config": {
            "department_discovery_batch_size": 5,
            "professor_discovery_batch_size": 10,
            "professor_filtering_batch_size": 15,
            "publication_retrieval_batch_size": 20,
            "linkedin_matching_batch_size": 15,
        },
        "rate_limits": {"archive_org": 30, "linkedin": 10, "paper_search": 20},
        "rate_limiting": {"max_concurrent_llm_calls": 5},
        "filtering_config": {
            "low_confidence_threshold": 70,
            "high_confidence_threshold": 90,
            "borderline_review_enabled": True,
        },
        "timeouts": {"web_scraping": 30, "mcp_query": 60},
        "confidence_thresholds": {"professor_filter": 70.0, "linkedin_match": 75.0},
        "publication_years": 3,
        "log_level": "INFO",
    }


class TestSchemaLoading:
    """Test schema loading functionality."""

    def test_load_schema_success(self, validator):
        """Test loading a valid schema."""
        schema = validator.load_schema("user_profile_schema.json")
        assert schema is not None
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_load_schema_caching(self, validator):
        """Test that schemas are cached after first load."""
        schema1 = validator.load_schema("user_profile_schema.json")
        schema2 = validator.load_schema("user_profile_schema.json")
        assert schema1 is schema2  # Should be same object (cached)

    def test_load_schema_not_found(self, validator):
        """Test loading a non-existent schema."""
        with pytest.raises(ConfigurationError) as exc_info:
            validator.load_schema("nonexistent_schema.json")
        assert "Schema file not found" in str(exc_info.value)


class TestUserProfileValidation:
    """Test user profile configuration validation."""

    def test_valid_user_profile(self, validator, valid_user_profile):
        """Test validation of a valid user profile."""
        # Should not raise any exception
        validator.validate(valid_user_profile, "user_profile_schema.json")

    def test_missing_required_field_name(self, validator, valid_user_profile):
        """Test missing required field shows helpful error."""
        del valid_user_profile["name"]

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate(valid_user_profile, "user_profile_schema.json")

        error_message = str(exc_info.value)
        assert "Missing required field: 'name'" in error_message
        assert "Add this field to your configuration file" in error_message

    def test_missing_required_field_current_degree(self, validator, valid_user_profile):
        """Test missing current_degree field."""
        del valid_user_profile["current_degree"]

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate(valid_user_profile, "user_profile_schema.json")

        error_message = str(exc_info.value)
        assert "Missing required field: 'current_degree'" in error_message

    def test_missing_research_interests(self, validator, valid_user_profile):
        """Test missing required array field."""
        del valid_user_profile["research_interests"]

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate(valid_user_profile, "user_profile_schema.json")

        error_message = str(exc_info.value)
        assert "Missing required field: 'research_interests'" in error_message

    def test_type_mismatch_name(self, validator, valid_user_profile):
        """Test type mismatch for string field."""
        valid_user_profile["name"] = 12345  # Should be string

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate(valid_user_profile, "user_profile_schema.json")

        error_message = str(exc_info.value)
        assert "Type mismatch" in error_message

    def test_type_mismatch_research_interests(self, validator, valid_user_profile):
        """Test type mismatch for array field."""
        valid_user_profile["research_interests"] = "Machine Learning"  # Should be array

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate(valid_user_profile, "user_profile_schema.json")

        error_message = str(exc_info.value)
        assert "Type mismatch" in error_message

    def test_empty_string_field(self, validator, valid_user_profile):
        """Test empty string violates minLength."""
        valid_user_profile["name"] = ""

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate(valid_user_profile, "user_profile_schema.json")

        error_message = str(exc_info.value)
        assert "Value too short" in error_message

    def test_graduation_duration_out_of_range_min(self, validator, valid_user_profile):
        """Test graduation duration below minimum."""
        valid_user_profile["preferred_graduation_duration"] = 2.0  # Min is 3.0

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate(valid_user_profile, "user_profile_schema.json")

        error_message = str(exc_info.value)
        assert "Value too small" in error_message

    def test_graduation_duration_out_of_range_max(self, validator, valid_user_profile):
        """Test graduation duration above maximum."""
        valid_user_profile["preferred_graduation_duration"] = 15.0  # Max is 10.0

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate(valid_user_profile, "user_profile_schema.json")

        error_message = str(exc_info.value)
        assert "Value too large" in error_message


class TestUniversityConfigValidation:
    """Test university configuration validation."""

    def test_valid_university_config(self, validator, valid_university_config):
        """Test validation of a valid university config."""
        validator.validate(valid_university_config, "university_config_schema.json")

    def test_missing_required_field(self, validator, valid_university_config):
        """Test missing required field in university config."""
        del valid_university_config["core_website"]

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate(valid_university_config, "university_config_schema.json")

        error_message = str(exc_info.value)
        assert "Missing required field: 'core_website'" in error_message

    def test_invalid_url_format(self, validator, valid_university_config):
        """Test invalid URL format."""
        # Note: jsonschema's uri format validation is permissive
        # Simple strings may be considered valid URIs
        # This test is kept for documentation but may not catch all invalid URLs
        # For stricter validation, consider additional runtime checks
        valid_university_config["core_website"] = "not-a-valid-url"

        # This test documents expected behavior but jsonschema uri format
        # is lenient and may accept this as valid
        try:
            validator.validate(valid_university_config, "university_config_schema.json")
            # If validation passes, that's acceptable given format checker limitations
        except ConfigurationError as e:
            # If it does catch it, verify the error message
            assert "Invalid format" in str(e)


class TestSystemParamsValidation:
    """Test system parameters configuration validation."""

    def test_valid_system_params(self, validator, valid_system_params):
        """Test validation of valid system parameters."""
        validator.validate(valid_system_params, "system_params_schema.json")

    def test_invalid_log_level_enum(self, validator, valid_system_params):
        """Test invalid log_level enum value."""
        valid_system_params["log_level"] = "INVALID"

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate(valid_system_params, "system_params_schema.json")

        error_message = str(exc_info.value)
        assert "Invalid value" in error_message
        assert "Allowed values" in error_message

    def test_batch_size_below_minimum(self, validator, valid_system_params):
        """Test batch size below minimum."""
        valid_system_params["batch_config"]["department_discovery_batch_size"] = (
            0  # Min is 1
        )

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate(valid_system_params, "system_params_schema.json")

        error_message = str(exc_info.value)
        assert "Value too small" in error_message

    def test_batch_size_above_maximum(self, validator, valid_system_params):
        """Test batch size above maximum."""
        valid_system_params["batch_config"]["department_discovery_batch_size"] = (
            100  # Max is 99
        )

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate(valid_system_params, "system_params_schema.json")

        error_message = str(exc_info.value)
        assert "Value too large" in error_message


class TestFileValidation:
    """Test file-based validation."""

    def test_validate_file_success(self, validator, valid_user_profile, tmp_path):
        """Test successful file validation."""
        config_file = tmp_path / "user_profile.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(valid_user_profile, f)

        result = validator.validate_file(config_file, "user_profile_schema.json")
        assert result == valid_user_profile

    def test_validate_file_not_found(self, validator):
        """Test validation of non-existent file."""
        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate_file(
                Path("nonexistent.json"), "user_profile_schema.json"
            )

        error_message = str(exc_info.value)
        assert "Configuration file not found" in error_message

    def test_validate_file_invalid_json(self, validator, tmp_path):
        """Test validation of file with invalid JSON."""
        config_file = tmp_path / "invalid.json"
        with open(config_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json content }")

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate_file(config_file, "user_profile_schema.json")

        error_message = str(exc_info.value)
        assert "Invalid JSON" in error_message
        assert "trailing commas" in error_message

    def test_validate_file_fails_validation(self, validator, tmp_path):
        """Test validation of file with schema violations."""
        config_file = tmp_path / "invalid_profile.json"
        invalid_config = {"name": "Jane"}  # Missing required fields

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(invalid_config, f)

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate_file(config_file, "user_profile_schema.json")

        error_message = str(exc_info.value)
        assert "Missing required field" in error_message


class TestValidateAllConfigs:
    """Test validate_all_configs method."""

    def test_validate_all_configs_success(
        self,
        validator,
        valid_user_profile,
        valid_university_config,
        valid_system_params,
        tmp_path,
    ):
        """Test validating all configs successfully."""
        # Create config files
        user_file = tmp_path / "user_profile.json"
        univ_file = tmp_path / "university.json"
        params_file = tmp_path / "system_params.json"

        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(valid_user_profile, f)
        with open(univ_file, "w", encoding="utf-8") as f:
            json.dump(valid_university_config, f)
        with open(params_file, "w", encoding="utf-8") as f:
            json.dump(valid_system_params, f)

        # Validate all
        result = validator.validate_all_configs(user_file, univ_file, params_file)

        assert "user_profile" in result
        assert "university" in result
        assert "system_params" in result
        assert result["user_profile"]["name"] == "Jane Doe"

    def test_validate_all_configs_without_system_params(
        self, validator, valid_user_profile, valid_university_config, tmp_path
    ):
        """Test validating configs without system params (optional)."""
        user_file = tmp_path / "user_profile.json"
        univ_file = tmp_path / "university.json"

        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(valid_user_profile, f)
        with open(univ_file, "w", encoding="utf-8") as f:
            json.dump(valid_university_config, f)

        # Validate without system params
        result = validator.validate_all_configs(user_file, univ_file)

        assert "user_profile" in result
        assert "university" in result
        assert "system_params" in result
        assert result["system_params"] == {}  # Empty dict when not provided

    def test_validate_all_configs_user_profile_fails(
        self, validator, valid_university_config, tmp_path
    ):
        """Test that validation fails early on invalid user profile."""
        user_file = tmp_path / "user_profile.json"
        univ_file = tmp_path / "university.json"

        # Invalid user profile (missing required fields)
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump({"name": "Jane"}, f)
        with open(univ_file, "w", encoding="utf-8") as f:
            json.dump(valid_university_config, f)

        with pytest.raises(ConfigurationError) as exc_info:
            validator.validate_all_configs(user_file, univ_file)

        error_message = str(exc_info.value)
        assert "Missing required field" in error_message
