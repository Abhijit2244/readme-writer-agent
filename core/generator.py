"""
Production README Markdown Synthesizer
======================================
Compiles structured repository analysis into an enterprise-grade, publication-ready README
matching modern high-standard developer portfolios (e.g. Abhijit2244/let-the-wheel-decide).

Includes:
  • Vibrant title, bold tagline, and live demo callout
  • Thematically grouped features with descriptive bullet points
  • 2-Column Tech Stack table (Technology | Purpose)
  • Screenshot preview placeholders
  • Numbered step-by-step Getting Started instructions
  • Clean ASCII directory hierarchy tree
  • Comprehensive Function & Component Reference Table with detailed operational commentary
  • Interactive Mermaid architecture flowcharts
  • Step-by-step user journey guide ("How to Use")
  • Future Improvements checklist
  • Git branch-and-PR contributing guidelines
  • License, Author attribution, and star callout

All functions are heavily annotated with commentary explaining markdown formatting and structure.
"""

import os
import re
from typing import List, Dict, Any, Optional
from core.models import RepositoryMetadata, CodeEntity, ModuleAnalysis


class ReadmeGenerator:
    """
    Synthesizes structural repository metadata into production-grade GitHub-Flavored Markdown.
    """

    def __init__(self, metadata: RepositoryMetadata):
        """
        Initializes the README generator with repository inspection metadata.

        Args:
            metadata: RepositoryMetadata populated by scanner and code analyzer.
        """
        self.metadata = metadata

    def generate_markdown(self) -> str:
        """
        Orchestrates full assembly of all standard production README sections.

        Operational Mechanics:
        Assembles all sections in exact alignment with modern production README standards.

        Returns:
            Complete GitHub-Flavored Markdown string.
        """
        sections: List[str] = [
            self._build_header(),
            self._build_features(),
            self._build_tech_stack_table(),
            self._build_preview_section(),
            self._build_getting_started(),
            self._build_file_tree(),
            self._build_function_commentary_table(),
            self._build_architecture_mermaid(),
            self._build_how_to_use(),
            self._build_future_improvements(),
            self._build_contributing(),
            self._build_license_and_author()
        ]

        return "\n\n---\n\n".join(sections)

    def _build_header(self) -> str:
        """
        Generates repository title, bold tagline, overview synopsis, and demo badge.
        Inspired by the clean, inviting style of Abhijit2244/let-the-wheel-decide.
        """
        repo_title = self.metadata.repo_name.replace("-", " ").replace("_", " ").title()
        primary_lang = self.metadata.tech_stack.primary_language
        frameworks_str = ", ".join(self.metadata.tech_stack.frameworks) if self.metadata.tech_stack.frameworks else "modern design patterns"

        # Choose a fitting thematic emoji
        name_lower = self.metadata.repo_name.lower()
        if any(w in name_lower for w in ["wheel", "game", "spin"]):
            emoji = "🎡"
        elif any(w in name_lower for w in ["agent", "ai", "bot"]):
            emoji = "🤖"
        elif any(w in name_lower for w in ["rag", "search", "retriev"]):
            emoji = "🔍"
        elif any(w in name_lower for w in ["platform", "cloud", "server", "api"]):
            emoji = "🌐"
        elif any(w in name_lower for w in ["transformer", "model", "llm"]):
            emoji = "🧠"
        elif any(w in name_lower for w in ["readme", "doc", "writer"]):
            emoji = "📝"
        else:
            emoji = "🚀"

        lines = [
            f"# {emoji} {repo_title}",
            "",
            f"**Streamlined, production-grade {primary_lang} solution engineered with {frameworks_str}.**",
            "",
            f"{repo_title} is a modular, high-reliability software system built with {primary_lang}. "
            f"It provides clean separation of concerns, comprehensive automated testing, and deterministic execution "
            f"tailored for developers and teams demanding scalable performance.",
            "",
            f"< [🚀 **Live Demo & Project Repository**](https://github.com/YOUR_USERNAME/{self.metadata.repo_name}) >",
            "",
            f"Whether you are integrating into existing CI/CD workflows, developing custom modules, "
            f"or deploying standalone services, {repo_title} delivers an intuitive, well-documented experience."
        ]
        return "\n".join(lines)

    def _build_features(self) -> str:
        """
        Compiles highlighted features grouped into rich thematic subsections with emojis,
        exactly mirroring the structure in Abhijit2244/let-the-wheel-decide.
        """
        primary_lang = self.metadata.tech_stack.primary_language
        frameworks = ", ".join(self.metadata.tech_stack.frameworks) if self.metadata.tech_stack.frameworks else "Native Architecture"

        lines = [
            "## ✨ Features",
            "",
            "### 🎯 Core Execution Pipeline",
            f"- High-throughput execution engine optimized for {primary_lang}.",
            "- Deterministic execution loops with granular error handling and safety boundaries.",
            "- Clean separation of domain logic, state management, and output serialization.",
            "",
            "### ⚙️ Component & Logic Management",
            f"- Fully modular architecture built on {frameworks}.",
            "- Strictly typed models ensuring robust contract validation.",
            "- Automated detection of manifests, dependencies, and environment configurations.",
            "",
            "### 🛡️ Safety & Non-Destructive Guardrails",
            "- Non-destructive execution safeguards preventing accidental data loss or file collisions.",
            "- Explicit confirmation and override flags for administrative actions.",
            "- Comprehensive logging with color-coded operational telemetry.",
            "",
            "### 📊 Analytics & Reporting",
            "- Built-in verification metrics and structural code inspection.",
            "- Automatic generation of component relationship graphs and file trees.",
            "- Production-ready artifacts and structured summaries."
        ]
        return "\n".join(lines)

    def _build_tech_stack_table(self) -> str:
        """
        Constructs a clean 2-column Technology-Purpose table matching let-the-wheel-decide.
        """
        stack = self.metadata.tech_stack
        lines = [
            "## 🛠️ Tech Stack",
            "",
            "| Technology | Purpose |",
            "|---|---|"
        ]

        # Primary language
        lines.append(f"| {stack.primary_language} | Core application runtime & logic |")

        # Package manager
        if stack.package_managers:
            pm = ", ".join(stack.package_managers)
            lines.append(f"| {pm} | Package management & dependency resolution |")

        # Frameworks
        for fw in stack.frameworks:
            lines.append(f"| {fw} | Application framework & service orchestration |")

        # Testing
        if stack.testing_tools:
            tt = ", ".join(stack.testing_tools)
            lines.append(f"| {tt} | Automated test runner & regression verification |")
        else:
            lines.append(f"| Built-in Test Suite | Behavioral stability verification |")

        # Key dependencies
        for dep in stack.dependencies[:4]:
            lines.append(f"| {dep} | Domain utility & functional processing |")

        # Markdown & Documentation
        lines.append("| GitHub Flavored Markdown | Standardized documentation specification |")
        lines.append("| Mermaid.js | Interactive architectural flowcharts |")

        return "\n".join(lines)

    def _build_preview_section(self) -> str:
        """
        Generates screenshot and UI preview placeholders.
        """
        lines = [
            "## 📸 Application Preview",
            "",
            "<!-- Add your application screenshots here -->",
            "",
            "<!--",
            f"![Overview Screenshot](./screenshots/overview.png)",
            f"![Workflow Demonstration](./screenshots/workflow.png)",
            "-->"
        ]
        return "\n".join(lines)

    def _build_getting_started(self) -> str:
        """
        Generates numbered, step-by-step local setup instructions matching let-the-wheel-decide:
        1. Clone repository
        2. Navigate to directory
        3. Install dependencies
        4. Start application
        5. Build / Verify
        6. Run automated tests
        """
        primary_lang = self.metadata.tech_stack.primary_language
        repo_name = self.metadata.repo_name
        entry = self.metadata.entry_points[0] if self.metadata.entry_points else "main.py"
        test_file = self.metadata.test_files[0] if self.metadata.test_files else "test_all.py"

        is_python = "python" in primary_lang.lower()
        is_node = any(l in primary_lang.lower() for l in ["javascript", "typescript", "react", "node"])

        lines = [
            "## 🚀 Getting Started",
            "",
            "Follow these instructions to run the project locally.",
            "",
            "### Prerequisites",
            "",
            "Make sure you have the following installed:",
            ""
        ]

        if is_node:
            lines.extend([
                "- [Node.js](https://nodejs.org/) (LTS version recommended)",
                "- npm / pnpm / yarn",
                "- [Git](https://git-scm.com/)"
            ])
            install_cmd = "npm install"
            run_cmd = "npm run dev" if any("vite" in d.lower() or "next" in d.lower() for d in self.metadata.tech_stack.dependencies) else "npm start"
            build_cmd = "npm run build"
            test_cmd = "npm test"
        else:
            lines.extend([
                "- [Python](https://www.python.org/) (v3.9 or higher recommended)",
                "- pip package manager",
                "- [Git](https://git-scm.com/)"
            ])
            install_cmd = "pip install -r requirements.txt"
            run_cmd = f"python {entry}"
            build_cmd = f"python {entry} --help"
            test_cmd = f"python {test_file}"

        lines.extend([
            "",
            "### 1. Clone the repository",
            "",
            "```bash",
            f"git clone https://github.com/YOUR_USERNAME/{repo_name}.git",
            "```",
            "",
            "### 2. Navigate to the project directory",
            "",
            "```bash",
            f"cd {repo_name}",
            "```",
            "",
            "### 3. Install dependencies",
            "",
            "```bash",
            install_cmd,
            "```",
            "",
            "### 4. Start the application",
            "",
            "```bash",
            run_cmd,
            "```",
            "",
            "### 5. Verify build & execution flags",
            "",
            "```bash",
            build_cmd,
            "```",
            "",
            "### 6. Run automated test suite",
            "",
            "```bash",
            test_cmd,
            "```"
        ])

        return "\n".join(lines)

    def _build_file_tree(self) -> str:
        """
        Formats the ASCII directory hierarchy tree.
        """
        lines = [
            "## 📁 Project Structure",
            "",
            "```text",
            self.metadata.file_tree_ascii,
            "```"
        ]
        return "\n".join(lines)

    def _build_function_commentary_table(self) -> str:
        """
        Generates the Comprehensive Component & Function Reference Table with commentary on what it wrote!

        Operational Mechanics:
        Iterates through all discovered classes, methods, and functions, compiling an
        exhaustive documentation table with parameter signatures and operational comments.
        """
        lines = [
            "## 🔍 Function & Component Reference Guide",
            "",
            "The table below details the key functions, classes, and methods discovered across the codebase, "
            "along with operational commentary on what each component does:",
            "",
            "| Component / Function | File Location | Parameters | Operational Purpose & Commentary |",
            "|:---|:---|:---|:---|"
        ]

        if not self.metadata.all_entities:
            lines.append("| `main()` | `main.py:1` | `*(None)*` | Primary execution entry point. |")
            return "\n".join(lines)

        for entity in self.metadata.all_entities[:25]:
            name_display = f"`{entity.name}()`" if entity.entity_type != "class" else f"**{entity.name}** *(Class)*"
            loc_display = f"`{entity.file_path}:{entity.line_number}`"
            params_display = ", ".join(entity.parameters[:3]) if entity.parameters else "*(None)*"
            if len(entity.parameters) > 3:
                params_display += f" *(+{len(entity.parameters)-3} more)*"

            clean_commentary = entity.commentary.replace("|", "-").replace("\n", " ").strip()
            if not clean_commentary:
                clean_commentary = f"Executes {entity.name} operations."

            lines.append(f"| {name_display} | {loc_display} | `{params_display}` | {clean_commentary} |")

        return "\n".join(lines)

    def _build_architecture_mermaid(self) -> str:
        """
        Constructs an interactive Mermaid flowchart representing the high-level codebase architecture.
        """
        lines = [
            "## 🏗️ System Architecture",
            "",
            "```mermaid",
            "flowchart TD",
            "    Client([\"Client / User Request\"]) --> Gateway[\"Execution Interface\"]",
            "    Gateway --> Router{\"Core Orchestrator\"}"
        ]

        top_modules = [m.file_path for m in self.metadata.modules[:4]]
        if top_modules:
            for idx, mod in enumerate(top_modules, 1):
                clean_name = os.path.basename(mod).replace(".", "_")
                label = os.path.basename(mod)
                lines.append(f"    Router --> Mod_{idx}[\"{label}\"]")
            lines.append("    Mod_1 --> Output([\"Validated Output / Report\"])")
        else:
            lines.append("    Router --> Processing[\"Data Processing & State Validation\"]")
            lines.append("    Processing --> Output([\"Execution Output\"])")

        lines.append("```")
        return "\n".join(lines)

    def _build_how_to_use(self) -> str:
        """
        Generates numbered "How to Use" user journey steps.
        """
        entry = self.metadata.entry_points[0] if self.metadata.entry_points else "main.py"
        return (
            "## 🧭 How to Use\n\n"
            "1. **Initialize the Environment**: Ensure required runtime dependencies are installed.\n"
            f"2. **Launch the Application**: Run `{entry}` from your terminal or command prompt.\n"
            "3. **Configure Parameters**: Supply target input paths, configuration flags, or environment variables.\n"
            "4. **Inspect Generated Outputs**: Review generated artifacts, structured outputs, or UI displays.\n"
            "5. **Execute Test Harness**: Run automated test suites to verify stability before deployment."
        )

    def _build_future_improvements(self) -> str:
        """
        Generates future improvements checklist with interactive markdown checkboxes.
        """
        return (
            "## 🔮 Future Improvements\n\n"
            "Here are planned features and ideas for upcoming releases:\n\n"
            "- [ ] Interactive real-time Web dashboard interface.\n"
            "- [ ] Docker containerization and pre-built deployment images.\n"
            "- [ ] GitHub Actions CI/CD workflows for automated testing on pull requests.\n"
            "- [ ] Deep telemetry metrics and performance tracing.\n"
            "- [ ] Cloud synchronization and remote storage adapters."
        )

    def _build_contributing(self) -> str:
        """
        Generates standardized Git branch-and-PR contributing guidelines matching let-the-wheel-decide.
        """
        return (
            "## 🤝 Contributing\n\n"
            "Contributions, suggestions, and feature requests are welcome!\n\n"
            "If you have an idea that could make this project better:\n\n"
            "1. Fork the repository.\n"
            "2. Create a feature branch.\n\n"
            "```bash\n"
            "git checkout -b feature/your-feature-name\n"
            "```\n\n"
            "3. Commit your changes.\n\n"
            "```bash\n"
            "git commit -m \"Add: your feature description\"\n"
            "```\n\n"
            "4. Push your branch.\n\n"
            "```bash\n"
            "git push origin feature/your-feature-name\n"
            "```\n\n"
            "5. Open a Pull Request."
        )

    def _build_license_and_author(self) -> str:
        """
        Generates License, Author attribution, and star callout matching let-the-wheel-decide.
        """
        return (
            "## 📄 License\n\n"
            "This project is licensed under the MIT License - see the LICENSE file for details.\n\n"
            "---\n\n"
            "## 👨‍💻 Author\n\n"
            "Built with ❤️ and engineered for production reliability.\n\n"
            "---\n\n"
            "⭐ If you find this project interesting, consider giving the repository a star!"
        )
