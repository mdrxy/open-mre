"""Report generator agent subgraph.

This agent generates a validation report and reproduction script
based on the analysis and execution results.
"""

from typing import Annotated, Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from open_mre.agents.report_generator.schemas import (
    ReportGeneratorInput,
    ReportGeneratorOutput,
)
from open_mre.prompts import REPORT_GENERATOR_SYSTEM_PROMPT
from open_mre.state import PackageInfo


class AgentState(TypedDict):
    """Internal state for the report generator agent."""

    messages: Annotated[list[BaseMessage], add_messages]
    issue_content: str
    python_version: str | None
    packages: list[PackageInfo]
    version_notes: list[str]
    code_snippets: list[str]
    extraction_notes: list[str]
    expected_behavior: str | None
    actual_behavior: str | None
    analysis_notes: list[str]
    execution_output: str | None
    execution_error: str | None
    hydrated_code: str | None
    draft_comments: list[str]
    termination_reason: str | None

    # Results
    validation_report: str
    reproduction_script: str | None


def create_report_generator_agent() -> CompiledStateGraph[Any, Any]:
    """Create the report generator agent subgraph.

    Returns:
        A compiled `StateGraph` that generates validation reports.
    """
    model = init_chat_model(model="claude-sonnet-4-5")

    def generate_report(state: AgentState) -> dict[str, Any]:
        """Generate the validation report and reproduction script."""
        # Gather all information
        issue_content = state.get("issue_content", "")
        python_version = state.get("python_version")
        packages = state.get("packages", [])
        version_notes = state.get("version_notes", [])
        code_snippets = state.get("code_snippets", [])
        extraction_notes = state.get("extraction_notes", [])
        expected_behavior = state.get("expected_behavior")
        actual_behavior = state.get("actual_behavior")
        analysis_notes = state.get("analysis_notes", [])
        execution_output = state.get("execution_output")
        execution_error = state.get("execution_error")
        hydrated_code = state.get("hydrated_code")
        draft_comments = state.get("draft_comments", [])
        termination_reason = state.get("termination_reason")

        # Determine execution status
        if termination_reason:
            execution_status = f"Not Executed ({termination_reason})"
        elif execution_output is not None:
            execution_status = "Success"
        elif execution_error is not None:
            execution_status = "Error"
        else:
            execution_status = "Not Executed"

        # Format package information
        package_info = []
        for pkg in packages:
            name = pkg.get("name", "Unknown")
            user_ver = pkg.get("user_version", "not specified")
            latest_ver = pkg.get("latest_version", "unknown")
            is_outdated = pkg.get("is_outdated", False)
            status = " (OUTDATED)" if is_outdated else ""
            info_line = f"- {name}: {user_ver} (latest: {latest_ver}){status}"
            package_info.append(info_line)

        package_str = (
            "\n".join(package_info) if package_info else "- No packages detected"
        )

        # Format notes
        all_notes = version_notes + extraction_notes + analysis_notes
        notes_str = "\n".join([f"- {n}" for n in all_notes]) if all_notes else "- None"

        # Format draft comments
        comments_str = (
            "\n\n---\n\n".join(draft_comments) if draft_comments else "None pending"
        )

        # Build context for LLM
        system_message = SystemMessage(content=REPORT_GENERATOR_SYSTEM_PROMPT)
        human_message = HumanMessage(
            content=f"""Generate a validation report for this MRE analysis.

## Original Issue
{issue_content[:2000]}{"..." if len(issue_content) > 2000 else ""}

## Version Information
- Python: {python_version or "not specified"}
{package_str}

## Code Analysis
- Code snippets found: {len(code_snippets)}
- Expected behavior: {expected_behavior or "not specified"}
- Actual behavior: {actual_behavior or "not specified"}

## Execution Results
- Status: {execution_status}
- Output: {execution_output or "None"}
- Error: {execution_error or "None"}

## Analysis Notes
{notes_str}

## Pending Comments for Human Review
{comments_str}

Generate a professional markdown report that summarizes this analysis.
The report should help maintainers quickly understand:
1. What the issue is about
2. Whether it was successfully reproduced
3. What the next steps should be

Keep it concise but thorough."""
        )

        response = model.invoke(input=[system_message, human_message])
        # TODO: use .content_blocks?
        report = response.content if isinstance(response.content, str) else ""

        # Determine if issue was reproduced
        was_reproduced = (
            execution_output is not None
            and execution_error is None
            and not termination_reason
        )

        # Add reproduction status to report
        if was_reproduced:
            report += (
                "\n\n---\n\n**Status: Issue behavior observed in sandbox execution**"
            )
        elif execution_error:
            report += (
                "\n\n---\n\n**Status: Execution produced an error "
                "(may indicate reproduction of the reported issue)**"
            )
        else:
            report += (
                "\n\n---\n\n**Status: Could not reproduce (execution not completed)**"
            )

        # Add draft comments section
        if draft_comments:
            report += "\n\n## Pending Comments for Human Review\n\n"
            for i, comment in enumerate(draft_comments, 1):
                report += f"### Comment {i}\n\n{comment}\n\n"

        return {
            "validation_report": report,
            "reproduction_script": hydrated_code,
        }

    builder = StateGraph(AgentState)
    builder.add_node("generate_report", generate_report)
    builder.add_edge(START, "generate_report")
    builder.add_edge("generate_report", END)

    return builder.compile()


def invoke_report_generator(
    agent: CompiledStateGraph[Any, Any], input_data: ReportGeneratorInput
) -> ReportGeneratorOutput:
    """Invoke the report generator agent and return structured output.

    Args:
        agent: The compiled report generator agent.
        input_data: The input containing all analysis results.

    Returns:
        Structured output with validation report and reproduction script.
    """
    result = agent.invoke(
        input={
            "issue_content": input_data.get("issue_content", ""),
            "python_version": input_data.get("python_version"),
            "packages": input_data.get("packages", []),
            "version_notes": input_data.get("version_notes", []),
            "code_snippets": input_data.get("code_snippets", []),
            "extraction_notes": input_data.get("extraction_notes", []),
            "expected_behavior": input_data.get("expected_behavior"),
            "actual_behavior": input_data.get("actual_behavior"),
            "analysis_notes": input_data.get("analysis_notes", []),
            "execution_output": input_data.get("execution_output"),
            "execution_error": input_data.get("execution_error"),
            "hydrated_code": input_data.get("hydrated_code"),
            "draft_comments": input_data.get("draft_comments", []),
            "termination_reason": input_data.get("termination_reason"),
        }
    )

    return ReportGeneratorOutput(
        validation_report=result.get("validation_report", ""),
        reproduction_script=result.get("reproduction_script"),
    )
