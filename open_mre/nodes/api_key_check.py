"""API Key Check node with Human-in-the-Loop interrupt.

This node pauses execution if the code requires API keys and waits
for human approval before continuing.
"""

from typing import Literal

from langgraph.types import Command, interrupt

from open_mre.state import MREValidationState


def api_key_check_node(
    state: MREValidationState,
) -> Command[Literal["executor", "report_generator"]]:
    """Check if API keys are required and get approval if needed.

    This node implements a blocking HITL pattern using LangGraph's interrupt().
    If the code requires API keys to run, it pauses execution and waits for
    human approval. The human can approve (with API keys) or reject.

    Args:
        state: The current MRE validation state.

    Returns:
        A `Command` to route to the executor or `report_generator` node.
    """
    requires_api_keys = state.get("requires_api_keys", False)
    detected_providers = state.get("detected_api_providers", [])

    # If no API keys needed, continue to executor
    if not requires_api_keys:
        return Command(
            goto="executor",
            update={"approved_api_keys": {}},
        )

    # Pause and wait for human approval
    approval = interrupt(
        {
            "type": "api_key_approval",
            "providers": detected_providers,
            "message": (
                f"The code requires API keys for: {', '.join(detected_providers)}. "
                "Do you approve using these API keys for sandbox execution?"
            ),
            "instructions": (
                "To approve, resume with: "
                '{"approved": true, "env_vars": {"PROVIDER_API_KEY": "key_value"}}\n'
                "To reject, resume with: "
                '{"approved": false}'
            ),
        }
    )

    # Process the approval response
    if isinstance(approval, dict) and approval.get("approved"):
        # Extract environment variables from approval
        env_vars = approval.get("env_vars", {})
        return Command(
            goto="executor",
            update={"approved_api_keys": env_vars},
        )
    # Rejected - skip execution and go to report generation
    return Command(
        goto="report_generator",
        update={
            "should_terminate": True,
            "termination_reason": "API key usage not approved by maintainer",
            "approved_api_keys": {},
        },
    )
