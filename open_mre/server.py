"""LangGraph server entry point.

This module exposes the compiled coordinator graph for the LangGraph local server.
"""

from open_mre.coordinator import create_coordinator

# Module-level compiled graph for LangGraph server
# The server imports this variable directly
# use_default_checkpointer=False because LangGraph server handles persistence
graph = create_coordinator(use_default_checkpointer=False)
