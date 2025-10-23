"""Tests for the coordinator agent."""

from open_mre.coordinator import create_mre_coordinator


def test_create_coordinator() -> None:
    """Test coordinator agent creation."""
    coordinator = create_mre_coordinator()

    assert coordinator is not None
    # Check that subagents are configured
    # This is a basic smoke test to ensure the agent can be created
