"""
Unit tests for prompt_loader module.
"""

import pytest
from pathlib import Path
from jinja2 import TemplateNotFound, TemplateSyntaxError, UndefinedError

from src.utils.prompt_loader import (
    PromptLoader,
    render_prompt,
    get_default_loader,
)


class TestPromptLoader:
    """Test cases for PromptLoader class."""

    def test_initialization_with_default_path(self):
        """Test that PromptLoader initializes with default template directory."""
        # Act
        loader = PromptLoader()

        # Assert
        assert loader.template_dir.name == "prompts"
        assert loader.template_dir.exists()

    def test_initialization_with_custom_path(self, tmp_path):
        """Test that PromptLoader initializes with custom template directory."""
        # Arrange
        custom_dir = tmp_path / "custom_prompts"
        custom_dir.mkdir()

        # Act
        loader = PromptLoader(template_dir=custom_dir)

        # Assert
        assert loader.template_dir == custom_dir

    def test_render_simple_template(self, tmp_path):
        """Test rendering a simple template with variables."""
        # Arrange
        template_dir = tmp_path / "prompts"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("Hello {{ name }}!")

        loader = PromptLoader(template_dir=template_dir)

        # Act
        result = loader.render("test.j2", name="World")

        # Assert
        assert result == "Hello World!"

    def test_render_with_multiple_variables(self, tmp_path):
        """Test rendering template with multiple variables."""
        # Arrange
        template_dir = tmp_path / "prompts"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("{{ greeting }} {{ name }}! You are {{ age }} years old.")

        loader = PromptLoader(template_dir=template_dir)

        # Act
        result = loader.render("test.j2", greeting="Hello", name="Alice", age=30)

        # Assert
        assert result == "Hello Alice! You are 30 years old."

    def test_render_template_not_found(self, tmp_path):
        """Test that TemplateNotFound is raised for missing template."""
        # Arrange
        template_dir = tmp_path / "prompts"
        template_dir.mkdir()
        loader = PromptLoader(template_dir=template_dir)

        # Act & Assert
        with pytest.raises(TemplateNotFound):
            loader.render("nonexistent.j2")

    def test_render_with_undefined_variable_non_strict(self, tmp_path):
        """Test rendering with undefined variable (non-strict mode)."""
        # Arrange
        template_dir = tmp_path / "prompts"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("Hello {{ name }}!")

        loader = PromptLoader(template_dir=template_dir, strict_undefined=False)

        # Act
        result = loader.render("test.j2")  # name not provided

        # Assert
        # In non-strict mode, undefined variables render as empty string
        assert result == "Hello !"

    def test_render_with_correlation_id(self, tmp_path):
        """Test rendering with correlation ID for logging."""
        # Arrange
        template_dir = tmp_path / "prompts"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("Test")

        loader = PromptLoader(template_dir=template_dir)

        # Act
        result = loader.render("test.j2", correlation_id="test-123")

        # Assert
        assert result == "Test"

    def test_render_with_conditional(self, tmp_path):
        """Test rendering template with Jinja2 conditional."""
        # Arrange
        template_dir = tmp_path / "prompts"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("{% if enabled %}Enabled{% else %}Disabled{% endif %}")

        loader = PromptLoader(template_dir=template_dir)

        # Act
        result_enabled = loader.render("test.j2", enabled=True)
        result_disabled = loader.render("test.j2", enabled=False)

        # Assert
        assert result_enabled == "Enabled"
        assert result_disabled == "Disabled"

    def test_render_with_loop(self, tmp_path):
        """Test rendering template with Jinja2 loop."""
        # Arrange
        template_dir = tmp_path / "prompts"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text(
            "{% for item in items %}{{ item }}\n{% endfor %}"
        )

        loader = PromptLoader(template_dir=template_dir)

        # Act
        result = loader.render("test.j2", items=["apple", "banana", "cherry"])

        # Assert
        assert "apple" in result
        assert "banana" in result
        assert "cherry" in result

    def test_strip_markdown_filter(self, tmp_path):
        """Test custom strip_markdown filter."""
        # Arrange
        template_dir = tmp_path / "prompts"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("{{ text | strip_markdown }}")

        loader = PromptLoader(template_dir=template_dir)

        # Act
        result = loader.render("test.j2", text="**bold** and `code`")

        # Assert
        assert result == "bold and code"

    def test_get_system_prompt(self, tmp_path):
        """Test get_system_prompt convenience method."""
        # Arrange
        template_dir = tmp_path / "prompts"
        template_dir.mkdir()
        base_dir = template_dir / "base"
        base_dir.mkdir()
        template_file = base_dir / "analysis.j2"
        template_file.write_text("System: {{ instruction }}")

        loader = PromptLoader(template_dir=template_dir)

        # Act
        result = loader.get_system_prompt("analysis", instruction="Analyze text")

        # Assert
        assert result == "System: Analyze text"

    def test_nested_directory_template(self, tmp_path):
        """Test rendering template from nested directory."""
        # Arrange
        template_dir = tmp_path / "prompts"
        template_dir.mkdir()
        nested_dir = template_dir / "professor"
        nested_dir.mkdir()
        template_file = nested_dir / "filter.j2"
        template_file.write_text("Professor: {{ name }}")

        loader = PromptLoader(template_dir=template_dir)

        # Act
        result = loader.render("professor/filter.j2", name="Dr. Smith")

        # Assert
        assert result == "Professor: Dr. Smith"

    def test_trim_blocks_and_lstrip_blocks(self, tmp_path):
        """Test that trim_blocks and lstrip_blocks work correctly."""
        # Arrange
        template_dir = tmp_path / "prompts"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text(
            "Start\n{% if true %}\n  Content\n{% endif %}\nEnd"
        )

        loader = PromptLoader(template_dir=template_dir)

        # Act
        result = loader.render("test.j2")

        # Assert
        # trim_blocks removes first newline after tag, lstrip_blocks strips leading whitespace
        assert "Start" in result
        assert "Content" in result
        assert "End" in result


class TestRenderPromptFunction:
    """Test cases for render_prompt convenience function."""

    def test_render_prompt_uses_default_loader(self, tmp_path, monkeypatch):
        """Test that render_prompt uses the default loader."""
        # Arrange
        template_dir = tmp_path / "prompts"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("Hello {{ name }}!")

        # Create a loader and monkeypatch get_default_loader
        loader = PromptLoader(template_dir=template_dir)
        monkeypatch.setattr("src.utils.prompt_loader._default_loader", loader)

        # Act
        result = render_prompt("test.j2", name="World")

        # Assert
        assert result == "Hello World!"

    def test_render_prompt_with_correlation_id(self, tmp_path, monkeypatch):
        """Test render_prompt with correlation ID."""
        # Arrange
        template_dir = tmp_path / "prompts"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("Test")

        loader = PromptLoader(template_dir=template_dir)
        monkeypatch.setattr("src.utils.prompt_loader._default_loader", loader)

        # Act
        result = render_prompt("test.j2", correlation_id="test-123")

        # Assert
        assert result == "Test"


class TestGetDefaultLoader:
    """Test cases for get_default_loader function."""

    def test_get_default_loader_creates_singleton(self, monkeypatch):
        """Test that get_default_loader creates and reuses singleton."""
        # Arrange
        monkeypatch.setattr("src.utils.prompt_loader._default_loader", None)

        # Act
        loader1 = get_default_loader()
        loader2 = get_default_loader()

        # Assert
        assert loader1 is loader2  # Same instance

    def test_get_default_loader_returns_prompt_loader(self, monkeypatch):
        """Test that get_default_loader returns PromptLoader instance."""
        # Arrange
        monkeypatch.setattr("src.utils.prompt_loader._default_loader", None)

        # Act
        loader = get_default_loader()

        # Assert
        assert isinstance(loader, PromptLoader)


class TestRealTemplates:
    """Integration tests with real project templates."""

    def test_department_relevance_template(self):
        """Test rendering actual department relevance template."""
        # Act
        result = render_prompt(
            "department/relevance_filter.j2",
            interests="machine learning",
            degree="PhD Computer Science",
            background="BS in CS",
            department_name="Computer Science",
            school="Engineering",
        )

        # Assert
        assert "machine learning" in result
        assert "PhD Computer Science" in result
        assert "Computer Science" in result
        assert "Engineering" in result
        assert "JSON" in result

    def test_professor_research_filter_template(self):
        """Test rendering actual professor research filter template."""
        # Act
        result = render_prompt(
            "professor/research_filter.j2",
            profile="PhD student in ML",
            name="Dr. Jane Smith",
            research_areas="deep learning, NLP",
            bio="Professor of CS",
        )

        # Assert
        assert "PhD student in ML" in result
        assert "Dr. Jane Smith" in result
        assert "deep learning, NLP" in result
        assert "Professor of CS" in result
        assert "confidence" in result

    def test_linkedin_profile_match_template(self):
        """Test rendering actual LinkedIn profile match template."""
        # Act
        result = render_prompt(
            "linkedin/profile_match.j2",
            member_name="John Doe",
            university="Stanford",
            lab_name="AI Lab",
            profile_data="PhD student at Stanford",
        )

        # Assert
        assert "John Doe" in result
        assert "Stanford" in result
        assert "AI Lab" in result
        assert "PhD student at Stanford" in result

    def test_name_match_template(self):
        """Test rendering actual name match template."""
        # Act
        result = render_prompt(
            "professor/name_match.j2",
            name1="J. Smith",
            name2="Jane Smith",
            context="Both at Stanford CS",
        )

        # Assert
        assert "J. Smith" in result
        assert "Jane Smith" in result
        assert "Both at Stanford CS" in result

    def test_abstract_relevance_template(self):
        """Test rendering actual abstract relevance template."""
        # Act
        result = render_prompt(
            "publication/abstract_relevance.j2",
            interests="machine learning",
            abstract="We propose a new ML algorithm...",
            title="Novel ML Approach",
        )

        # Assert
        assert "machine learning" in result
        assert "We propose a new ML algorithm..." in result
        assert "Novel ML Approach" in result
