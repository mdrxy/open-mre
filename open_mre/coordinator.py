"""Coordinator graph for MRE validation.

This is the parent graph that orchestrates all agent subgraphs
to validate Minimal Reproducible Examples from GitHub issues.
"""

from typing import Any, Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from open_mre.agents.behavior_analyst import create_behavior_analyst_agent
from open_mre.agents.code_extractor import create_code_extractor_agent
from open_mre.agents.executor import create_executor_agent
from open_mre.agents.report_generator import create_report_generator_agent
from open_mre.agents.version_validator import create_version_validator_agent
from open_mre.nodes.api_key_check import api_key_check_node
from open_mre.state import MREValidationState


def create_coordinator(
    checkpointer: InMemorySaver | None = None,
    *,
    use_default_checkpointer: bool = True,
) -> CompiledStateGraph[Any, Any]:
    """Create coordinator graph to orchestrate MRE validation.

    Args:
        checkpointer: Checkpointer for persistence and HITL.

            If `None` and `use_default_checkpointer` is `True`, an `InMemorySaver`
            will be created.

            If `None` and `use_default_checkpointer` is `False`, no checkpointer will be
            used (for LangGraph server deployments).

        use_default_checkpointer: Whether to create a default `InMemorySaver` when no
            checkpointer is provided.

            Set to `False` when deploying to LangGraph server, which handles
            persistence automatically.

    Returns:
        A compiled `StateGraph` that coordinates all agents.
    """
    # Graph
    version_validator = create_version_validator_agent()
    code_extractor = create_code_extractor_agent()
    behavior_analyst = create_behavior_analyst_agent()
    executor = create_executor_agent()
    report_generator = create_report_generator_agent()

    # Define wrapper nodes that invoke subgraphs and map state

    def version_validator_node(state: MREValidationState) -> dict[str, Any]:
        """Invoke the version validator agent.

        Reads issue content and outputs attempted Python version and package detection.

        Args:
            state: Current state.

                Should start as empty, since this is the first node.

        Returns:
            State updates from version validation.
        """
        result = version_validator.invoke(
            input={"issue_content": state["issue_content"]}
        )

        # Build state update
        update: dict[str, Any] = {
            "python_version": result.get("python_version"),
            "packages": result.get("packages", []),
            "version_notes": result.get("version_notes", []),
        }

        # Handle draft comment
        draft_comment = result.get("draft_comment")
        if draft_comment:
            update["draft_comments"] = [draft_comment]

        # Handle termination
        if result.get("should_terminate"):
            update["should_terminate"] = True
            update["termination_reason"] = "Outdated package versions detected"

        return update

    def code_extractor_node(state: MREValidationState) -> dict[str, Any]:
        """Invoke the code extractor agent.

        Attempts to extract code snippets from the issue content.

        Args:
            state: Current state.

        Returns:
            State updates from code extraction.
        """
        result = code_extractor.invoke(
            input={
                "issue_content": state["issue_content"],
                "version_notes": state.get("version_notes", []),
            }
        )

        update = {
            "code_snippets": result.get("code_snippets", []),
            "extraction_notes": result.get("extraction_notes", []),
        }

        draft_comment = result.get("draft_comment")
        if draft_comment:
            update["draft_comments"] = [draft_comment]

        if result.get("should_terminate"):
            update["should_terminate"] = True
            update["termination_reason"] = "No code snippets found"

        return update

    def behavior_analyst_node(state: MREValidationState) -> dict[str, Any]:
        """Invoke the behavior analyst agent.

        Attempt to resolve expected and actual behavior from the issue.

        Args:
            state: Current state.

        Returns:
            State updates from behavior analysis.
        """
        result = behavior_analyst.invoke(
            input={
                "issue_content": state["issue_content"],
                "code_snippets": state.get("code_snippets", []),
                "version_notes": state.get("version_notes", []),
            }
        )

        update = {
            "expected_behavior": result.get("expected_behavior"),
            "actual_behavior": result.get("actual_behavior"),
            "analysis_notes": result.get("analysis_notes", []),
            "requires_api_keys": result.get("requires_api_keys", False),
            "detected_api_providers": result.get("detected_api_providers", []),
        }

        draft_comment = result.get("draft_comment")
        if draft_comment:
            update["draft_comments"] = [draft_comment]

        if result.get("should_terminate"):
            update["should_terminate"] = True
            update["termination_reason"] = "Missing critical information"

        return update

    def executor_node(state: MREValidationState) -> dict[str, Any]:
        """Invoke the executor agent.

        Args:
            state: Current state.

        Returns:
            State updates from code execution.
        """
        result = executor.invoke(
            input={
                "code_snippets": state.get("code_snippets", []),
                "packages": state.get("packages", []),
                "approved_api_keys": state.get("approved_api_keys", {}),
                "expected_behavior": state.get("expected_behavior"),
                "actual_behavior": state.get("actual_behavior"),
            }
        )

        return {
            "execution_output": result.get("execution_output"),
            "execution_error": result.get("execution_error"),
            "hydrated_code": result.get("hydrated_code"),
        }

    def report_generator_node(state: MREValidationState) -> dict[str, Any]:
        """Invoke the report generator agent.

        Args:
            state: Current state.

                At this point, all prior steps have been completed.

        Returns:
            State updates containing the final validation report and reproduction
                script, if generated.
        """
        result = report_generator.invoke(
            input={
                "issue_content": state["issue_content"],
                "python_version": state.get("python_version"),
                "packages": state.get("packages", []),
                "version_notes": state.get("version_notes", []),
                "code_snippets": state.get("code_snippets", []),
                "extraction_notes": state.get("extraction_notes", []),
                "expected_behavior": state.get("expected_behavior"),
                "actual_behavior": state.get("actual_behavior"),
                "analysis_notes": state.get("analysis_notes", []),
                "execution_output": state.get("execution_output"),
                "execution_error": state.get("execution_error"),
                "hydrated_code": state.get("hydrated_code"),
                "draft_comments": state.get("draft_comments", []),
                "termination_reason": state.get("termination_reason"),
            }
        )

        return {
            "validation_report": result.get("validation_report"),
            "reproduction_script": result.get("reproduction_script"),
        }

    # Conditional edges

    def after_version_validator(
        state: MREValidationState,
    ) -> Literal["code_extractor", "report_generator"]:
        """Route after version validation.

        `'code_extractor'` if continuing execution.

        `'report_generator'` to terminate early if outdated package versions were
        detected.
        """
        if state.get("should_terminate"):
            return "report_generator"
        return "code_extractor"

    def after_code_extractor(
        state: MREValidationState,
    ) -> Literal["behavior_analyst", "report_generator"]:
        """Route after code extraction.

        `'behavior_analyst'` if continuing execution.

        `'report_generator'` to terminate early if no code snippets were found.
        """
        if state.get("should_terminate"):
            return "report_generator"
        return "behavior_analyst"

    def after_behavior_analyst(
        state: MREValidationState,
    ) -> Literal["api_key_check", "report_generator"]:
        """Route after behavior analysis.

        `'api_key_check'` if continuing execution.

        `'report_generator'` to terminate early if critical information is missing.
        """
        if state.get("should_terminate"):
            return "report_generator"
        return "api_key_check"

    builder = StateGraph(MREValidationState)
    builder.add_node("version_validator", version_validator_node)
    builder.add_node("code_extractor", code_extractor_node)
    builder.add_node("behavior_analyst", behavior_analyst_node)
    builder.add_node("api_key_check", api_key_check_node)
    builder.add_node("executor", executor_node)
    builder.add_node("report_generator", report_generator_node)
    builder.add_edge(START, "version_validator")
    builder.add_conditional_edges("version_validator", after_version_validator)
    builder.add_conditional_edges("code_extractor", after_code_extractor)
    builder.add_conditional_edges("behavior_analyst", after_behavior_analyst)

    # api_key_check uses Command to route to executor or report_generator
    builder.add_edge("executor", "report_generator")
    builder.add_edge("report_generator", END)

    # Compile with checkpointer for HITL support
    # For LangGraph server deployments, use_default_checkpointer=False
    # since the server handles persistence automatically
    effective_checkpointer = checkpointer
    if effective_checkpointer is None and use_default_checkpointer:
        effective_checkpointer = InMemorySaver()

    return builder.compile(checkpointer=effective_checkpointer)


def create_default_state(issue_content: str) -> MREValidationState:
    """Initialize default initial state for validation.

    Args:
        issue_content: The raw content of the GitHub issue in markdown.

    Returns:
        Initial `MREValidationState` with defaults.
    """
    return MREValidationState(
        issue_content=issue_content,
        python_version=None,
        packages=[],
        version_notes=[],
        code_snippets=[],
        extraction_notes=[],
        expected_behavior=None,
        actual_behavior=None,
        analysis_notes=[],
        requires_api_keys=False,
        detected_api_providers=[],
        approved_api_keys={},
        execution_output=None,
        execution_error=None,
        hydrated_code=None,
        draft_comments=[],
        validation_report=None,
        reproduction_script=None,
        should_terminate=False,
        termination_reason=None,
    )
