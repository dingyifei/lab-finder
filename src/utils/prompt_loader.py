"""
Jinja2-based prompt template loading and rendering.

This module provides utilities for loading and rendering LLM prompt templates
from the prompts/ directory. Templates support Jinja2 features including:
- Variable substitution
- Template inheritance ({% extends %})
- Conditional logic ({% if %})
- Loops ({% for %})

Usage:
    from src.utils.prompt_loader import render_prompt

    prompt = render_prompt(
        "professor/research_filter.j2",
        name="Dr. Smith",
        research_areas="Machine Learning, AI",
        profile=user_profile
    )
"""

from pathlib import Path
from typing import Any, Optional

import structlog
from jinja2 import (
    Environment,
    FileSystemLoader,
    TemplateNotFound,
    TemplateSyntaxError,
    UndefinedError,
)

logger = structlog.get_logger(__name__)


class PromptLoader:
    """
    Manages loading and rendering of Jinja2 prompt templates.

    Templates are loaded from the prompts/ directory relative to the project root.
    Supports template inheritance, custom filters, and error handling.
    """

    def __init__(
        self,
        template_dir: Optional[Path] = None,
        strict_undefined: bool = False,
    ) -> None:
        """
        Initialize PromptLoader with Jinja2 environment.

        Args:
            template_dir: Base directory for templates (defaults to prompts/ in project root)
            strict_undefined: If True, raise error for undefined variables (default: False)
        """
        if template_dir is None:
            # Assume project root is 2 levels up from this file (src/utils/)
            project_root = Path(__file__).parent.parent.parent
            template_dir = project_root / "prompts"

        self.template_dir = template_dir
        self.strict_undefined = strict_undefined

        # Configure Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=False,  # Prompts are text, not HTML
            trim_blocks=True,  # Remove first newline after template tag
            lstrip_blocks=True,  # Strip leading spaces/tabs from start of line to start of block
            keep_trailing_newline=True,  # Preserve trailing newline
        )

        # Add custom filters if needed
        self.env.filters["strip_markdown"] = self._strip_markdown_filter

        logger.debug(
            "PromptLoader initialized",
            template_dir=str(self.template_dir),
            strict_undefined=strict_undefined,
        )

    def render(
        self,
        template_name: str,
        correlation_id: Optional[str] = None,
        **variables: Any,
    ) -> str:
        """
        Render a template with provided variables.

        Args:
            template_name: Path to template relative to prompts/ (e.g., "professor/research_filter.j2")
            correlation_id: Optional correlation ID for logging
            **variables: Template variables as keyword arguments

        Returns:
            Rendered prompt string

        Raises:
            TemplateNotFound: If template file doesn't exist
            TemplateSyntaxError: If template has syntax errors
            UndefinedError: If strict_undefined=True and variable is missing
        """
        log = logger.bind(
            template_name=template_name,
            correlation_id=correlation_id,
        )

        try:
            template = self.env.get_template(template_name)
            log.debug("Template loaded", template_path=str(self.template_dir / template_name))

            rendered = template.render(**variables)
            log.debug(
                "Template rendered",
                rendered_length=len(rendered),
                variables_provided=list(variables.keys()),
            )

            return rendered

        except TemplateNotFound as e:
            log.error(
                "Template not found",
                template_name=template_name,
                template_dir=str(self.template_dir),
                error=str(e),
            )
            raise

        except TemplateSyntaxError as e:
            log.error(
                "Template syntax error",
                template_name=template_name,
                error=str(e),
                lineno=e.lineno,
            )
            raise

        except UndefinedError as e:
            log.error(
                "Undefined variable in template",
                template_name=template_name,
                error=str(e),
                variables_provided=list(variables.keys()),
            )
            raise

    def get_system_prompt(
        self,
        prompt_type: str,
        correlation_id: Optional[str] = None,
        **variables: Any,
    ) -> str:
        """
        Load and render a system prompt template.

        Convenience method for loading prompts from the base/ directory.

        Args:
            prompt_type: Type of system prompt (e.g., "analysis", "filtering")
            correlation_id: Optional correlation ID for logging
            **variables: Template variables as keyword arguments

        Returns:
            Rendered system prompt string
        """
        template_name = f"base/{prompt_type}.j2"
        return self.render(template_name, correlation_id=correlation_id, **variables)

    @staticmethod
    def _strip_markdown_filter(text: str) -> str:
        """
        Custom Jinja2 filter to strip markdown formatting.

        Args:
            text: Input text with markdown

        Returns:
            Text with markdown formatting removed
        """
        # Simple implementation - can be enhanced with markdown library if needed
        import re

        # Remove code blocks
        text = re.sub(r"```[\s\S]*?```", "", text)
        # Remove inline code
        text = re.sub(r"`([^`]*)`", r"\1", text)
        # Remove bold/italic
        text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]*)\*", r"\1", text)
        # Remove headers
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

        return text.strip()


# Global instance for convenience
_default_loader: Optional[PromptLoader] = None


def get_default_loader() -> PromptLoader:
    """
    Get or create the default PromptLoader instance.

    Returns:
        Global PromptLoader instance
    """
    global _default_loader
    if _default_loader is None:
        _default_loader = PromptLoader()
    return _default_loader


def render_prompt(
    template_name: str,
    correlation_id: Optional[str] = None,
    **variables: Any,
) -> str:
    """
    Convenience function to render a prompt template.

    Uses the default PromptLoader instance. For most use cases, this is the
    recommended entry point.

    Args:
        template_name: Path to template relative to prompts/ (e.g., "professor/research_filter.j2")
        correlation_id: Optional correlation ID for logging
        **variables: Template variables as keyword arguments

    Returns:
        Rendered prompt string

    Raises:
        TemplateNotFound: If template file doesn't exist
        TemplateSyntaxError: If template has syntax errors
        UndefinedError: If template references undefined variables

    Example:
        >>> prompt = render_prompt(
        ...     "professor/research_filter.j2",
        ...     name="Dr. Smith",
        ...     research_areas="ML, AI",
        ...     profile=user_profile
        ... )
    """
    loader = get_default_loader()
    return loader.render(template_name, correlation_id=correlation_id, **variables)
