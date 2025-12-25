"""Critic agent for validating generated documents."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional

from jinja2 import Environment, FileSystemLoader

from app.core.config import get_settings
from app.core.llm import get_llm

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity level of validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Single validation issue found in document."""

    severity: ValidationSeverity
    category: str
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of a validation check."""

    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    checked_items: int = 0

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue and update passed status."""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.ERROR:
            self.passed = False


@dataclass
class CriticReport:
    """Complete critic report for a document."""

    overall_passed: bool
    markdown_result: ValidationResult
    mermaid_result: ValidationResult
    content_result: Optional[ValidationResult] = None
    total_errors: int = 0
    total_warnings: int = 0
    suggestions: List[str] = field(default_factory=list)


class CriticAgent:
    """
    Validate generated technical documents.

    Checks:
    - Markdown syntax validity
    - Mermaid chart syntax
    - Content structure and quality
    - Requirements compliance
    """

    # Common Mermaid syntax patterns
    MERMAID_TYPES = [
        "flowchart",
        "graph",
        "sequenceDiagram",
        "classDiagram",
        "stateDiagram",
        "stateDiagram-v2",
        "erDiagram",
        "gantt",
        "pie",
        "journey",
        "gitGraph",
        "mindmap",
        "timeline",
        "quadrantChart",
        "xychart-beta",
        "block-beta",
    ]

    # Mermaid syntax error patterns
    MERMAID_ERROR_PATTERNS = [
        (r"\[\s*\[", "Double brackets not allowed in node definitions"),
        (r"\]\s*\]", "Double brackets not allowed in node definitions"),
        (r"-->\s*$", "Arrow must have a target node"),
        (r"^\s*-->|^\s*---", "Arrow must have a source node"),
        (r"subgraph\s*$", "Subgraph must have a name"),
        (r"participant\s*$", "Participant must have a name"),
    ]

    def __init__(self):
        settings = get_settings()
        self.llm = get_llm()
        try:
            self.env = Environment(loader=FileSystemLoader(str(settings.prompts_dir)))
        except Exception:
            self.env = None

    def validate_markdown_syntax(self, content: str) -> ValidationResult:
        """
        Validate basic Markdown syntax.

        Checks:
        - Heading structure
        - Code block closure
        - Link syntax
        - List formatting
        """
        result = ValidationResult(passed=True)
        lines = content.split("\n")
        result.checked_items = len(lines)

        # Track state
        in_code_block = False
        code_block_start = 0
        heading_levels = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Code block tracking
            if stripped.startswith("```"):
                if in_code_block:
                    in_code_block = False
                else:
                    in_code_block = True
                    code_block_start = i
                continue

            if in_code_block:
                continue

            # Heading validation
            if stripped.startswith("#"):
                level = len(stripped) - len(stripped.lstrip("#"))
                if level > 6:
                    result.add_issue(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category="heading",
                            message="Heading level exceeds maximum (6)",
                            line_number=i,
                        )
                    )

                # Check heading hierarchy (shouldn't skip levels)
                if heading_levels and level > heading_levels[-1] + 1:
                    result.add_issue(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category="heading",
                            message=f"Heading skips from level {heading_levels[-1]} to {level}",
                            line_number=i,
                            suggestion="Consider using intermediate heading levels",
                        )
                    )
                heading_levels.append(level)

            # Link validation
            link_matches = re.findall(r"\[([^\]]*)\]\(([^)]*)\)", line)
            for text, url in link_matches:
                if not url:
                    result.add_issue(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category="link",
                            message=f"Empty URL in link '{text}'",
                            line_number=i,
                        )
                    )

            # Unclosed inline code
            backtick_count = line.count("`") - line.count("```") * 3
            if backtick_count % 2 != 0:
                result.add_issue(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="code",
                        message="Possible unclosed inline code block",
                        line_number=i,
                    )
                )

        # Check for unclosed code blocks
        if in_code_block:
            result.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="code",
                    message=f"Unclosed code block starting at line {code_block_start}",
                    line_number=code_block_start,
                )
            )

        return result

    def validate_mermaid_charts(self, content: str) -> ValidationResult:
        """
        Validate Mermaid chart syntax in document.

        Extracts all Mermaid blocks and checks for common syntax errors.
        """
        result = ValidationResult(passed=True)

        # Extract mermaid blocks
        mermaid_pattern = r"```mermaid\s*\n(.*?)```"
        mermaid_blocks = re.findall(mermaid_pattern, content, re.DOTALL)
        result.checked_items = len(mermaid_blocks)

        if not mermaid_blocks:
            result.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="mermaid",
                    message="No Mermaid diagrams found in document",
                )
            )
            return result

        for i, block in enumerate(mermaid_blocks, 1):
            block_lines = block.strip().split("\n")
            if not block_lines:
                result.add_issue(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="mermaid",
                        message=f"Empty Mermaid block #{i}",
                    )
                )
                continue

            # Check for valid diagram type
            first_line = block_lines[0].strip()
            valid_type = any(first_line.startswith(dtype) for dtype in self.MERMAID_TYPES)
            if not valid_type:
                result.add_issue(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="mermaid",
                        message=f"Invalid diagram type in block #{i}: '{first_line}'",
                        suggestion=f"Use one of: {', '.join(self.MERMAID_TYPES[:5])}...",
                    )
                )

            # Check for common syntax errors
            for line_num, line in enumerate(block_lines, 1):
                for pattern, error_msg in self.MERMAID_ERROR_PATTERNS:
                    if re.search(pattern, line):
                        result.add_issue(
                            ValidationIssue(
                                severity=ValidationSeverity.ERROR,
                                category="mermaid",
                                message=f"Block #{i}, line {line_num}: {error_msg}",
                            )
                        )

            # Check bracket balance
            open_brackets = block.count("[") + block.count("{") + block.count("(")
            close_brackets = block.count("]") + block.count("}") + block.count(")")
            if open_brackets != close_brackets:
                result.add_issue(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="mermaid",
                        message=f"Block #{i}: Unbalanced brackets",
                        suggestion="Check that all brackets are properly closed",
                    )
                )

            # Check subgraph closure
            subgraph_opens = len(re.findall(r"\bsubgraph\b", block))
            subgraph_closes = len(re.findall(r"\bend\b", block))
            if subgraph_opens != subgraph_closes:
                result.add_issue(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="mermaid",
                        message=f"Block #{i}: Unclosed subgraph ({subgraph_opens} opens, {subgraph_closes} ends)",
                    )
                )

        return result

    async def check_content_quality(
        self,
        content: str,
        requirements: Optional[str] = None,
    ) -> ValidationResult:
        """
        Use LLM to check content quality and requirements compliance.
        """
        result = ValidationResult(passed=True)
        result.checked_items = 1

        prompt = f"""Analyze this technical document for quality and completeness.

## Document Content
{content[:8000]}  # Truncate for token limit

## Evaluation Criteria
1. Structure: Does it have clear sections and hierarchy?
2. Completeness: Are all standard sections present?
3. Clarity: Is the language clear and professional?
4. Technical accuracy: Are technical terms used correctly?

{f"## Requirements to Check\n{requirements}" if requirements else ""}

## Response Format
Respond with a JSON object:
{{
  "passed": true/false,
  "issues": [
    {{"severity": "error/warning/info", "message": "...", "suggestion": "..."}}
  ],
  "overall_quality": 1-10
}}
"""

        try:
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            response_text = self._extract_content(response)

            # Try to parse JSON from response
            import json

            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                result.passed = data.get("passed", True)
                for issue in data.get("issues", []):
                    result.add_issue(
                        ValidationIssue(
                            severity=ValidationSeverity(issue.get("severity", "info")),
                            category="content",
                            message=issue.get("message", ""),
                            suggestion=issue.get("suggestion"),
                        )
                    )

        except Exception as e:
            logger.warning(f"LLM content check failed: {e}")
            result.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="content",
                    message="Could not perform LLM-based content analysis",
                )
            )

        return result

    def _extract_content(self, response: Any) -> str:
        """Extract text from LLM response."""
        if hasattr(response, "content"):
            if isinstance(response.content, str):
                return response.content
            if isinstance(response.content, list):
                return " ".join(
                    c.get("text", "") if isinstance(c, dict) else str(c) for c in response.content
                )
        return str(response)

    async def full_review(
        self,
        content: str,
        requirements: Optional[str] = None,
        check_content: bool = True,
    ) -> CriticReport:
        """
        Perform complete document review.

        Args:
            content: Document content to review
            requirements: Optional requirements to check against
            check_content: Whether to use LLM for content quality check

        Returns:
            Complete critic report
        """
        logger.info("Starting full document review")

        # Run all validations
        markdown_result = self.validate_markdown_syntax(content)
        mermaid_result = self.validate_mermaid_charts(content)

        content_result = None
        if check_content:
            content_result = await self.check_content_quality(content, requirements)

        # Calculate totals
        all_issues = (
            markdown_result.issues
            + mermaid_result.issues
            + (content_result.issues if content_result else [])
        )

        total_errors = sum(1 for i in all_issues if i.severity == ValidationSeverity.ERROR)
        total_warnings = sum(1 for i in all_issues if i.severity == ValidationSeverity.WARNING)

        # Overall pass = no errors
        overall_passed = total_errors == 0

        # Collect unique suggestions
        suggestions = list(set(i.suggestion for i in all_issues if i.suggestion))

        report = CriticReport(
            overall_passed=overall_passed,
            markdown_result=markdown_result,
            mermaid_result=mermaid_result,
            content_result=content_result,
            total_errors=total_errors,
            total_warnings=total_warnings,
            suggestions=suggestions,
        )

        logger.info(f"Review complete: {total_errors} errors, {total_warnings} warnings")
        return report
