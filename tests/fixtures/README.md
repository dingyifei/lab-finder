# Test Fixtures

This directory contains test data fixtures used across the test suite.

## Available Fixtures

### Configuration Fixtures

#### Valid Configurations
- **`sample_user_profile.json`** - Valid user profile configuration following the schema in `src/schemas/user_profile_schema.json`
- **`sample_university_config.json`** - Valid university configuration following the schema in `src/schemas/university_config_schema.json`

#### Invalid Configurations (for validation testing)
- **`invalid_user_profile.json`** - Invalid user profile (empty name, missing required fields, empty research_interests array)
- **`invalid_university_config.json`** - Invalid university config (malformed URLs)

## Usage in Tests

### Loading JSON Fixtures

```python
import json
from pathlib import Path

# Load valid fixture
def test_with_fixture():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_user_profile.json"
    with open(fixture_path, 'r') as f:
        config = json.load(f)

    assert config["name"] == "Alice Johnson"
```

### Using with pytest Fixtures

```python
import pytest
import json
from pathlib import Path

@pytest.fixture
def sample_user_profile():
    """Load sample user profile fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_user_profile.json"
    with open(fixture_path, 'r') as f:
        return json.load(f)

def test_user_profile_validation(sample_user_profile):
    # Use the loaded fixture
    assert "research_interests" in sample_user_profile
```

### Testing Validation Logic

```python
def test_invalid_config_rejected():
    """Test that invalid configs are properly rejected."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "invalid_user_profile.json"
    with open(fixture_path, 'r') as f:
        invalid_config = json.load(f)

    # Verify validator rejects invalid config
    with pytest.raises(ValidationError):
        validate_user_profile(invalid_config)
```

## Adding New Fixtures

When adding new test fixtures:

1. Create the fixture file in this directory
2. Document it in this README
3. Follow naming convention: `sample_*.json` for valid, `invalid_*.json` for invalid
4. Ensure fixtures match the corresponding JSON schema in `src/schemas/`
