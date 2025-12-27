"""Code extractor agent subgraph.

This agent extracts code snippets from inbound issues that could serve as
Minimal Reproducible Examples (MREs).
"""

import re
from typing import Annotated, Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from open_mre.agents.code_extractor.schemas import (
    CodeExtractorInput,
    CodeExtractorOutput,
)
from open_mre.prompts import CODE_EXTRACTOR_SYSTEM_PROMPT


class AgentState(TypedDict):
    """Internal state for the code extractor agent."""

    messages: Annotated[list[BaseMessage], add_messages]
    issue_content: str
    version_notes: list[str]

    # Results
    code_snippets: list[str]
    extraction_notes: list[str]
    draft_comment: str | None
    should_terminate: bool


def extract_fenced_code_blocks(content: str) -> list[str]:
    """Extract fenced code blocks from markdown content.

    Args:
        content: The markdown content to parse.

    Returns:
        List of code snippets found in fenced blocks.
    """
    # Match ```python ... ``` or ``` ... ``` blocks
    pattern = r"```(?:python|py)?\s*\n(.*?)```"
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
    return [match.strip() for match in matches if match.strip()]


def _format_fenced_snippets(snippets: list[str]) -> str:
    """Format fenced snippets for display in LLM prompt.

    Args:
        snippets: List of code snippets.

    Returns:
        Formatted string of code blocks.
    """
    if not snippets:
        return "None found"
    return "\n".join(f"```python\n{s}\n```" for s in snippets)


def create_code_extractor_agent() -> CompiledStateGraph[Any, Any]:
    """Create the code extractor agent subgraph.

    Returns:
        A compiled `StateGraph` that extracts code from issues.
    """
    model = init_chat_model(model="claude-sonnet-4-5")

    def extract_code(state: AgentState) -> dict[str, Any]:
        """Extract code snippets from the issue content."""
        # TODO: migrate to use provider (native) structured output?
        issue_content = state["issue_content"]
        version_notes = state.get("version_notes", [])

        # First, try to extract fenced code blocks directly
        fenced_snippets = extract_fenced_code_blocks(issue_content)

        extraction_notes: list[str] = []
        code_snippets: list[str] = []

        if fenced_snippets:
            code_snippets = fenced_snippets
            extraction_notes.append(
                f"Found {len(fenced_snippets)} fenced code block(s)"
            )
        else:
            extraction_notes.append("No fenced code blocks found")

        # Use LLM to help identify any missed code or provide analysis
        system_message = SystemMessage(content=CODE_EXTRACTOR_SYSTEM_PROMPT)
        human_message = HumanMessage(
            content=f"""Analyze this GitHub issue for code snippets that could be used
to reproduce the reported behavior.

I already found these fenced code blocks:
{_format_fenced_snippets(fenced_snippets)}

GitHub Issue:
---
{issue_content}
---

Please:
1. Identify any additional code that might be in the issue but not properly fenced
2. Note if the code appears to be a complete MRE or if pieces are missing
3. If no code is found at all, indicate that we need to request an MRE

Respond in this format:
ADDITIONAL_CODE: <code if found, or "none">
NOTES: <observations about the code, separated by semicolons>
NEEDS_MRE: <true/false>"""
        )

        response = model.invoke(input=[system_message, human_message])
        # TODO: migrate to use .content_blocks?
        content = response.content if isinstance(response.content, str) else ""

        # Parse the response
        additional_code = None
        needs_mre = False

        for raw_line in content.strip().split("\n"):
            line = raw_line.strip()
            if line.startswith("ADDITIONAL_CODE:"):
                code_part = line.replace("ADDITIONAL_CODE:", "").strip()
                if code_part.lower() != "none" and code_part:
                    additional_code = code_part
            elif line.startswith("NOTES:"):
                notes_str = line.replace("NOTES:", "").strip()
                if notes_str:
                    extraction_notes.extend(
                        [n.strip() for n in notes_str.split(";") if n.strip()]
                    )
            elif line.startswith("NEEDS_MRE:"):
                value = line.replace("NEEDS_MRE:", "").strip().lower()
                needs_mre = value == "true"

        # If LLM found additional code, add it
        if additional_code:
            code_snippets.append(additional_code)
            extraction_notes.append("LLM identified additional unfenced code")

        # Determine if we should terminate and draft a comment
        draft_comment = None
        should_terminate = False

        if not code_snippets or needs_mre:
            should_terminate = True
            # Build draft comment
            comment_parts = [
                "Hi, I'm an automated bot that helps triage issues.",
                "",
                "I noticed you did not provide a minimal reproducible example (MRE) "
                "in your issue. To help maintainers investigate the issue, we need "
                "a code snippet that reproduces the behavior you are reporting.",
                "",
                "Please edit your issue to include a code example.",
            ]

            # Add version-related notes if any
            if version_notes:
                comment_parts.extend(
                    ["", "Additionally:"] + [f"- {note}" for note in version_notes]
                )

            draft_comment = "\n".join(comment_parts)

        return {
            "code_snippets": code_snippets,
            "extraction_notes": extraction_notes,
            "draft_comment": draft_comment,
            "should_terminate": should_terminate,
        }

    builder = StateGraph(AgentState)
    builder.add_node("extract_code", extract_code)
    builder.add_edge(START, "extract_code")
    builder.add_edge("extract_code", END)

    return builder.compile()


def invoke_code_extractor(
    agent: CompiledStateGraph[Any, Any], input_data: CodeExtractorInput
) -> CodeExtractorOutput:
    """Invoke the code extractor agent and return structured output.

    Args:
        agent: The compiled code extractor agent.
        input_data: The input containing the issue content and version notes.

    Returns:
        Structured output with extracted code snippets.
    """
    result = agent.invoke(
        {
            "issue_content": input_data["issue_content"],
            "version_notes": input_data.get("version_notes", []),
        }
    )

    return CodeExtractorOutput(
        code_snippets=result.get("code_snippets", []),
        extraction_notes=result.get("extraction_notes", []),
        draft_comment=result.get("draft_comment"),
        should_terminate=result.get("should_terminate", False),
    )
