"""Tests for custom tools."""

import os
from unittest.mock import MagicMock, patch

from open_mre.tools import check_pypi_version, execute_python_code


def test_check_pypi_version_success() -> None:
    """Test successful PyPI version check."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"info": {"version": "2.31.0"}}
    mock_response.raise_for_status.return_value = None

    with patch("open_mre.tools.pypi_checker.httpx.get", return_value=mock_response):
        result = check_pypi_version.invoke({"package_name": "requests"})

    assert result["package"] == "requests"
    assert result["latest_version"] == "2.31.0"
    assert result["error"] is None


def test_check_pypi_version_not_found() -> None:
    """Test PyPI version check for non-existent package."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("404 Not Found")

    with patch("open_mre.tools.pypi_checker.httpx.get", return_value=mock_response):
        result = check_pypi_version.invoke(
            {"package_name": "this-package-does-not-exist-xyz123"}
        )

    assert result["package"] == "this-package-does-not-exist-xyz123"
    assert result["latest_version"] is None
    assert result["error"] is not None
