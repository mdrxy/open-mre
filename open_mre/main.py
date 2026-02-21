"""CLI entry point."""

import argparse
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig

load_dotenv()
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from open_mre.coordinator import create_coordinator, create_default_state


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Command-line arguments. If `None`, uses `sys.argv`.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog="open-mre",
        description="Validate Minimal Reproducible Examples from GitHub issues.",
    )

    parser.add_argument(
        "issue_file",
        type=Path,
        help="Path to the GitHub issue markdown file",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path(),
        help="Directory for output files (defaults to current directory)",
    )

    parser.add_argument(
        "--no-execute",
        action="store_true",
        help="Skip code execution (analysis only)",
    )

    # TODO: Pass option to run_validation (currently default is False)
    parser.add_argument(
        "--auto-approve-keys",
        action="store_true",
        help="Automatically approve API key usage (use with caution)",
    )

    return parser.parse_args(argv)


def prompt_for_api_keys(providers: list[str]) -> dict[str, str]:
    """Prompt user to provide API keys for detected providers.

    Args:
        providers: List of detected API providers.

    Returns:
        Dictionary mapping environment variable names to values.
    """
    print("\n" + "=" * 60)
    print("API KEY APPROVAL REQUIRED")
    print("=" * 60)
    print(f"\nThe MRE requires API keys for: {', '.join(providers)}")
    print("\nOptions:")
    print("  1. Provide API keys (will be used in sandbox only)")
    print("  2. Skip execution (continue with analysis only)")
    print()

    choice = input("Enter choice (1 or 2): ").strip()

    if choice != "1":
        return {}

    env_vars: dict[str, str] = {}

    # Map providers to their environment variable names
    provider_env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "azure": "AZURE_OPENAI_API_KEY",
        "cohere": "COHERE_API_KEY",
        "huggingface": "HUGGINGFACE_API_KEY",
        "aws": "AWS_ACCESS_KEY_ID",
        "mistral": "MISTRAL_API_KEY",
        "groq": "GROQ_API_KEY",
    }

    for provider in providers:
        provider_lower = provider.lower()
        env_var = provider_env_map.get(provider_lower, f"{provider.upper()}_API_KEY")

        print(f"\nEnter {env_var} (or press Enter to skip):")
        value = input().strip()
        if value:
            env_vars[env_var] = value

    return env_vars


def run_validation(
    issue_content: str,
    *,
    auto_approve_keys: bool = False,
    issue_file: Path | None = None,
) -> dict[str, Any]:
    """Run the validation workflow.

    Args:
        issue_content: The raw markdown content of the issue.
        auto_approve_keys: If `True`, skip API key approval prompts.
        issue_file: Path to the issue file (for metadata tracking).

    Returns:
        Final state dictionary from the coordinator graph.
    """
    checkpointer = InMemorySaver()
    coordinator = create_coordinator(checkpointer=checkpointer)
    initial_state = create_default_state(issue_content=issue_content)

    # thread_id is required by the checkpointer for HITL interrupt/resume flow
    # metadata is passed to LangSmith for observability
    metadata: dict[str, Any] = {}
    if issue_file is not None:
        metadata["issue_file"] = str(issue_file)

    config: RunnableConfig = {
        "configurable": {"thread_id": str(uuid.uuid4())},
        "metadata": metadata,
    }

    print("\nStarting MRE validation...")

    result = coordinator.invoke(initial_state, config)

    # Handle HITL interrupts
    while True:
        # Check if we're at an interrupt
        state = coordinator.get_state(config)

        if not state.tasks:
            # No pending tasks, we're done
            break

        # Check for interrupt
        for task in state.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                interrupt_data = task.interrupts[0].value

                if interrupt_data.get("type") == "api_key_approval":
                    providers = interrupt_data.get("providers", [])

                    if auto_approve_keys:
                        # Auto-approve with empty keys (will likely fail execution)
                        print("\nAuto-approving API key usage (no keys provided)")
                        approval = {"approved": True, "env_vars": {}}
                    else:
                        env_vars = prompt_for_api_keys(providers)
                        if env_vars:
                            approval = {"approved": True, "env_vars": env_vars}
                        else:
                            approval = {"approved": False, "reason": "User declined"}

                    # Resume with approval response
                    result = coordinator.invoke(
                        Command(resume=approval),
                        config,
                    )
                    break
        else:
            # No interrupts found, we're done
            break

    return result


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    """Write validation outputs to files.

    Args:
        result: Final state from the coordinator.
        output_dir: Directory to write output files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write validation report
    validation_report = result.get("validation_report")
    if validation_report:
        report_path = output_dir / "validation_report.md"
        report_path.write_text(validation_report)
        print(f"\nValidation report written to: {report_path}")

    # Write reproduction script
    reproduction_script = result.get("reproduction_script")
    if reproduction_script:
        script_path = output_dir / "reproduction.py"
        script_path.write_text(reproduction_script)
        print(f"Reproduction script written to: {script_path}")

    # Write draft comments
    draft_comments = result.get("draft_comments", [])
    if draft_comments:
        comments_path = output_dir / "draft_comments.md"
        content = "# Draft Comments for GitHub Issue\n\n"
        for i, comment in enumerate(draft_comments, 1):
            content += f"## Comment {i}\n\n{comment}\n\n---\n\n"
        comments_path.write_text(content)
        print(f"Draft comments written to: {comments_path}")


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments. If `None`, uses `sys.argv`.

    Returns:
        Exit code (`0`: success, non-zero: failure).
    """
    args = parse_args(argv=argv)

    issue_file: Path = args.issue_file
    if not issue_file.exists():
        print(f"Error: Issue file not found: {issue_file}", file=sys.stderr)
        return 1

    if not args.no_execute and not os.environ.get("DAYTONA_API_KEY"):
        print(
            "Error: DAYTONA_API_KEY environment variable is required for code "
            "execution.\nUse --no-execute to skip execution, or set the "
            "DAYTONA_API_KEY environment variable.",
            file=sys.stderr,
        )
        return 1

    issue_content = issue_file.read_text()
    print(f"Loaded issue from: {issue_file}")

    try:
        result = run_validation(
            issue_content=issue_content,
            issue_file=issue_file,
        )
    except KeyboardInterrupt:
        print("Validation interrupted by user.")
        return 130
    except Exception as e:
        print(f"Error during validation: {e}", file=sys.stderr)
        return 1

    # Write outputs
    write_outputs(result, args.output_dir)

    # Print summary
    execution_ran = result.get("execution_output") or result.get("execution_error")
    termination_reason = result.get("termination_reason")

    if execution_ran:
        if result.get("execution_error"):
            print("VALIDATION FAILED")
            print(f"Execution error: {result['execution_error']}")
        else:
            print("VALIDATION COMPLETE")
    elif termination_reason:
        print(f"VALIDATION INCOMPLETE: {termination_reason}")
    else:
        print("ANALYSIS COMPLETE (no code execution!)")

    draft_count = len(result.get("draft_comments", []))
    if draft_count:
        print(f"\n{draft_count} draft comment(s) pending review")

    return 0


if __name__ == "__main__":
    sys.exit(main())
