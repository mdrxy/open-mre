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


def test_execute_python_code_success() -> None:
    """Test successful code execution with langchain repo."""
    code = "print('Hello, World!')"

    # Mock Daytona sandbox
    mock_sandbox = MagicMock()
    mock_response = MagicMock()
    mock_response.exit_code = 0
    mock_response.result = "Hello, World!\n"
    mock_sandbox.process.code_run.return_value = mock_response

    # Mock Daytona client
    mock_daytona = MagicMock()
    mock_daytona.create.return_value = mock_sandbox

    # Mock the CreateSandboxFromImageParams to avoid Pydantic validation
    mock_params = MagicMock()

    with (
        patch("open_mre.tools.code_executor.Daytona", return_value=mock_daytona),
        patch("open_mre.tools.code_executor._create_langchain_image") as mock_image,
        patch(
            "open_mre.tools.code_executor.CreateSandboxFromImageParams",
            return_value=mock_params,
        ),
    ):
        result = execute_python_code.invoke(
            {"code": code, "packages": [], "timeout": 5}
        )

    assert result["exit_code"] == 0
    assert "Hello, World!" in result["stdout"]
    assert result["exception"] is None
    assert result["timed_out"] is False
    assert result["sandbox_available"] is True
    assert result["langchain_repo_path"] == "/workspace/langchain"
    # Verify image was created
    mock_image.assert_called_once()
    mock_sandbox.delete.assert_called_once()


def test_execute_python_code_error() -> None:
    """Test code execution with error."""
    code = "raise ValueError('Test error')"

    # Mock Daytona sandbox
    mock_sandbox = MagicMock()
    mock_response = MagicMock()
    mock_response.exit_code = 1
    mock_response.result = (
        "Traceback (most recent call last):\n  File ...\nValueError: Test error"
    )
    mock_sandbox.process.code_run.return_value = mock_response

    # Mock Daytona client
    mock_daytona = MagicMock()
    mock_daytona.create.return_value = mock_sandbox

    with (
        patch("open_mre.tools.code_executor.Daytona", return_value=mock_daytona),
        patch("open_mre.tools.code_executor._create_langchain_image"),
        patch("open_mre.tools.code_executor.CreateSandboxFromImageParams"),
    ):
        result = execute_python_code.invoke(
            {"code": code, "packages": [], "timeout": 5}
        )

    assert result["exit_code"] == 1
    assert result["exception"] is not None
    assert "ValueError" in result["stderr"]
    assert result["langchain_repo_path"] == "/workspace/langchain"
    mock_sandbox.delete.assert_called_once()


def test_execute_python_code_needs_interaction() -> None:
    """Test code that needs user interaction."""
    code = "x = input('Enter value: ')"

    # This test doesn't need mocking since we detect input() before creating sandbox
    result = execute_python_code.invoke({"code": code, "packages": [], "timeout": 5})

    assert result["needs_interaction"] is True
    assert "input() detected" in result["stderr"]


def test_execute_python_code_timeout() -> None:
    """Test code execution timeout."""
    code = "import time; time.sleep(10)"

    # Mock Daytona sandbox to raise TimeoutError
    mock_sandbox = MagicMock()
    mock_sandbox.process.code_run.side_effect = TimeoutError("Execution timed out")

    # Mock Daytona client
    mock_daytona = MagicMock()
    mock_daytona.create.return_value = mock_sandbox

    with (
        patch("open_mre.tools.code_executor.Daytona", return_value=mock_daytona),
        patch("open_mre.tools.code_executor._create_langchain_image"),
        patch("open_mre.tools.code_executor.CreateSandboxFromImageParams"),
    ):
        result = execute_python_code.invoke(
            {"code": code, "packages": [], "timeout": 2}
        )

    assert result["timed_out"] is True
    assert result["exit_code"] == -1
    assert "timed out" in result["stderr"]
    assert result["langchain_repo_path"] == "/workspace/langchain"
    mock_sandbox.delete.assert_called_once()


def test_execute_python_code_with_packages() -> None:
    """Test code execution with package installation."""
    code = "import pandas as pd; print(pd.__version__)"
    packages = ["pandas==2.1.3"]

    # Mock Daytona sandbox
    mock_sandbox = MagicMock()

    # Mock install response
    install_response = MagicMock()
    install_response.exit_code = 0
    install_response.result = "Successfully installed pandas-2.1.3"

    # Mock execution response
    exec_response = MagicMock()
    exec_response.exit_code = 0
    exec_response.result = "2.1.3\n"

    # Set side_effect to return install response first, then exec response
    mock_sandbox.process.code_run.side_effect = [install_response, exec_response]

    # Mock Daytona client
    mock_daytona = MagicMock()
    mock_daytona.create.return_value = mock_sandbox

    with (
        patch("open_mre.tools.code_executor.Daytona", return_value=mock_daytona),
        patch("open_mre.tools.code_executor._create_langchain_image"),
        patch("open_mre.tools.code_executor.CreateSandboxFromImageParams"),
    ):
        result = execute_python_code.invoke(
            {"code": code, "packages": packages, "timeout": 5}
        )

    assert result["exit_code"] == 0
    assert "2.1.3" in result["stdout"]
    assert result["exception"] is None
    assert result["langchain_repo_path"] == "/workspace/langchain"
    # Verify both install and execute were called
    assert mock_sandbox.process.code_run.call_count == 2
    mock_sandbox.delete.assert_called_once()


def test_execute_python_code_sandbox_unavailable() -> None:
    """Test code execution when sandbox initialization fails."""
    code = "print('This will not run')"

    # Mock Daytona client to raise an exception during sandbox creation
    mock_daytona = MagicMock()
    mock_daytona.create.side_effect = Exception("Sandbox service unavailable")

    with (
        patch("open_mre.tools.code_executor.Daytona", return_value=mock_daytona),
        patch("open_mre.tools.code_executor._create_langchain_image"),
        patch("open_mre.tools.code_executor.CreateSandboxFromImageParams"),
    ):
        result = execute_python_code.invoke(
            {"code": code, "packages": [], "timeout": 5}
        )

    assert result["exit_code"] == -1
    assert result["sandbox_available"] is False
    assert "Sandbox initialization error" in result["stderr"]
    assert result["exception"] is not None
    assert "Sandbox service unavailable" in result["exception"]
    assert result["langchain_repo_path"] == "/workspace/langchain"


def test_create_langchain_image() -> None:
    """Test that custom image is created with correct parameters."""
    code = "print('test')"

    mock_sandbox = MagicMock()
    mock_response = MagicMock()
    mock_response.exit_code = 0
    mock_response.result = "test\n"
    mock_sandbox.process.code_run.return_value = mock_response

    mock_daytona = MagicMock()
    mock_daytona.create.return_value = mock_sandbox

    mock_image = MagicMock()

    with (
        patch("open_mre.tools.code_executor.Daytona", return_value=mock_daytona),
        patch(
            "open_mre.tools.code_executor._create_langchain_image",
            return_value=mock_image,
        ) as mock_create_image,
        patch("open_mre.tools.code_executor.CreateSandboxFromImageParams"),
    ):
        execute_python_code.invoke({"code": code, "packages": [], "timeout": 5})

    # Verify _create_langchain_image was called with correct defaults
    mock_create_image.assert_called_once()
    call_kwargs = mock_create_image.call_args.kwargs

    assert call_kwargs["repo_url"] == "https://github.com/langchain-ai/langchain.git"
    assert call_kwargs["repo_path"] == "/workspace/langchain"
    assert call_kwargs["python_version"] == "3.12"


def test_execute_python_code_with_env_vars() -> None:
    """Test that environment variables are passed to sandbox."""
    code = "import os; print(os.environ.get('API_KEY', 'not found'))"

    # Set environment variables with SANDBOX_ENV_ prefix
    original_env = os.environ.copy()
    os.environ["SANDBOX_ENV_API_KEY"] = "test-key-123"
    os.environ["SANDBOX_ENV_DATABASE_URL"] = "postgresql://localhost"

    try:
        # Mock Daytona sandbox
        mock_sandbox = MagicMock()
        mock_response = MagicMock()
        mock_response.exit_code = 0
        mock_response.result = "test-key-123\n"
        mock_sandbox.process.code_run.return_value = mock_response

        # Mock Daytona client
        mock_daytona = MagicMock()
        mock_daytona.create.return_value = mock_sandbox

        mock_image = MagicMock()

        with (
            patch("open_mre.tools.code_executor.Daytona", return_value=mock_daytona),
            patch(
                "open_mre.tools.code_executor._create_langchain_image",
                return_value=mock_image,
            ) as mock_create_image,
            patch("open_mre.tools.code_executor.CreateSandboxFromImageParams"),
        ):
            result = execute_python_code.invoke(
                {"code": code, "packages": [], "timeout": 5}
            )

        # Verify the image was created with env vars
        mock_create_image.assert_called_once()
        call_kwargs = mock_create_image.call_args.kwargs

        # Check that env_vars were passed correctly (without SANDBOX_ENV_ prefix)
        assert call_kwargs["env_vars"] is not None
        assert "API_KEY" in call_kwargs["env_vars"]
        assert call_kwargs["env_vars"]["API_KEY"] == "test-key-123"
        assert "DATABASE_URL" in call_kwargs["env_vars"]
        assert call_kwargs["env_vars"]["DATABASE_URL"] == "postgresql://localhost"

        # Verify execution succeeded
        assert result["exit_code"] == 0
        assert "test-key-123" in result["stdout"]

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_execute_python_code_without_env_vars() -> None:
    """Test that code execution works when no env vars are provided."""
    code = "print('Hello')"

    # Ensure no SANDBOX_ENV_ vars exist
    original_env = os.environ.copy()
    env_to_remove = [k for k in os.environ if k.startswith("SANDBOX_ENV_")]
    for key in env_to_remove:
        del os.environ[key]

    try:
        # Mock Daytona sandbox
        mock_sandbox = MagicMock()
        mock_response = MagicMock()
        mock_response.exit_code = 0
        mock_response.result = "Hello\n"
        mock_sandbox.process.code_run.return_value = mock_response

        # Mock Daytona client
        mock_daytona = MagicMock()
        mock_daytona.create.return_value = mock_sandbox

        mock_image = MagicMock()

        with (
            patch("open_mre.tools.code_executor.Daytona", return_value=mock_daytona),
            patch(
                "open_mre.tools.code_executor._create_langchain_image",
                return_value=mock_image,
            ) as mock_create_image,
            patch("open_mre.tools.code_executor.CreateSandboxFromImageParams"),
        ):
            result = execute_python_code.invoke(
                {"code": code, "packages": [], "timeout": 5}
            )

        # Verify the image was created with None or empty env vars
        mock_create_image.assert_called_once()
        call_kwargs = mock_create_image.call_args.kwargs
        # When no env vars, should pass None (empty dict evaluates to False)
        env_vars_param = call_kwargs["env_vars"]
        assert env_vars_param is None or not env_vars_param

        # Verify execution succeeded
        assert result["exit_code"] == 0
        assert "Hello" in result["stdout"]

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)
