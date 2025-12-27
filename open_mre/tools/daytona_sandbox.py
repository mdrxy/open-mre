"""Daytona sandbox tool for code execution.

Provides functions to create, execute code in, and clean up Daytona sandboxes.
"""

import contextlib
import logging
import os
import types
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

try:
    from daytona import Daytona, DaytonaConfig

    DAYTONA_AVAILABLE = True
except ImportError:
    DAYTONA_AVAILABLE = False
    Daytona = None
    DaytonaConfig = None


@dataclass
class ExecutionResult:
    """Result of code execution in a sandbox."""

    stdout: str
    stderr: str
    exit_code: int
    success: bool
    error_message: str | None = None


class DaytonaSandbox:
    """Wrapper around Daytona sandbox for code execution."""

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
    ) -> None:
        """Initialize the Daytona sandbox manager.

        Args:
            api_key: Daytona API key.

                Defaults to `DAYTONA_API_KEY` env var.
            api_url: Daytona API URL.

                Defaults to `DAYTONA_API_URL` env var.

        Raises:
            ImportError: If `daytona` is not installed.
            ValueError: If API key is not provided.
        """
        if not DAYTONA_AVAILABLE:
            msg = "daytona is not installed. Install it with: `pip install daytona`"
            raise ImportError(msg)

        self.api_key = api_key or os.environ.get("DAYTONA_API_KEY")
        self.api_url = api_url or os.environ.get(
            "DAYTONA_API_URL", "https://app.daytona.io/api"
        )

        if not self.api_key:
            msg = "Daytona API key is required"
            raise ValueError(msg)

        self.config = DaytonaConfig(
            api_key=self.api_key,
            api_url=self.api_url,
        )
        self.daytona = Daytona(self.config)
        self.sandbox: Any = None

    def create(self) -> None:
        """Create a new sandbox instance."""
        logger.info("Creating Daytona sandbox...")
        self.sandbox = self.daytona.create()
        logger.info("Sandbox created successfully")

    def install_packages(self, packages: list[str]) -> ExecutionResult:
        """Install Python packages in the sandbox.

        Args:
            packages: List of package names to install.

        Returns:
            `ExecutionResult` with installation output.
        """
        if not self.sandbox:
            return ExecutionResult(
                stdout="",
                stderr="Sandbox not created",
                exit_code=1,
                success=False,
                error_message="Sandbox not created",
            )

        if not packages:
            return ExecutionResult(
                stdout="No packages to install",
                stderr="",
                exit_code=0,
                success=True,
            )

        package_str = " ".join(packages)
        cmd = f"pip install {package_str}"

        logger.info("Installing packages: %s", packages)
        try:
            response = self.sandbox.process.exec(cmd)
            stdout = str(response.result) if response.result else ""
            logger.debug("Package install output: %s", stdout)
            logger.info("Packages installed successfully")
            return ExecutionResult(
                stdout=stdout,
                stderr="",
                exit_code=0,
                success=True,
            )
        except Exception as e:
            logger.exception("Package installation failed")
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                success=False,
                error_message=str(e),
            )

    def set_env_vars(self, env_vars: dict[str, str]) -> None:
        """Set environment variables in the sandbox.

        Args:
            env_vars: Dictionary of environment variable names and values.
        """
        if not self.sandbox or not env_vars:
            return

        # Export environment variables (best effort)
        for key, value in env_vars.items():
            with contextlib.suppress(Exception):
                self.sandbox.process.exec(f"export {key}='{value}'")

    def execute_code(
        self,
        code: str,
        env_vars: dict[str, str] | None = None,
        timeout: int = 60,
    ) -> ExecutionResult:
        """Execute Python code in the sandbox.

        Args:
            code: Python code to execute.
            env_vars: Optional environment variables to set.
            timeout: Timeout in seconds.

        Returns:
            `ExecutionResult` with execution output.
        """
        if not self.sandbox:
            return ExecutionResult(
                stdout="",
                stderr="Sandbox not created",
                exit_code=1,
                success=False,
                error_message="Sandbox not created",
            )

        # Set environment variables if provided
        if env_vars:
            self.set_env_vars(env_vars)

        # Write code to a file
        code_escaped = code.replace("'", "'\\''")
        write_cmd = f"echo '{code_escaped}' > /tmp/mre_code.py"

        logger.debug("Writing code to /tmp/mre_code.py")
        try:
            self.sandbox.process.exec(write_cmd)
            logger.debug("Code written successfully")
        except Exception as e:
            logger.exception("Failed to write code to sandbox")
            return ExecutionResult(
                stdout="",
                stderr=f"Failed to write code: {e}",
                exit_code=1,
                success=False,
                error_message=str(e),
            )

        # Build execution command with env vars
        env_prefix = ""
        if env_vars:
            env_parts = [f"{k}='{v}'" for k, v in env_vars.items()]
            env_prefix = " ".join(env_parts) + " "

        exec_cmd = f"{env_prefix}python /tmp/mre_code.py"

        logger.info("Executing code in sandbox (timeout=%ds)...", timeout)
        try:
            response = self.sandbox.process.exec(exec_cmd, timeout=timeout)

            # Parse response - structure may vary by SDK version
            result_str = str(response.result) if response.result else ""

            # Log the output for observability
            logger.info("Execution completed")
            logger.debug("stdout: %s", result_str)

            # Check for Python errors in output
            # (process succeeded but Python code may have failed)
            has_error = any(
                err in result_str
                for err in ("Error:", "Traceback (most recent call last):")
            )
            if has_error:
                logger.warning("Python error detected in output:\n%s", result_str)

            return ExecutionResult(
                stdout=result_str,
                stderr="",
                exit_code=0,
                success=True,
            )
        except Exception as e:
            error_str = str(e)

            # Check if it's a timeout
            if "timeout" in error_str.lower():
                logger.warning("Execution timed out after %ds", timeout)
                return ExecutionResult(
                    stdout="",
                    stderr=f"Execution timed out after {timeout} seconds",
                    exit_code=124,
                    success=False,
                    error_message="Timeout",
                )

            # Check if it's a Python error (which is expected for bug reports)
            # The error output is actually useful information
            logger.exception("Execution failed")
            return ExecutionResult(
                stdout="",
                stderr=error_str,
                exit_code=1,
                success=False,
                error_message=error_str,
            )

    def cleanup(self) -> None:
        """Clean up and delete the sandbox."""
        if self.sandbox:
            logger.info("Cleaning up sandbox...")
            try:
                # Try to delete the sandbox if the method exists
                if hasattr(self.sandbox, "delete"):
                    self.sandbox.delete()
                elif hasattr(self.daytona, "delete"):
                    self.daytona.delete(self.sandbox)
                logger.info("Sandbox cleaned up successfully")
            except Exception as e:
                logger.warning("Sandbox cleanup failed (best effort): %s", e)
            finally:
                self.sandbox = None

    def __enter__(self) -> "DaytonaSandbox":
        """Context manager entry."""
        self.create()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.cleanup()


def create_sandbox(
    api_key: str | None = None,
    api_url: str | None = None,
) -> DaytonaSandbox:
    """Create a new Daytona sandbox instance.

    Args:
        api_key: Optional Daytona API key.
        api_url: Optional Daytona API URL.

    Returns:
        A `DaytonaSandbox` instance.
    """
    sandbox = DaytonaSandbox(api_key=api_key, api_url=api_url)
    sandbox.create()
    return sandbox


def execute_in_sandbox(
    code: str,
    packages: list[str] | None = None,
    env_vars: dict[str, str] | None = None,
    api_key: str | None = None,
    api_url: str | None = None,
    timeout: int = 60,
) -> ExecutionResult:
    """Execute code in a Daytona sandbox (convenience function).

    Creates a sandbox, installs packages, executes code, and cleans up.

    Args:
        code: Python code to execute.
        packages: Optional packages to install.
        env_vars: Optional environment variables.
        api_key: Optional Daytona API key.
        api_url: Optional Daytona API URL.
        timeout: Execution timeout in seconds.

    Returns:
        `ExecutionResult` with execution output.
    """
    logger.info(
        "Starting sandbox execution (packages=%s, timeout=%ds)",
        packages or [],
        timeout,
    )
    try:
        with DaytonaSandbox(api_key=api_key, api_url=api_url) as sandbox:
            # Install packages if specified
            if packages:
                install_result = sandbox.install_packages(packages)
                if not install_result.success:
                    logger.error("Package installation failed, aborting execution")
                    return install_result

            # Execute code
            result = sandbox.execute_code(code, env_vars=env_vars, timeout=timeout)
            logger.info(
                "Sandbox execution finished (success=%s, exit_code=%d)",
                result.success,
                result.exit_code,
            )
            return result
    except ImportError:
        logger.warning("Daytona SDK not available")
        return ExecutionResult(
            stdout="",
            stderr="Daytona SDK not installed",
            exit_code=1,
            success=False,
            error_message="Daytona SDK not available",
        )
    except Exception as e:
        logger.exception("Unexpected error during sandbox execution")
        return ExecutionResult(
            stdout="",
            stderr=str(e),
            exit_code=1,
            success=False,
            error_message=str(e),
        )
