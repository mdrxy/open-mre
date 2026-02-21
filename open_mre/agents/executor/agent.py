"""Executor agent subgraph.

This agent prepares code for execution, runs it in a Daytona sandbox,
and captures the results.
"""

from typing import Annotated, Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from open_mre.agents.executor.schemas import ExecutorInput, ExecutorOutput
from open_mre.prompts import EXECUTOR_SYSTEM_PROMPT
from open_mre.state import PackageInfo
from open_mre.tools.daytona_sandbox import (
    DAYTONA_AVAILABLE,
    ExecutionResult,
    execute_in_sandbox,
)


class AgentState(TypedDict):
    """Internal state for the executor agent."""

    messages: Annotated[list[BaseMessage], add_messages]
    code_snippets: list[str]
    packages: list[PackageInfo]
    approved_api_keys: dict[str, str]
    expected_behavior: str | None
    actual_behavior: str | None

    # Results
    execution_output: str | None
    execution_error: str | None
    hydrated_code: str | None
    execution_notes: list[str]


def create_executor_agent() -> CompiledStateGraph[Any, Any]:
    """Create the executor agent subgraph.

    Returns:
        A compiled `StateGraph` that executes code in a sandbox.
    """
    model = init_chat_model(model="claude-sonnet-4-5")

    def hydrate_code(state: AgentState) -> dict[str, Any]:
        """Prepare the code for execution by adding necessary boilerplate."""
        code_snippets = state.get("code_snippets", [])
        packages = state.get("packages", [])
        expected_behavior = state.get("expected_behavior")
        actual_behavior = state.get("actual_behavior")

        if not code_snippets:
            return {
                "hydrated_code": None,
                "execution_notes": ["No code snippets to execute"],
            }

        # Combine code snippets
        combined_code = "\n\n".join(code_snippets)

        # Get package names for context
        package_names = [p["name"] for p in packages if p.get("name")]

        system_message = SystemMessage(content=EXECUTOR_SYSTEM_PROMPT)
        human_message = HumanMessage(
            content=f"""Prepare this code for execution in a sandboxed environment.

The code should:
1. Have all necessary imports
2. Be executable as a standalone script
3. NOT have the reported bug fixed - we want to reproduce the issue
4. Have print statements to show output

Original Code:
```python
{combined_code}
```

Known packages being used: {package_names or "Unknown"}
Expected behavior: {expected_behavior or "Not specified"}
Actual behavior: {actual_behavior or "Not specified"}

Return ONLY the hydrated Python code, nothing else. Do not include markdown fences."""
        )

        response = model.invoke(input=[system_message, human_message])
        # TODO: use .content_blocks?
        hydrated_code = response.content if isinstance(response.content, str) else ""

        # Clean up the response - remove any markdown fences if present
        hydrated_code = hydrated_code.strip()
        hydrated_code = hydrated_code.removeprefix("```python")
        hydrated_code = hydrated_code.removeprefix("```")
        hydrated_code = hydrated_code.removesuffix("```")
        hydrated_code = hydrated_code.strip()

        return {
            "hydrated_code": hydrated_code,
            "execution_notes": ["Code hydrated with necessary imports and boilerplate"],
        }

    def execute_code(state: AgentState) -> dict[str, Any]:
        """Execute the hydrated code in a Daytona sandbox."""
        hydrated_code = state.get("hydrated_code")
        packages = state.get("packages", [])
        approved_api_keys = state.get("approved_api_keys", {})
        execution_notes = list(state.get("execution_notes", []))

        if not hydrated_code:
            return {
                "execution_output": None,
                "execution_error": "No code to execute",
                "execution_notes": [*execution_notes, "No code to execute"],
            }

        # Check if Daytona is available
        if not DAYTONA_AVAILABLE:
            return {
                "execution_output": None,
                "execution_error": "Daytona SDK not available - cannot execute code",
                "execution_notes": [
                    *execution_notes,
                    "Daytona SDK not installed - skipping execution",
                ],
            }

        # Prepare package list for installation
        packages_to_install: list[str] = []
        for pkg in packages:
            name = pkg.get("name")
            version = pkg.get("user_version") or pkg.get("latest_version")
            if name:
                if version:
                    packages_to_install.append(f"{name}=={version}")
                else:
                    packages_to_install.append(name)

        # Always include core langchain packages
        # TODO: hydrate with more?
        core_packages = ["langchain", "langchain-core"]
        for core_pkg in core_packages:
            if core_pkg not in [p.split("==")[0] for p in packages_to_install]:
                packages_to_install.append(core_pkg)

        execution_notes.append(f"Installing packages: {packages_to_install}")

        # Execute in sandbox
        try:
            result: ExecutionResult = execute_in_sandbox(
                code=hydrated_code,
                packages=packages_to_install,
                env_vars=approved_api_keys,
                timeout=120,  # 2 minute timeout
            )

            if not result.success:
                execution_notes.append(f"Execution failed: {result.error_message}")
                return {
                    "execution_output": result.stdout or None,
                    "execution_error": result.stderr or result.error_message,
                    "execution_notes": execution_notes,
                }
        except Exception as e:
            execution_notes.append(f"Execution error: {e}")
            return {
                "execution_output": None,
                "execution_error": str(e),
                "execution_notes": execution_notes,
            }
        else:
            execution_notes.append("Code executed successfully")
            return {
                "execution_output": result.stdout,
                "execution_error": None,
                "execution_notes": execution_notes,
            }

    builder = StateGraph(AgentState)
    builder.add_node("hydrate_code", hydrate_code)
    builder.add_node("execute_code", execute_code)
    builder.add_edge(START, "hydrate_code")
    builder.add_edge("hydrate_code", "execute_code")
    builder.add_edge("execute_code", END)

    return builder.compile()


def invoke_executor(
    agent: CompiledStateGraph[Any, Any], input_data: ExecutorInput
) -> ExecutorOutput:
    """Invoke the executor agent and return structured output.

    Args:
        agent: The compiled executor agent.
        input_data: The input containing code snippets and execution context.

    Returns:
        Structured output with execution results.
    """
    result = agent.invoke(
        input={
            "code_snippets": input_data.get("code_snippets", []),
            "packages": input_data.get("packages", []),
            "approved_api_keys": input_data.get("approved_api_keys", {}),
            "expected_behavior": input_data.get("expected_behavior"),
            "actual_behavior": input_data.get("actual_behavior"),
        }
    )

    return ExecutorOutput(
        execution_output=result.get("execution_output"),
        execution_error=result.get("execution_error"),
        hydrated_code=result.get("hydrated_code"),
        execution_notes=result.get("execution_notes", []),
    )
