"""Version validation subagent for checking package versions against PyPI."""

from deepagents.middleware.subagents import SubAgent

from open_mre.tools import check_pypi_version

VERSION_VALIDATOR_PROMPT = """You are a Python package version validator. Given a bug
report:

1. Extract all mentioned packages and versions from the markdown file
    - Look for patterns like: "pandas 2.0.0", "numpy>=1.24", "langchain==0.1.0"
    - Look in code imports for package names

2. For each package found, use the `check_pypi_version` tool to check the latest version

3. If no version mentioned for a package, assume user is using latest

4. Write results to `/version_report.json` with this exact JSON structure:
    {
        "packages": [
            {
            "name": "package_name",
            "mentioned_version": "1.0.0" or null,
            "latest_version": "1.2.0",
            "is_latest": false,
            "needs_update": true
            }
        ],
        "all_latest": false,
        "can_proceed": true
    }

5. Set `can_proceed: false` if any version mentioned is not the latest

Return a summary of version validation results.
"""

version_validator_subagent: SubAgent = {
    "name": "version_validator",
    "description": (
        "Validates that mentioned package versions are latest. Extracts package names "
        "and versions from issue, queries PyPI API, and returns version status report."
    ),
    "system_prompt": VERSION_VALIDATOR_PROMPT,
    "tools": [check_pypi_version],
}
