"""
Core Data Models for README Writer Agent
========================================
Defines structured dataclasses representing repository metadata, extracted code
entities (functions, classes, routes), detected technology stacks, and generation output.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class CodeEntity:
    """
    Represents an extracted function, method, or class within a source code file.

    Attributes:
        name: Name of the function or class.
        entity_type: Type identifier ('function', 'async_function', 'class', 'route').
        file_path: Relative path of the file containing the entity.
        line_number: Line number where definition begins.
        docstring: Extracted docstring or documentation comment.
        parameters: List of parameter names and optional type annotations.
        return_type: Return type annotation if specified.
        commentary: Generated or parsed commentary explaining what this entity does.
    """
    name: str
    entity_type: str
    file_path: str
    line_number: int = 1
    docstring: str = ""
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    commentary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Converts CodeEntity instance to a serializable dictionary."""
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "docstring": self.docstring,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "commentary": self.commentary
        }


@dataclass
class ModuleAnalysis:
    """
    Represents structural code analysis of an individual source file.

    Attributes:
        file_path: Relative path to the source file.
        language: Programming language of the file (e.g. 'python', 'javascript').
        total_lines: Total lines of code.
        classes: List of CodeEntity objects representing classes.
        functions: List of CodeEntity objects representing functions or methods.
        imports: List of imported package and module names.
        cli_commands: List of detected CLI command names or argument flags.
        api_routes: List of detected HTTP routes (e.g. FastAPI / Flask / Express).
    """
    file_path: str
    language: str
    total_lines: int = 0
    classes: List[CodeEntity] = field(default_factory=list)
    functions: List[CodeEntity] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    cli_commands: List[str] = field(default_factory=list)
    api_routes: List[str] = field(default_factory=list)


@dataclass
class ProjectTechStack:
    """
    Identified frameworks, tools, package managers, and languages in the repository.

    Attributes:
        primary_language: Primary detected programming language.
        languages: Set/List of all detected languages.
        package_managers: Package managers detected (e.g. pip, npm, poetry, cargo).
        frameworks: Frameworks detected (e.g. FastAPI, Flask, React, Next.js, PyTorch).
        testing_tools: Testing frameworks detected (e.g. pytest, unittest, jest).
        dependencies: Key third-party dependencies extracted from manifest files.
    """
    primary_language: str = "Unknown"
    languages: List[str] = field(default_factory=list)
    package_managers: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    testing_tools: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class RepositoryMetadata:
    """
    Comprehensive aggregated structural model of the entire inspected repository.

    Attributes:
        repo_name: Name of the repository folder.
        repo_path: Absolute filesystem path to the repository.
        tech_stack: Identified ProjectTechStack object.
        modules: List of ModuleAnalysis objects for each analyzed source file.
        all_entities: Combined list of all CodeEntity instances found.
        file_tree_ascii: Formatted ASCII directory hierarchy tree.
        entry_points: Detected primary execution files (e.g. main.py, app.py, index.js).
        test_files: Detected test file paths.
        has_existing_readme: Boolean flag indicating if a README file is present.
        existing_readme_path: Absolute path to existing README if present.
    """
    repo_name: str
    repo_path: str
    tech_stack: ProjectTechStack = field(default_factory=ProjectTechStack)
    modules: List[ModuleAnalysis] = field(default_factory=list)
    all_entities: List[CodeEntity] = field(default_factory=list)
    file_tree_ascii: str = ""
    entry_points: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    has_existing_readme: bool = False
    existing_readme_path: Optional[str] = None


@dataclass
class ReadmeGenerationResult:
    """
    Output payload of the README generation process.

    Attributes:
        output_path: Absolute path where markdown was saved.
        was_overwritten: True if an existing README was overwritten (only via --force).
        saved_as_alternate: True if written to README.generated.md due to existing README.
        markdown_content: The full generated Markdown text.
        entities_documented_count: Count of functions/classes documented with comments.
        sections_included: List of sections generated in the README.
    """
    output_path: str
    was_overwritten: bool
    saved_as_alternate: bool
    markdown_content: str
    entities_documented_count: int
    sections_included: List[str] = field(default_factory=list)
