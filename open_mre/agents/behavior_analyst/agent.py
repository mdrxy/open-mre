"""Behavior analyst agent subgraph.

This agent analyzes GitHub issues and extracted code to understand the
expected vs actual behavior and detect if API keys are needed.
"""

from typing import Annotated, Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from open_mre.agents.behavior_analyst.schemas import (
    BehaviorAnalystInput,
    BehaviorAnalystOutput,
)
from open_mre.prompts import BEHAVIOR_ANALYST_SYSTEM_PROMPT

# Known API providers and their indicators
API_PROVIDER_PATTERNS = {
    "openai": [
        "langchain_openai",
        "langchain-openai",
        "ChatOpenAI",
        "OPENAI_API_KEY",
        "openai.api_key",
    ],
    "anthropic": [
        "langchain_anthropic",
        "langchain-anthropic",
        "ChatAnthropic",
        "ANTHROPIC_API_KEY",
        "anthropic.api_key",
    ],
    "google": [
        "langchain_google_genai",
        "langchain-google-genai",
        "ChatGoogleGenerativeAI",
        "langchain_google_vertexai",
        "langchain-google-vertexai",
        "ChatVertexAI",
        "GOOGLE_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ],
    "azure": [
        "AzureChatOpenAI",
        "AzureOpenAI",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
    ],
    "cohere": [
        "langchain_cohere",
        "ChatCohere",
        "COHERE_API_KEY",
    ],
    "mistral": [
        "langchain_mistralai",
        "ChatMistralAI",
        "MISTRAL_API_KEY",
    ],
    "fireworks": [
        "langchain_fireworks",
        "ChatFireworks",
        "FIREWORKS_API_KEY",
    ],
}


class AgentState(TypedDict):
    """Internal state for the behavior analyst agent."""

    messages: Annotated[list[BaseMessage], add_messages]
    issue_content: str
    code_snippets: list[str]
    version_notes: list[str]

    # Results
    expected_behavior: str | None
    actual_behavior: str | None
    analysis_notes: list[str]
    requires_api_keys: bool
    detected_api_providers: list[str]
    draft_comment: str | None
    should_terminate: bool


def detect_api_providers(code_snippets: list[str]) -> list[str]:
    """Detect which API providers are used in the code.

    Args:
        code_snippets: List of code snippets to analyze.

    Returns:
        List of detected API provider names.
    """
    detected = set()
    combined_code = "\n".join(code_snippets)

    for provider, patterns in API_PROVIDER_PATTERNS.items():
        for pattern in patterns:
            if pattern in combined_code:
                detected.add(provider)
                break

    return sorted(detected)


def create_behavior_analyst_agent() -> CompiledStateGraph[Any, Any]:
    """Create the behavior analyst agent subgraph.

    Returns:
        A compiled `StateGraph` that analyzes issue behavior.
    """
    # TODO: migrate to use provider (native) structured output?
    model = init_chat_model(model="claude-sonnet-4-5")

    def analyze_behavior(state: AgentState) -> dict[str, Any]:
        """Analyze the issue and code to understand behavior."""
        issue_content = state["issue_content"]
        code_snippets = state.get("code_snippets", [])
        version_notes = state.get("version_notes", [])

        # Detect API providers from code
        detected_providers = detect_api_providers(code_snippets)
        requires_api_keys = len(detected_providers) > 0

        # Use LLM to analyze behavior
        code_block = (
            "\n\n".join([f"```python\n{s}\n```" for s in code_snippets])
            if code_snippets
            else "No code provided"
        )

        system_message = SystemMessage(content=BEHAVIOR_ANALYST_SYSTEM_PROMPT)
        human_message = HumanMessage(
            content=f"""Analyze this GitHub issue and its code to understand:
1. What behavior the user expects
2. What behavior the user is actually observing
3. Any critical missing information

GitHub Issue:
---
{issue_content}
---

Extracted Code:
{code_block}

I've detected these API providers in the code: {detected_providers or "None detected"}

Please respond in this format:
EXPECTED_BEHAVIOR: <what the user expects to happen>
ACTUAL_BEHAVIOR: <what the user reports is happening>
ANALYSIS_NOTES: <observations about the issue, separated by semicolons>
MISSING_INFO: <true if critical info is missing, false otherwise>
MISSING_DETAILS: <what specific info is missing, if any>"""
        )

        response = model.invoke(input=[system_message, human_message])
        # TODO: use .content_blocks?
        content = response.content if isinstance(response.content, str) else ""

        # Parse the response
        expected_behavior = None
        actual_behavior = None
        analysis_notes: list[str] = []
        missing_info = False
        missing_details = None

        for raw_line in content.strip().split("\n"):
            line = raw_line.strip()
            if line.startswith("EXPECTED_BEHAVIOR:"):
                expected_behavior = line.replace("EXPECTED_BEHAVIOR:", "").strip()
                if expected_behavior.lower() in ("none", "not specified", "unclear"):
                    expected_behavior = None
            elif line.startswith("ACTUAL_BEHAVIOR:"):
                actual_behavior = line.replace("ACTUAL_BEHAVIOR:", "").strip()
                if actual_behavior.lower() in ("none", "not specified", "unclear"):
                    actual_behavior = None
            elif line.startswith("ANALYSIS_NOTES:"):
                notes_str = line.replace("ANALYSIS_NOTES:", "").strip()
                if notes_str:
                    analysis_notes = [
                        n.strip() for n in notes_str.split(";") if n.strip()
                    ]
            elif line.startswith("MISSING_INFO:"):
                value = line.replace("MISSING_INFO:", "").strip().lower()
                missing_info = value == "true"
            elif line.startswith("MISSING_DETAILS:"):
                missing_details = line.replace("MISSING_DETAILS:", "").strip()
                if missing_details.lower() in ("none", "n/a"):
                    missing_details = None

        # Add note about API providers
        if detected_providers:
            analysis_notes.append(
                f"Code uses API providers: {', '.join(detected_providers)}"
            )

        # Determine if we should terminate and draft a comment
        draft_comment = None
        should_terminate = False

        if missing_info and missing_details:
            should_terminate = True
            comment_parts = [
                "Hi, I'm an automated bot that helps triage issues.",
                "",
                "I noticed that some critical information is missing from your issue "
                "that prevents us from fully understanding the reported behavior.",
                "",
                f"Specifically: {missing_details}",
                "",
                "Please edit your issue to include this information.",
            ]

            # Add version-related notes if any
            if version_notes:
                comment_parts.extend(
                    ["", "Additionally:"] + [f"- {note}" for note in version_notes]
                )

            draft_comment = "\n".join(comment_parts)

        return {
            "expected_behavior": expected_behavior,
            "actual_behavior": actual_behavior,
            "analysis_notes": analysis_notes,
            "requires_api_keys": requires_api_keys,
            "detected_api_providers": detected_providers,
            "draft_comment": draft_comment,
            "should_terminate": should_terminate,
        }

    builder = StateGraph(AgentState)
    builder.add_node("analyze_behavior", analyze_behavior)
    builder.add_edge(START, "analyze_behavior")
    builder.add_edge("analyze_behavior", END)

    return builder.compile()


def invoke_behavior_analyst(
    agent: CompiledStateGraph[Any, Any], input_data: BehaviorAnalystInput
) -> BehaviorAnalystOutput:
    """Invoke the behavior analyst agent and return structured output.

    Args:
        agent: The compiled behavior analyst agent.
        input_data: The input containing issue content, code, and version notes.

    Returns:
        Structured output with behavior analysis results.
    """
    result = agent.invoke(
        input={
            "issue_content": input_data["issue_content"],
            "code_snippets": input_data.get("code_snippets", []),
            "version_notes": input_data.get("version_notes", []),
        }
    )

    return BehaviorAnalystOutput(
        expected_behavior=result.get("expected_behavior"),
        actual_behavior=result.get("actual_behavior"),
        analysis_notes=result.get("analysis_notes", []),
        requires_api_keys=result.get("requires_api_keys", False),
        detected_api_providers=result.get("detected_api_providers", []),
        draft_comment=result.get("draft_comment"),
        should_terminate=result.get("should_terminate", False),
    )
