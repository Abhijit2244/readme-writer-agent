"""
README Writer Agent - Command Line Interface (CLI)
==================================================
Accepts a local repository location path, inspects codebase architecture and AST entities,
enforces non-destructive safety guardrails (never overwrites existing README by default),
and generates a production-grade publication README with detailed function commentary.

Usage:
  python main.py C:\\path\\to\\your\\repo
  python main.py C:\\path\\to\\your\\repo --force
  python main.py C:\\path\\to\\your\\repo --output custom_readme.md
"""

import sys
import os
import argparse
from typing import Any

# Ensure project root is on Python module search path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import colorama
    colorama.init(autoreset=True)
    Fore: Any = colorama.Fore
    Style: Any = colorama.Style
except ImportError:
    # Minimal ANSI fallback object if colorama is not installed
    class _AnsiFallback:
        CYAN = "\033[36m"
        GREEN = "\033[32m"
        YELLOW = "\033[33m"
        RED = "\033[31m"
        MAGENTA = "\033[35m"
        BLUE = "\033[34m"
        RESET = "\033[0m"
        BRIGHT = "\033[1m"
        RESET_ALL = "\033[0m"

    Fore: Any = _AnsiFallback()
    Style: Any = _AnsiFallback()

from core.agent import ReadmeWriterAgent


def print_banner():
    """
    Renders standard startup banner with agent capabilities and safety notes.
    """
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'=' * 78}")
    print("📝 AUTONOMOUS PRODUCTION README WRITER AGENT")
    print("   Codebase AST Inspection • Functional Commentary • Non-Destructive Guardrails")
    print(f"{'=' * 78}{Style.RESET_ALL}")
    print("  Core Guarantees:")
    print("    • 🛡️ Non-Destructive Safety: Preserves existing READMEs (saves as README.generated.md)")
    print("    • 🔍 Deep AST Parsing: Discovers functions, classes, arguments, and docstrings")
    print("    • 💡 Function Commentary: Explains the operational purpose of every function")
    print("    • 🏗️ Architectural Mermaid: Generates interactive component flowcharts")
    print("    • 📁 Structure Visualizer: Builds an annotated ASCII repository file tree")
    print(f"{Fore.CYAN}{'-' * 78}{Style.RESET_ALL}\n")


def setup_cli_telemetry(agent: ReadmeWriterAgent):
    """
    Connects real-time observer to format and display live agent execution steps.

    Operational Mechanics:
    Intercepts agent lifecycle notifications and prints formatted, color-coded status badges.
    """
    def on_event(event_type: str, data: Any):
        if event_type == "START":
            print(f"  {Fore.MAGENTA}[AGENT]{Style.RESET_ALL} {data}")
        elif event_type == "SCANNING":
            print(f"  {Fore.BLUE}[SCANNER]{Style.RESET_ALL} {data}")
        elif event_type == "SCAN_COMPLETE":
            print(f"  {Fore.BLUE}[SCANNER]{Style.RESET_ALL} Found {data['total_files']} files | Primary: {Fore.GREEN}{data['primary_language']}{Style.RESET_ALL} | Frameworks: {data['frameworks']}")
        elif event_type == "ANALYSIS":
            print(f"  {Fore.YELLOW}[ANALYZER]{Style.RESET_ALL} {data}")
        elif event_type == "ANALYSIS_COMPLETE":
            print(f"  {Fore.YELLOW}[ANALYZER]{Style.RESET_ALL} Parsed {data['modules_analyzed']} modules | Cataloged {Fore.GREEN}{data['total_entities_extracted']} functions/classes{Style.RESET_ALL}")
        elif event_type == "SAFETY":
            print(f"  {Fore.CYAN}[SAFETY]{Style.RESET_ALL} {data}")
        elif event_type == "SAFETY_PRESERVATION":
            print(f"  {Fore.YELLOW}{Style.BRIGHT}⚠️ [SAFETY ALERT]{Style.RESET_ALL} {data['message']}")
            print(f"     Existing File: {data['existing_path']}")
            print(f"     Safe Target:   {data['target_path']}")
        elif event_type == "SAFETY_OVERWRITE":
            print(f"  {Fore.RED}{Style.BRIGHT}⚡ [OVERWRITE MODE]{Style.RESET_ALL} {data['message']}")
        elif event_type == "GENERATING":
            print(f"  {Fore.GREEN}[GENERATOR]{Style.RESET_ALL} {data}")
        elif event_type == "SAVED":
            print(f"  {Fore.GREEN}[GENERATOR]{Style.RESET_ALL} Written to: {data['output_path']}")

    agent.register_callback(on_event)


def main():
    """
    Entry point for README Writer Agent CLI execution.

    Operational Mechanics:
    1. Parses repository path and flags (--force, --output, --preview).
    2. Instantiates ReadmeWriterAgent.
    3. Runs inspection, safety check, and markdown generation.
    4. Displays execution summary and target file path.
    """
    print_banner()

    parser = argparse.ArgumentParser(
        description="Autonomous README Writer Agent: Inspects code repositories and generates production-ready READMEs."
    )
    parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to the repository root directory (default: current directory)."
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Authorize overwriting existing README.md if present (default is non-destructive preservation)."
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Custom output filename (e.g. CUSTOM_README.md)."
    )
    parser.add_argument(
        "--preview", "-p",
        action="store_true",
        help="Print a preview of the generated Markdown to the terminal."
    )

    args = parser.parse_args()

    repo_target = os.path.abspath(args.repo)
    if not os.path.exists(repo_target):
        print(f"{Fore.RED}Error: Repository path does not exist: {repo_target}{Style.RESET_ALL}")
        sys.exit(1)

    agent = ReadmeWriterAgent(verbose=True)
    setup_cli_telemetry(agent)

    try:
        result = agent.run(
            repo_path=repo_target,
            force=args.force,
            custom_output_name=args.output
        )

        print(f"\n{Fore.GREEN}{Style.BRIGHT}{'=' * 78}")
        print("🎉 README GENERATION COMPLETE!")
        print(f"{'=' * 78}{Style.RESET_ALL}")
        print(f"  • Target File:       {Fore.CYAN}{result.output_path}{Style.RESET_ALL}")
        if result.saved_as_alternate:
            print(f"  • Safety Status:     {Fore.YELLOW}Existing README preserved! Saved as alternate (README.generated.md){Style.RESET_ALL}")
        elif result.was_overwritten:
            print(f"  • Safety Status:     {Fore.RED}Existing README overwritten via --force flag{Style.RESET_ALL}")
        else:
            print(f"  • Safety Status:     {Fore.GREEN}Clean generation (no existing file conflicts){Style.RESET_ALL}")
        print(f"  • Functions Cataloged: {Fore.GREEN}{result.entities_documented_count} functions/classes with commentary{Style.RESET_ALL}")
        print(f"  • Sections Included: {len(result.sections_included)} standard production sections")
        print(f"{Fore.GREEN}{'=' * 78}{Style.RESET_ALL}\n")

        if args.preview:
            print(f"\n{Fore.YELLOW}--- PREVIEW OF GENERATED README ---{Style.RESET_ALL}\n")
            print(result.markdown_content[:2000])
            if len(result.markdown_content) > 2000:
                print(f"\n{Fore.YELLOW}... [{len(result.markdown_content)-2000} more characters written to file] ...{Style.RESET_ALL}")

    except Exception as e:
        print(f"\n{Fore.RED}❌ Generation Failed: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
