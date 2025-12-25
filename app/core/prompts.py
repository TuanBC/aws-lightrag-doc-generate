"""Prompt template loader for .prompty files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from app.core.config import get_settings


class PromptLoader:
    """Load and render .prompty templates."""

    def __init__(self, prompts_dir: Optional[Path] = None):
        settings = get_settings()
        self.prompts_dir = prompts_dir or settings.prompts_dir

    def load(self, template_name: str) -> str:
        """
        Load a .prompty template file.

        Args:
            template_name: Template name (with or without .prompty extension)

        Returns:
            Template content (without YAML frontmatter)
        """
        if not template_name.endswith(".prompty"):
            template_name = f"{template_name}.prompty"

        template_path = self.prompts_dir / template_name

        if not template_path.exists():
            raise FileNotFoundError(f"Template '{template_name}' not found in: {self.prompts_dir}")

        content = template_path.read_text(encoding="utf-8")

        # Remove YAML frontmatter (between --- markers)
        content = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL)

        return content.strip()

    def render(self, template_name: str, **variables: Any) -> str:
        """
        Load and render a .prompty template with variables.

        Args:
            template_name: Template name
            **variables: Variables to substitute in the template

        Returns:
            Rendered template string
        """
        template = self.load(template_name)

        # Replace {{ variable }} patterns
        for key, value in variables.items():
            # Handle both {{ var }} and {{var}} formats
            pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"
            template = re.sub(pattern, str(value), template)

        return template


# Singleton instance
_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Get the singleton prompt loader instance."""
    global _loader
    if _loader is None:
        _loader = PromptLoader()
    return _loader


def load_prompt(template_name: str, **variables: Any) -> str:
    """
    Convenience function to load and render a prompt template.

    Args:
        template_name: Template name (e.g., 'planning_create' or 'srs_template')
        **variables: Variables to substitute

    Returns:
        Rendered prompt string
    """
    return get_prompt_loader().render(template_name, **variables)
