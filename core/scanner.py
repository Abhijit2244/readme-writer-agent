"""
Repository Scanner & Structure Crawler
======================================
Recursively inspects repository directories, filters out build/runtime artifacts,
detects package managers and frameworks, and generates clean ASCII file trees.

All functions are heavily annotated with educational commentary on their operational logic.
"""

import os
import re
from typing import List, Dict, Set, Tuple
from core.models import ProjectTechStack


class RepositoryScanner:
    """
    Crawls repository file systems and identifies high-level architectural metadata.
    """

    # Directory names that represent virtual environments, package caches, or VCS metadata
    # that should NEVER clutter repository analysis or documentation.
    IGNORED_DIRS: Set[str] = {
        ".git", ".svn", ".hg", "__pycache__", ".pytest_cache", ".mypy_cache",
        "node_modules", "bower_components", ".venv", "venv", "env", ".env",
        ".idea", ".vscode", "dist", "build", "target", "out", "coverage",
        ".egg-info", "eggs", ".tox"
    }

    # File extensions to ignore (binaries, lock files with noise, compiled binaries)
    IGNORED_EXTENSIONS: Set[str] = {
        ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe", ".bin",
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".zip", ".tar",
        ".gz", ".7z", ".pdf", ".lock"
    }

    def __init__(self, repo_path: str):
        """
        Initializes the repository scanner.

        Args:
            repo_path: Filesystem path to the root directory of the target repository.
        """
        self.repo_path = os.path.abspath(repo_path)
        self.repo_name = os.path.basename(self.repo_path.rstrip(os.sep))

    def scan_files(self) -> List[str]:
        """
        Discovers all relevant source, configuration, and documentation files.

        Operational Mechanics:
        1. Uses os.walk to recursively descend through the directory tree.
        2. Filters dirnames in-place to prune ignored directories (.git, node_modules, etc.)
           before descending, saving I/O time on massive trees.
        3. Checks file extensions against IGNORED_EXTENSIONS to discard binaries.
        4. Returns normalized relative paths for consistent cross-platform reporting.

        Returns:
            List of normalized relative file paths from repository root.
        """
        discovered_files: List[str] = []

        for root, dirs, files in os.walk(self.repo_path):
            # In-place directory filtering prevents os.walk from descending into junk folders
            dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS and not d.startswith(".git")]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.IGNORED_EXTENSIONS:
                    continue

                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, self.repo_path).replace("\\", "/")
                discovered_files.append(rel_path)

        return sorted(discovered_files)

    def detect_tech_stack(self, files: List[str]) -> ProjectTechStack:
        """
        Analyzes file names, manifest files, and dependencies to deduce the project tech stack.

        Operational Mechanics:
        1. Inspects manifest files (requirements.txt, package.json, pyproject.toml, Cargo.toml).
        2. Counts extension frequencies to determine the primary programming language.
        3. Identifies web frameworks (FastAPI, Flask, Django, Express, Next.js).
        4. Identifies testing tools (pytest, unittest, jest, mocha).
        5. Extracts notable external libraries to populate prerequisites and dependencies.

        Args:
            files: List of relative file paths discovered in the repository.

        Returns:
            ProjectTechStack dataclass summarizing languages, frameworks, and tools.
        """
        languages_count: Dict[str, int] = {}
        package_managers: Set[str] = set()
        frameworks: Set[str] = set()
        testing_tools: Set[str] = set()
        dependencies: Set[str] = set()

        extension_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "React (JSX)",
            ".tsx": "React (TSX)",
            ".go": "Go",
            ".rs": "Rust",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".cs": "C#",
            ".rb": "Ruby",
            ".php": "PHP",
            ".sh": "Shell Script",
            ".html": "HTML",
            ".css": "CSS",
            ".sql": "SQL"
        }

        # 1. Count language extensions
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in extension_map:
                lang = extension_map[ext]
                languages_count[lang] = languages_count.get(lang, 0) + 1

        # 2. Inspect manifest files for package managers and libraries
        for f in files:
            base = os.path.basename(f).lower()

            # Python manifests
            if base == "requirements.txt" or base == "requirements-dev.txt":
                package_managers.add("pip")
                self._extract_python_requirements(f, dependencies, frameworks, testing_tools)
            elif base in ["pyproject.toml", "poetry.lock"]:
                package_managers.add("poetry / pip")
                self._inspect_toml_or_text(f, dependencies, frameworks, testing_tools)
            elif base == "setup.py":
                package_managers.add("setuptools")

            # Node / JavaScript manifests
            elif base == "package.json":
                package_managers.add("npm / pnpm / yarn")
                self._extract_node_dependencies(f, dependencies, frameworks, testing_tools)

            # Rust manifest
            elif base == "cargo.toml":
                package_managers.add("cargo")
                frameworks.add("Rust Cargo")

            # Go manifest
            elif base == "go.mod":
                package_managers.add("go modules")

            # Docker containerization
            elif "dockerfile" in base or "docker-compose" in base:
                frameworks.add("Docker")

        # 3. Detect testing frameworks by file naming conventions
        for f in files:
            f_lower = f.lower()
            if "test_" in f_lower or "_test.py" in f_lower or "tests/" in f_lower:
                testing_tools.add("pytest / unittest")
            elif ".test.js" in f_lower or ".spec.ts" in f_lower:
                testing_tools.add("Jest / Mocha")

        # Determine primary language by frequency
        primary_lang = "Generic / Multi-Language"
        if languages_count:
            primary_lang = max(languages_count.items(), key=lambda x: x[1])[0]

        return ProjectTechStack(
            primary_language=primary_lang,
            languages=list(languages_count.keys()),
            package_managers=sorted(list(package_managers)),
            frameworks=sorted(list(frameworks)),
            testing_tools=sorted(list(testing_tools)),
            dependencies=sorted(list(dependencies))[:12]
        )

    def _extract_python_requirements(self, rel_path: str, deps: Set[str], frameworks: Set[str], tests: Set[str]):
        """
        Parses requirements.txt to detect key frameworks and dependencies.

        Operational Mechanics:
        Reads line-by-line, ignores comments, strips versions (e.g. 'fastapi>=0.100' -> 'fastapi'),
        and matches against a dictionary of well-known frameworks.
        """
        abs_path = os.path.join(self.repo_path, rel_path)
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    clean = re.split(r'[>=<#~]', line.strip())[0].strip().lower()
                    if not clean or clean.startswith("-"):
                        continue
                    deps.add(clean)

                    # Framework heuristic mapping
                    if clean in ["fastapi", "flask", "django", "tornado", "sanic"]:
                        frameworks.add(clean.capitalize())
                    elif clean in ["torch", "pytorch", "tensorflow", "keras", "scikit-learn"]:
                        frameworks.add(f"ML / {clean.capitalize()}")
                    elif clean in ["pytest", "unittest", "nose"]:
                        tests.add(clean)
                    elif clean in ["celery", "redis", "pydantic", "sqlalchemy"]:
                        frameworks.add(clean.capitalize())
        except Exception:
            pass

    def _extract_node_dependencies(self, rel_path: str, deps: Set[str], frameworks: Set[str], tests: Set[str]):
        """
        Inspects package.json to extract Node.js dependencies and frameworks.
        """
        abs_path = os.path.join(self.repo_path, rel_path)
        try:
            import json
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
                all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                for pkg in all_deps.keys():
                    pkg_lower = pkg.lower()
                    deps.add(pkg)
                    if pkg_lower in ["express", "react", "next", "vue", "angular", "svelte"]:
                        frameworks.add(pkg.capitalize())
                    elif pkg_lower in ["jest", "mocha", "vitest", "cypress"]:
                        tests.add(pkg.capitalize())
        except Exception:
            pass

    def _inspect_toml_or_text(self, rel_path: str, deps: Set[str], frameworks: Set[str], tests: Set[str]):
        """Quick text-based dependency scanner for TOML files."""
        abs_path = os.path.join(self.repo_path, rel_path)
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                for kw in ["fastapi", "flask", "django", "torch", "pydantic", "pytest"]:
                    if kw in content:
                        frameworks.add(kw.capitalize())
        except Exception:
            pass

    def generate_ascii_tree(self, files: List[str], max_depth: int = 3, max_files_per_dir: int = 8) -> str:
        """
        Constructs an attractive ASCII tree representation of the repository.

        Operational Mechanics:
        1. Breaks relative paths into hierarchical directory components.
        2. Limits recursion depth (max_depth) and entries per folder (max_files_per_dir)
           so the resulting README tree remains clean, readable, and compact.
        3. Uses standard Unicode tree formatting glyphs ('├── ', '└── ', '│   ').

        Args:
            files: List of relative file paths.
            max_depth: Maximum directory nesting level to display.
            max_files_per_dir: Maximum files to list per directory before summarizing.

        Returns:
            A formatted multi-line ASCII directory hierarchy tree string.
        """
        # Build nested dictionary tree
        tree: Dict[str, Any] = {}
        for f in files:
            parts = f.split("/")
            curr = tree
            for part in parts:
                curr = curr.setdefault(part, {})

        lines = [f"{self.repo_name}/"]

        def _render(node: Dict[str, Any], prefix: str = "", depth: int = 1):
            if depth > max_depth:
                lines.append(f"{prefix}└── ...")
                return

            items = sorted(node.keys(), key=lambda k: (bool(node[k]), k))
            visible_items = items[:max_files_per_dir]
            hidden_count = len(items) - len(visible_items)

            for i, key in enumerate(visible_items):
                is_last = (i == len(visible_items) - 1) and (hidden_count == 0)
                connector = "└── " if is_last else "├── "
                is_dir = bool(node[key])
                display_name = f"{key}/" if is_dir else key
                lines.append(f"{prefix}{connector}{display_name}")

                if is_dir:
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    _render(node[key], new_prefix, depth + 1)

            if hidden_count > 0:
                lines.append(f"{prefix}└── ... ({hidden_count} more items)")

        _render(tree, "", 1)
        return "\n".join(lines)

    def identify_entry_points(self, files: List[str]) -> List[str]:
        """
        Locates the primary execution entry points of the application.

        Operational Mechanics:
        Checks for conventional script entry filenames (main.py, app.py, index.js, cli.py, etc.)
        and sorts them by typical invocation priority.
        """
        candidates = []
        priority_names = [
            "main.py", "app.py", "run.py", "server.py", "cli.py", "index.py",
            "index.js", "index.ts", "server.js", "app.js", "main.go", "main.rs"
        ]

        for p in priority_names:
            for f in files:
                if f.lower() == p or f.lower().endswith("/" + p):
                    candidates.append(f)

        return candidates
