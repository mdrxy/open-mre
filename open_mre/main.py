"""CLI entry point for open-MRE."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage

from open_mre.coordinator import create_mre_coordinator


def _print_message_progress(message: Any) -> None:
    """Print clean progress updates from message content blocks.

    Args:
        message: LangChain message object with content_blocks.
    """
    # Skip user input
    if message.__class__.__name__ == "HumanMessage":
        return

    if hasattr(message, "content_blocks"):
        for block in message.content_blocks:
            if block.get("type") == "text":
                text = block.get("text", "").strip()
                if text:
                    print(f"→ {text}")
                    print()
            elif block.get("type") == "tool_use":
                tool_name = block.get("name", "unknown")
                print(f"🔧 Calling tool: {tool_name}")
                print()


def _extract_and_save_files(final_state: dict[str, Any], output_dir: Path) -> int:
    """Extract files from agent state and save to local filesystem.

    Args:
        final_state: Final state from the coordinator agent execution.
        output_dir: Directory to save extracted files.

    Returns:
        Number of files saved.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    files_saved = 0

    # DeepAgents stores files in the "files" key of the state
    if "files" not in final_state:
        return files_saved

    files_state = final_state["files"]

    # Files are stored with their paths as keys (e.g., "validation_report.md")
    for file_path, file_content in files_state.items():
        # Skip the original issue.md to avoid confusion
        if file_path in {"issue.md", "/issue.md"}:
            continue

        clean_path = file_path.lstrip("/")
        output_file = output_dir / clean_path
        output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Convert non-string content to appropriate format
            content_to_write: str
            if isinstance(file_content, (dict, list)):
                # Convert JSON-serializable objects to formatted JSON strings
                content_to_write = json.dumps(file_content, indent=2)
            elif not isinstance(file_content, str):
                # Convert other types to strings
                content_to_write = str(file_content)
            else:
                content_to_write = file_content

            output_file.write_text(content_to_write)
            print(f"✓ Saved: {output_file}")
            files_saved += 1
        except Exception as e:
            print(f"⚠ Failed to save {clean_path}: {e}")

    return files_saved


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="open-mre",
        description="Validates a bug report and attempts to reproduce the issue.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  open-mre bug_report.md
  open-mre bug_report.md -e OPENAI_API_KEY ANTHROPIC_API_KEY
  open-mre bug_report.md --env DATABASE_URL API_TOKEN
        """,
    )
    parser.add_argument(
        "issue_file",
        type=Path,
        help="Path to the bug report markdown file",
    )
    parser.add_argument(
        "-e",
        "--env",
        nargs="+",
        metavar="VAR",
        help=(
            "Environment variable names to pass from host to sandbox "
            "(e.g., -e OPENAI_API_KEY)"
        ),
    )

    args = parser.parse_args()

    issue_path: Path = args.issue_file
    if not issue_path.exists():
        print(f"Error: File not found: `{issue_path}`")
        sys.exit(1)

    # Read the issue file content
    try:
        issue_content = issue_path.read_text()
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    # Collect and set environment variables for sandbox execution
    if args.env:
        captured_count = 0
        for var_name in args.env:
            value = os.getenv(var_name)
            if value is None:
                print(f"Warning: Environment variable '{var_name}' not found in host")
            else:
                # Set with SANDBOX_ENV_ prefix so executor can find them
                os.environ[f"SANDBOX_ENV_{var_name}"] = value
                captured_count += 1
                print(f"✓ Captured env var: {var_name}")

        if captured_count > 0:
            print(f"✓ {captured_count} env var(s) will be passed to sandbox")
            print()

    print(f"🔍 Validating issue from: `{issue_path}`")
    print()

    # Create coordinator agent
    coordinator = create_mre_coordinator()

    # Run validation - pass content instead of path
    task = f"""Validate the following bug report and follow the full MRE validation
workflow.

# Bug Report

{issue_content}
"""

    try:
        final_state = None
        last_message_count = 0

        # Stream events to show progress
        for event in coordinator.stream(
            {"messages": [HumanMessage(content=task)]},
            stream_mode="values",  # Use "values" to get full state
        ):
            # Store the final state
            final_state = event

            # Print progress for new messages only
            if "messages" in event:
                messages = event["messages"]
                # Only show new messages since last event
                for message in messages[last_message_count:]:
                    _print_message_progress(message)
                last_message_count = len(messages)

        # Print final result
        if final_state and "messages" in final_state:
            final_message = final_state["messages"][-1]
            print("=" * 80)
            print("VALIDATION COMPLETE")
            print("=" * 80)

            # Extract text from content_blocks
            if hasattr(final_message, "content_blocks"):
                for block in final_message.content_blocks:
                    if block.get("type") == "text":
                        print(block.get("text", ""))
            else:
                # Fallback to raw content if content_blocks not available
                print(final_message.content)
            print()

        if final_state:
            output_dir = Path("outputs")
            files_saved = _extract_and_save_files(final_state, output_dir)

            if files_saved > 0:
                print()
                print(f"✓ {files_saved} file(s) saved to: {output_dir}/")
            else:
                print()
                print("⚠ No output files found in agent state")

    except Exception as e:
        print(f"Error during validation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
