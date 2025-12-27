"""Input/output schemas for the report generator agent."""

from typing_extensions import TypedDict

from open_mre.state import PackageInfo


class ReportGeneratorInput(TypedDict):
    """Input to the report generator agent."""

    issue_content: str
    python_version: str | None
    packages: list[PackageInfo]
    version_notes: list[str]
    code_snippets: list[str]
    extraction_notes: list[str]
    expected_behavior: str | None
    actual_behavior: str | None
    analysis_notes: list[str]
    execution_output: str | None
    execution_error: str | None
    hydrated_code: str | None
    draft_comments: list[str]
    termination_reason: str | None


class ReportGeneratorOutput(TypedDict):
    """Output from the report generator agent."""

    validation_report: str
    reproduction_script: str | None
