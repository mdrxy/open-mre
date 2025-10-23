"""Code execution tool for running Python code in isolated Daytona sandboxes."""

import logging
import os
import time
from typing import Literal, get_args

from daytona import CreateSandboxFromImageParams, Daytona, Image
from langchain_core.tools import tool

# Configure logging for sandbox lifecycle tracking
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Type alias for supported Python versions
PythonVersion = Literal["3.10", "3.11", "3.12", "3.13"]


def _create_langchain_image(
    repo_url: str = "https://github.com/langchain-ai/langchain.git",
    repo_path: str = "/workspace/langchain",
    python_version: PythonVersion = "3.12",
    branch: str | None = None,
    env_vars: dict[str, str] | None = None,
) -> Image:
    """Create a custom Daytona image with langchain repository pre-cloned.

    Args:
        repo_url: Git repository URL to clone
        repo_path: Path where to clone the repository in the sandbox
        python_version: Python version for the base image
        branch: Optional git branch to checkout
        env_vars: Environment variables to set in the sandbox

    Returns:
        Configured Image object with langchain repo pre-cloned
    """
    # Build git clone command
    clone_cmd = f"git clone {repo_url} {repo_path}"
    if branch:
        clone_cmd = f"git clone -b {branch} {repo_url} {repo_path}"

    # Create custom image with git and the cloned repo
    image = Image.debian_slim(python_version).run_commands(
        "apt-get update && apt-get install -y git",
        clone_cmd,
    )

    # Set environment variables if provided
    if env_vars:
        image = image.env(env_vars)

    return image.workdir(repo_path)


@tool
def execute_python_code(
    code: str,
    packages: list[str] | None = None,
    timeout: int = 30,
) -> dict[str, str | int | bool | None]:
    """Execute Python code in an isolated Daytona sandbox.

    The sandbox is created with a custom image that includes `langchain-ai/langchain`
    pre-cloned at `/workspace/langchain`. This allows the code to access the langchain
    source code for debugging and investigation.

    Args:
        code: Python code to execute
        packages: List of packages to install before execution
            (e.g., `["pandas==2.1.3"]`)
        timeout: Maximum execution time in seconds

    Returns:
        ```json
        {
            "exit_code": 0,
            "stdout": "...",
            "stderr": "...",
            "exception": None,
            "timed_out": false,
            "needs_interaction": false,
            "execution_time_ms": 1234,
            "sandbox_available": true,
            "langchain_repo_path": "/workspace/langchain"
        }
        ```
        Note: `sandbox_available` will be `false` if sandbox initialization fails.
            The langchain repository is available at `/workspace/langchain`.
    """
    packages = packages or []
    start_time = time.time()

    repo_url = os.getenv(
        "LANGCHAIN_REPO_URL",
        "https://github.com/langchain-ai/langchain.git",
    )
    repo_path = os.getenv("LANGCHAIN_REPO_PATH", "/workspace/langchain")
    repo_branch = os.getenv("LANGCHAIN_REPO_BRANCH")  # Optional
    python_version_str = os.getenv("PYTHON_VERSION", "3.12")

    allowed_versions: tuple[str, ...] = get_args(PythonVersion)
    if python_version_str not in allowed_versions:
        python_version: PythonVersion = "3.12"  # Fallback
    else:
        python_version = python_version_str  # type: ignore[assignment]

    sandbox_env_vars: dict[str, str] = {}
    for key, value in os.environ.items():
        if key.startswith("SANDBOX_ENV_"):
            # Strip the SANDBOX_ENV_ prefix
            actual_key = key[len("SANDBOX_ENV_") :]
            sandbox_env_vars[actual_key] = value

    result: dict[str, str | int | bool | None] = {
        "exit_code": 0,
        "stdout": "",
        "stderr": "",
        "exception": None,
        "timed_out": False,
        "needs_interaction": False,
        "execution_time_ms": 0,
        "sandbox_available": True,
        "langchain_repo_path": repo_path,
    }

    sandbox = None
    sandbox_id = None
    try:
        # Check if code requires user input
        if "input(" in code:
            result["needs_interaction"] = True
            result["stderr"] = "Code requires user interaction (input() detected)"
            return result

        daytona = Daytona()

        image = _create_langchain_image(
            repo_url=repo_url,
            repo_path=repo_path,
            python_version=python_version,
            branch=repo_branch,
            env_vars=sandbox_env_vars if sandbox_env_vars else None,
        )

        logger.info("Creating Daytona sandbox...")
        sandbox = daytona.create(
            CreateSandboxFromImageParams(image=image),
        )
        sandbox_id = getattr(sandbox, "id", "unknown")
        logger.info("Sandbox created successfully: %s", sandbox_id)

        # Install packages if needed
        if packages:
            try:
                # Convert package list to pip install format
                packages_str = " ".join(packages)
                install_cmd = (
                    f"pip install --quiet --disable-pip-version-check {packages_str}"
                )

                install_response = sandbox.process.code_run(
                    install_cmd,
                    timeout=120,
                )

                if install_response.exit_code != 0:
                    msg = "Package installation failed"
                    result["stderr"] = f"{msg}: {install_response.result}"
                    result["exit_code"] = int(install_response.exit_code)
                    return result

            except Exception as e:
                msg = f"Package installation error: {e!s}"
                result["stderr"] = msg
                result["exception"] = str(e)
                result["exit_code"] = -1
                return result

        # Execute the code
        try:
            execution_response = sandbox.process.code_run(
                code,
                timeout=timeout,
            )

            result["exit_code"] = int(execution_response.exit_code)
            result["stdout"] = execution_response.result or ""

            # Daytona returns error information in the result when exit_code != 0
            if execution_response.exit_code != 0:
                result["stderr"] = execution_response.result or ""

                # Try to extract exception from the result
                result_lines = (execution_response.result or "").strip().split("\n")
                if result_lines:
                    # Usually the last line is the exception
                    result["exception"] = result_lines[-1]

        except TimeoutError:
            result["timed_out"] = True
            result["stderr"] = f"Execution timed out after {timeout} seconds"
            result["exit_code"] = -1
        except Exception as e:
            msg = f"Code execution error: {e!s}"
            result["exception"] = str(e)
            result["stderr"] = msg
            result["exit_code"] = -1

    except Exception as e:
        result["exception"] = str(e)
        result["stderr"] = f"Sandbox initialization error: {e!s}"
        result["exit_code"] = -1
        result["sandbox_available"] = False

    finally:
        # Clean up sandbox resources with retry logic
        if sandbox is not None:
            cleanup_success = False
            max_retries = 3

            for attempt in range(max_retries):
                try:
                    logger.info(
                        "Attempting to delete sandbox %s (attempt %d/%d)...",
                        sandbox_id,
                        attempt + 1,
                        max_retries,
                    )
                    sandbox.delete()
                    logger.info("Sandbox %s deleted successfully", sandbox_id)
                    cleanup_success = True
                    break
                except Exception as cleanup_error:
                    logger.warning(
                        "Cleanup attempt %d failed for sandbox %s: %s",
                        attempt + 1,
                        sandbox_id,
                        cleanup_error,
                    )
                    if attempt < max_retries - 1:
                        # Wait before retry (exponential backoff)
                        time.sleep(2**attempt)
                    else:
                        logger.exception(
                            "Failed to cleanup sandbox %s after %d attempts. "
                            "This may cause orphaned sandboxes!",
                            sandbox_id,
                            max_retries,
                        )

            # Add cleanup status to result for visibility
            if not cleanup_success:
                stderr_msg = f"WARNING: Sandbox cleanup failed for {sandbox_id}"
                if result["stderr"]:
                    result["stderr"] = f"{result['stderr']}\n\n{stderr_msg}"
                else:
                    result["stderr"] = stderr_msg

    execution_time = time.time() - start_time
    result["execution_time_ms"] = int(execution_time * 1000)

    return result
