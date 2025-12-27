"""Input/output schemas for the executor agent."""

from typing_extensions import TypedDict

from open_mre.state import PackageInfo


class ExecutorInput(TypedDict):
    """Input to the executor agent."""

    code_snippets: list[str]
    packages: list[PackageInfo]
    approved_api_keys: dict[str, str]
    expected_behavior: str | None
    actual_behavior: str | None


class ExecutorOutput(TypedDict):
    """Output from the executor agent."""

    execution_output: str | None
    execution_error: str | None
    hydrated_code: str | None
    execution_notes: list[str]
