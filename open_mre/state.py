"""Core state definitions for the MRE validation system."""

from typing import Annotated

from typing_extensions import TypedDict


class PackageInfo(TypedDict):
    """Information about a Python package mentioned in an issue."""

    name: str
    user_version: str | None
    latest_version: str | None
    is_outdated: bool | None


class MREValidationState(TypedDict):
    """Graph state for validation workflow.

    Passed through all nodes in the coordinator graph.

    Each agent subgraph receives a subset of this state as input
    and returns updates to specific fields.
    """

    # Input
    issue_content: str

    # Version validation results
    python_version: str | None
    packages: list[PackageInfo]
    version_notes: list[str]

    # Code extraction results
    code_snippets: list[str]
    extraction_notes: list[str]

    # Behavior analysis results
    expected_behavior: str | None
    actual_behavior: str | None
    analysis_notes: list[str]
    requires_api_keys: bool
    detected_api_providers: list[str]

    # Execution context (set after API key approval)
    approved_api_keys: dict[str, str]

    # Execution results
    execution_output: str | None
    execution_error: str | None
    hydrated_code: str | None

    # Final outputs
    draft_comments: Annotated[list[str], lambda x, y: x + y]  # Reducer: append
    validation_report: str | None
    reproduction_script: str | None

    # Control flow
    should_terminate: bool
    termination_reason: str | None


class ValidationResult(TypedDict):
    """Final output of the MRE validation process."""

    validation_report: str
    reproduction_script: str | None
    draft_comments: list[str]
    was_reproduced: bool
    termination_reason: str | None
