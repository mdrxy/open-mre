"""Input/output schemas for the behavior analyst agent."""

from typing_extensions import TypedDict


class BehaviorAnalystInput(TypedDict):
    """Input to the behavior analyst agent."""

    issue_content: str
    code_snippets: list[str]
    version_notes: list[str]


class BehaviorAnalystOutput(TypedDict):
    """Output from the behavior analyst agent."""

    expected_behavior: str | None
    actual_behavior: str | None
    analysis_notes: list[str]
    requires_api_keys: bool
    detected_api_providers: list[str]
    draft_comment: str | None
    should_terminate: bool
