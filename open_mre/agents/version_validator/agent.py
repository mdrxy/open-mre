"""Version validator agent subgraph.

Analyzes inbound issues to extract and validate version information for Python and
LangChain-related packages.
"""

from typing import Annotated, Any, Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from open_mre.agents.version_validator.schemas import (
    VersionValidatorInput,
    VersionValidatorOutput,
)
from open_mre.prompts import VERSION_VALIDATOR_SYSTEM_PROMPT
from open_mre.state import PackageInfo
from open_mre.tools import check_pypi_version


class AgentState(TypedDict):
    """Internal state for the version validator agent."""

    messages: Annotated[list[BaseMessage], add_messages]
    issue_content: str

    # Results to be extracted
    python_version: str | None
    packages: list[PackageInfo]
    version_notes: list[str]
    draft_comment: str | None
    should_terminate: bool


def create_version_validator_agent() -> CompiledStateGraph[Any, Any]:
    """Create the version validator agent subgraph.

    Returns:
        A compiled `StateGraph` that validates package versions.
    """
    model = init_chat_model(model="claude-sonnet-4-5")
    tools = [check_pypi_version]
    model_with_tools = model.bind_tools(tools=tools)

    def call_model(state: AgentState) -> dict[str, Any]:
        """Call the model to analyze the issue or continue tool loop."""
        messages = state["messages"]
        response = model_with_tools.invoke(input=messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> Literal["tools", "extract_results"]:
        """Determine if we should continue with tools or extract results."""
        messages = state["messages"]
        last_message = messages[-1]

        # If the model called tools, continue to tool node
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"

        # Otherwise, extract results from the conversation
        return "extract_results"

    def extract_results(state: AgentState) -> dict[str, Any]:
        """Extract structured results from the conversation."""
        # TODO: migrate to use provider (native) structured output
        #       Is this a case for middleware?
        messages = state["messages"]

        extraction_prompt = """Based on the analysis above, provide a summary:

1. Python version found (or "not specified" if none)
2. List of packages found with their versions and whether they're outdated
3. Any notes about missing version information
4. If any packages are outdated, draft a polite comment asking the user to upgrade

Respond in this exact format:
PYTHON_VERSION: <version or "not specified">
PACKAGES: <package1>:<user_version>:<latest_version>:<outdated>, <package2>:...
NOTES: <note1>; <note2>; ...
DRAFT_COMMENT: <comment or "none">
SHOULD_TERMINATE: <true if outdated packages found, false otherwise>"""

        extraction_model = init_chat_model(model="claude-sonnet-4-5")
        extraction_messages = [*messages, HumanMessage(content=extraction_prompt)]

        response = extraction_model.invoke(input=extraction_messages)
        # TODO: migrate to use .content_blocks?
        content = response.content if isinstance(response.content, str) else ""
        lines = content.strip().split("\n")

        python_version = None
        packages: list[PackageInfo] = []
        version_notes: list[str] = []
        draft_comment = None
        should_terminate = False

        for raw_line in lines:
            line = raw_line.strip()
            if line.startswith("PYTHON_VERSION:"):
                value = line.replace("PYTHON_VERSION:", "").strip()
                python_version = None if value.lower() == "not specified" else value
            elif line.startswith("PACKAGES:"):
                pkg_str = line.replace("PACKAGES:", "").strip()
                if pkg_str and pkg_str.lower() != "none":
                    for pkg in pkg_str.split(","):
                        parts = pkg.strip().split(":")
                        if len(parts) >= 4:
                            packages.append(
                                PackageInfo(
                                    name=parts[0].strip(),
                                    user_version=parts[1].strip() or None,
                                    latest_version=parts[2].strip() or None,
                                    is_outdated=parts[3].strip().lower() == "true",
                                )
                            )
            elif line.startswith("NOTES:"):
                notes_str = line.replace("NOTES:", "").strip()
                if notes_str and notes_str.lower() != "none":
                    version_notes = [
                        n.strip() for n in notes_str.split(";") if n.strip()
                    ]
            elif line.startswith("DRAFT_COMMENT:"):
                comment = line.replace("DRAFT_COMMENT:", "").strip()
                draft_comment = None if comment.lower() == "none" else comment
            elif line.startswith("SHOULD_TERMINATE:"):
                value = line.replace("SHOULD_TERMINATE:", "").strip().lower()
                should_terminate = value == "true"

        return {
            "python_version": python_version,
            "packages": packages,
            "version_notes": version_notes,
            "draft_comment": draft_comment,
            "should_terminate": should_terminate,
        }

    def prepare_prompt(state: AgentState) -> dict[str, Any]:
        """Prepare the initial prompt from the issue content."""
        issue_content = state["issue_content"]

        system_message = SystemMessage(content=VERSION_VALIDATOR_SYSTEM_PROMPT)
        human_message = HumanMessage(
            content=f"""Analyze this GitHub issue and extract version information.
Use the check_pypi_version tool to verify if LangChain packages are on their
latest versions.

GitHub Issue:
---
{issue_content}
---

Extract:
1. Python version (if mentioned)
2. All LangChain-related packages and their versions
3. Verify each package version against PyPI"""
        )

        return {
            "messages": [system_message, human_message],
            "python_version": None,
            "packages": [],
            "version_notes": [],
            "draft_comment": None,
            "should_terminate": False,
        }

    builder = StateGraph(AgentState)
    builder.add_node("prepare_prompt", prepare_prompt)
    builder.add_node("call_model", call_model)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("extract_results", extract_results)
    builder.add_edge(START, "prepare_prompt")
    builder.add_edge("prepare_prompt", "call_model")
    builder.add_conditional_edges("call_model", should_continue)
    builder.add_edge("tools", "call_model")
    builder.add_edge("extract_results", END)

    return builder.compile()


def invoke_version_validator(
    agent: CompiledStateGraph[Any, Any], input_data: VersionValidatorInput
) -> VersionValidatorOutput:
    """Invoke the version validator agent and return structured output.

    Args:
        agent: The compiled version validator agent.
        input_data: The input containing the issue content.

    Returns:
        Structured output with version validation results.
    """
    result = agent.invoke(input={"issue_content": input_data["issue_content"]})

    return VersionValidatorOutput(
        python_version=result.get("python_version"),
        packages=result.get("packages", []),
        version_notes=result.get("version_notes", []),
        draft_comment=result.get("draft_comment"),
        should_terminate=result.get("should_terminate", False),
    )
