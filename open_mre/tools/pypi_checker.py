"""PyPI package version checking tool."""

import httpx
from langchain_core.tools import tool


@tool
def check_pypi_version(package_name: str) -> dict[str, str | None]:
    """Query PyPI JSON API to get latest version of a package.

    Args:
        package_name: Name of Python package (e.g., `'requests'`)

    Returns:
        `{"package": "requests", "latest_version": "2.31.0", "error": null}`
    """
    try:
        response = httpx.get(
            f"https://pypi.org/pypi/{package_name}/json",
            timeout=5.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "package": package_name,
            "latest_version": data["info"]["version"],
            "error": None,
        }
    except Exception as e:
        return {
            "package": package_name,
            "latest_version": None,
            "error": str(e),
        }
