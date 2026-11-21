"""
Autonomous README Writer Agent Orchestrator
===========================================
Coordinates repository scanning, static AST inspection, safety collision detection,
and markdown generation into a single unified agent workflow.

All functions contain comprehensive educational commentary explaining agent lifecycle execution.
"""

import os
from typing import Optional, Callable, Any, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.models import RepositoryMetadata, ReadmeGenerationResult, CodeEntity
from core.scanner import RepositoryScanner
from core.analyzer import CodeAnalyzer
from core.safety import ReadmeSafetyController
from core.generator import ReadmeGenerator


class ReadmeWriterAgent:
    """
    Autonomous agent responsible for inspecting repositories and generating production-ready READMEs.
    """

    def __init__(self, verbose: bool = True):
        """
        Initializes the README Writer Agent.

        Args:
            verbose: Flag determining if real-time telemetry events are emitted.
        """
        self.verbose = verbose
        self.callbacks: List[Callable[[str, Any], None]] = []

    def register_callback(self, callback: Callable[[str, Any], None]):
        """
        Attaches an observer callback to receive live telemetry events.

        Args:
            callback: Function accepting (event_type: str, data: Any).
        """
        self.callbacks.append(callback)

    def _notify(self, event_type: str, data: Any):
        """
        Broadcasts an operational telemetry event to all registered listeners.
        """
        for cb in self.callbacks:
            try:
                cb(event_type, data)
            except Exception:
                pass

    def run(self, repo_path: str, force: bool = False, custom_output_name: Optional[str] = None) -> ReadmeGenerationResult:
        """
        Executes the end-to-end README generation workflow.

        Operational Lifecycle:
        1. [VALIDATION]: Verifies the target repository path exists and is a directory.
        2. [SCANNING]: Crawls directory tree, filters junk folders, detects tech stack.
        3. [CODE ANALYSIS]: Parses source code via AST, extracts classes, functions, docstrings,
           and synthesizes functional commentary for each entity.
        4. [SAFETY CHECK]: Inspects if README.md exists. If it exists and force=False,
           preserves original README and redirects output to README.generated.md!
        5. [SYNTHESIS]: Compiles Mermaid diagrams, ASCII trees, function tables, and guides.
        6. [PERSISTENCE]: Writes the markdown to disk safely and returns result metrics.

        Args:
            repo_path: Filesystem path to target repository root.
            force: If True, authorizes overwriting an existing README.md. Default is False.
            custom_output_name: Optional explicit filename for output.

        Returns:
            ReadmeGenerationResult containing path, status flags, and documented count.
        """
        abs_repo_path = os.path.abspath(repo_path)
        if not os.path.isdir(abs_repo_path):
            raise FileNotFoundError(f"Target repository path does not exist or is not a directory: {abs_repo_path}")

        repo_name = os.path.basename(abs_repo_path.rstrip(os.sep))
        self._notify("START", f"Initiating README inspection for: '{repo_name}' ({abs_repo_path})")

        # -------------------------------------------------------------
        # STEP 1: SCAN DIRECTORY STRUCTURE & TECH STACK
        # -------------------------------------------------------------
        self._notify("SCANNING", "Crawling files and detecting technology stack...")
        scanner = RepositoryScanner(abs_repo_path)
        files = scanner.scan_files()
        tech_stack = scanner.detect_tech_stack(files)
        ascii_tree = scanner.generate_ascii_tree(files)
        entry_points = scanner.identify_entry_points(files)
        test_files = [f for f in files if "test" in f.lower()]
        self._notify("SCAN_COMPLETE", {
            "total_files": len(files),
            "primary_language": tech_stack.primary_language,
            "frameworks": tech_stack.frameworks
        })

        # -------------------------------------------------------------
        # STEP 2: CODE ANALYSIS & FUNCTION COMMENTARY EXTRACTION
        # -------------------------------------------------------------
        self._notify("ANALYSIS", "Performing static AST code analysis & extracting function commentary...")
        analyzer = CodeAnalyzer(abs_repo_path)
        modules = []
        all_entities: List[CodeEntity] = []

        for f in files:
            analysis = analyzer.analyze_file(f)
            if analysis:
                modules.append(analysis)
                all_entities.extend(analysis.classes)
                all_entities.extend(analysis.functions)

        self._notify("ANALYSIS_COMPLETE", {
            "modules_analyzed": len(modules),
            "total_entities_extracted": len(all_entities)
        })

        # -------------------------------------------------------------
        # STEP 3: NON-DESTRUCTIVE SAFETY GUARDRAIL
        # -------------------------------------------------------------
        self._notify("SAFETY", "Checking for existing README files and verifying overwrite guardrails...")
        safety = ReadmeSafetyController(abs_repo_path)
        has_existing, existing_path = safety.check_existing_readme()

        target_output_path, was_overwritten, saved_as_alternate = safety.resolve_target_output_path(
            force_overwrite=force,
            custom_output_name=custom_output_name
        )

        if has_existing and not force and not custom_output_name:
            self._notify("SAFETY_PRESERVATION", {
                "message": "Existing README detected! Preserving original file. Output will be saved to README.generated.md",
                "existing_path": existing_path,
                "target_path": target_output_path
            })
        elif was_overwritten:
            self._notify("SAFETY_OVERWRITE", {
                "message": "Existing README will be overwritten as explicitly authorized via --force flag.",
                "target_path": target_output_path
            })

        # Assemble repository metadata model
        metadata = RepositoryMetadata(
            repo_name=repo_name,
            repo_path=abs_repo_path,
            tech_stack=tech_stack,
            modules=modules,
            all_entities=all_entities,
            file_tree_ascii=ascii_tree,
            entry_points=entry_points,
            test_files=test_files,
            has_existing_readme=has_existing,
            existing_readme_path=existing_path
        )

        # -------------------------------------------------------------
        # STEP 4: SYNTHESIZE PRODUCTION MARKDOWN
        # -------------------------------------------------------------
        self._notify("GENERATING", "Synthesizing Mermaid diagrams, file tree, and function reference table...")
        generator = ReadmeGenerator(metadata)
        markdown_text = generator.generate_markdown()

        # -------------------------------------------------------------
        # STEP 5: WRITE OUTPUT FILE TO DISK
        # -------------------------------------------------------------
        with open(target_output_path, "w", encoding="utf-8") as out_f:
            out_f.write(markdown_text)

        self._notify("SAVED", {
            "output_path": target_output_path,
            "was_overwritten": was_overwritten,
            "saved_as_alternate": saved_as_alternate,
            "entities_documented": len(all_entities)
        })

        sections = [
            "Executive Overview", "System Architecture (Mermaid)",
            "Key Capabilities", "Repository Structure",
            "Function & Component Reference Guide", "Installation & Prerequisites",
            "Quick Start & Usage", "Automated Testing", "Technology Stack Breakdown"
        ]

        return ReadmeGenerationResult(
            output_path=target_output_path,
            was_overwritten=was_overwritten,
            saved_as_alternate=saved_as_alternate,
            markdown_content=markdown_text,
            entities_documented_count=len(all_entities),
            sections_included=sections
        )
