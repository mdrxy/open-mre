"""Input/output schemas for the code extractor agent."""

from typing_extensions import TypedDict


class CodeExtractorInput(TypedDict):
    """Input to the code extractor agent."""

    issue_content: str
    version_notes: list[str]  # Notes from version validation to include in comments


class CodeExtractorOutput(TypedDict):
    """Output from the code extractor agent."""

    code_snippets: list[str]
    extraction_notes: list[str]
    draft_comment: str | None
    should_terminate: bool
