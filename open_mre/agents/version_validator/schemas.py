"""Input/output schemas for the version validator agent."""

from typing_extensions import TypedDict

from open_mre.state import PackageInfo


class VersionValidatorInput(TypedDict):
    """Input to the version validator agent."""

    issue_content: str


class VersionValidatorOutput(TypedDict):
    """Output from the version validator agent."""

    python_version: str | None
    packages: list[PackageInfo]
    version_notes: list[str]
    draft_comment: str | None
    should_terminate: bool
