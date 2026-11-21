"""
Code Inspection & Structural AST Analyzer
=========================================
Performs static analysis on source files using Python's Abstract Syntax Tree (AST) module
and regex parsers for polyglot codebases. Extracts functions, classes, docstrings,
signatures, and auto-generates descriptive functional commentary.

All functions contain comprehensive educational commentary on how static code parsing operates.
"""

import ast
import os
import re
from typing import List, Dict, Any, Optional
from core.models import CodeEntity, ModuleAnalysis
from core.security import SecurityValidator


class CodeAnalyzer:
    """
    Statically analyzes source code files to extract entities and generate functional summaries.
    """

    def __init__(self, repo_path: str, enhancer: Optional[Any] = None):
        """
        Initializes the code analyzer.

        Args:
            repo_path: Filesystem path to root directory of the inspected repository.
            enhancer: Optional GeminiEnhancer instance for LLM-powered commentary synthesis.
        """
        self.repo_path = os.path.abspath(repo_path)
        self.enhancer = enhancer

    def analyze_file(self, rel_path: str) -> Optional[ModuleAnalysis]:
        """
        Routes a source file to the appropriate static analyzer based on file extension.

        Operational Mechanics:
        1. Reads the raw file text safely with UTF-8 and ignore fallback for encoding safety.
        2. Routes Python (.py) files to the Python AST parser for deep structural extraction.
        3. Routes JS/TS/Go/Rust/Shell files to regex-based heuristic signature parsers.
        4. Returns a populated ModuleAnalysis containing all extracted classes and functions.

        Args:
            rel_path: Relative path to the source file from repository root.

        Returns:
            ModuleAnalysis dataclass or None if file cannot be parsed or is non-code.
        """
        abs_path = os.path.join(self.repo_path, rel_path)
        ext = os.path.splitext(rel_path)[1].lower()

        if ext not in [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".sh"]:
            return None

        # Guard against oversized files (prevents DoS / memory exhaustion)
        is_safe, _ = SecurityValidator.is_file_safe_to_read(abs_path)
        if not is_safe:
            return None

        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return None

        lines_count = len(content.splitlines())

        if ext == ".py":
            return self._analyze_python_ast(rel_path, content, lines_count)
        else:
            return self._analyze_polyglot_regex(rel_path, content, ext, lines_count)

    def _analyze_python_ast(self, rel_path: str, content: str, line_count: int) -> ModuleAnalysis:
        """
        Parses Python code using the official Abstract Syntax Tree (ast) standard library.

        Operational Mechanics:
        1. Compiles source code into an AST node hierarchy via ast.parse().
        2. Traverses the tree using ast.iter_child_nodes() to identify top-level:
           - ast.ClassDef: extracts class name, docstring, and member methods.
           - ast.FunctionDef / ast.AsyncFunctionDef: extracts parameters, return types,
             docstring, and decorator routes (e.g. @app.get('/api/...')).
           - ast.Import / ast.ImportFrom: extracts module dependencies.
        3. Generates descriptive functional commentary for each function explaining its role.

        Args:
            rel_path: Relative file path.
            content: Raw source code string.
            line_count: Total lines in the file.

        Returns:
            ModuleAnalysis populated with classes, functions, routes, and commentary.
        """
        classes: List[CodeEntity] = []
        functions: List[CodeEntity] = []
        imports: List[str] = []
        api_routes: List[str] = []
        cli_commands: List[str] = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Fall back to regex if file has Python 3.x syntax unsupported or invalid syntax
            return self._analyze_polyglot_regex(rel_path, content, ".py", line_count)

        for node in ast.iter_child_nodes(tree):
            # Extract Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

            # Extract Classes
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node) or ""
                commentary = self._synthesize_functional_commentary(node.name, "class", doc)
                class_entity = CodeEntity(
                    name=node.name,
                    entity_type="class",
                    file_path=rel_path,
                    line_number=node.lineno,
                    docstring=doc.strip(),
                    parameters=[b.id for b in node.bases if isinstance(b, ast.Name)],
                    commentary=commentary
                )
                classes.append(class_entity)

                # Extract Member Methods of the Class
                for sub_node in node.body:
                    if isinstance(sub_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_doc = ast.get_docstring(sub_node) or ""
                        method_type = "async_method" if isinstance(sub_node, ast.AsyncFunctionDef) else "method"
                        method_params = [arg.arg for arg in sub_node.args.args if arg.arg != "self"]
                        method_commentary = self._synthesize_functional_commentary(
                            sub_node.name, method_type, method_doc, parent_class=node.name
                        )
                        functions.append(CodeEntity(
                            name=f"{node.name}.{sub_node.name}",
                            entity_type=method_type,
                            file_path=rel_path,
                            line_number=sub_node.lineno,
                            docstring=method_doc.strip(),
                            parameters=method_params,
                            commentary=method_commentary
                        ))

            # Extract Top-Level Functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_doc = ast.get_docstring(node) or ""
                fn_type = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
                params = [arg.arg for arg in node.args.args]
                ret_type = ast.unparse(node.returns) if getattr(node, "returns", None) else None

                # Check for Web Framework Route Decorators (e.g. @app.get('/users'))
                is_route, route_path = self._detect_route_decorator(node)
                if is_route:
                    api_routes.append(route_path)

                # Check for CLI commands (e.g. @click.command() or argparse hooks)
                is_cli = any("command" in getattr(dec, "attr", "") or "command" in getattr(dec, "id", "")
                             for dec in node.decorator_list if hasattr(dec, "attr") or hasattr(dec, "id"))
                if is_cli:
                    cli_commands.append(node.name)

                commentary = self._synthesize_functional_commentary(node.name, fn_type, fn_doc)
                functions.append(CodeEntity(
                    name=node.name,
                    entity_type=fn_type,
                    file_path=rel_path,
                    line_number=node.lineno,
                    docstring=fn_doc.strip(),
                    parameters=params,
                    return_type=ret_type,
                    commentary=commentary
                ))

        # Check for argparse commands in main execution blocks
        if "argparse" in content:
            arg_matches = re.findall(r'add_argument\s*\(\s*["\'](-+[a-zA-Z0-9_\-]+)["\']', content)
            cli_commands.extend(list(set(arg_matches)))

        return ModuleAnalysis(
            file_path=rel_path,
            language="Python",
            total_lines=line_count,
            classes=classes,
            functions=functions,
            imports=sorted(list(set(imports))),
            cli_commands=sorted(list(set(cli_commands))),
            api_routes=sorted(list(set(api_routes)))
        )

    def _detect_route_decorator(self, node: ast.AST) -> Tuple[bool, str]:
        """
        Inspects function decorators for FastAPI / Flask HTTP route definitions.

        Operational Mechanics:
        Matches decorators like @app.get('/items'), @router.post('/login'), etc.
        """
        for dec in getattr(node, "decorator_list", []):
            if isinstance(dec, ast.Call):
                func = dec.func
                # Check for patterns like router.get or app.post
                if isinstance(func, ast.Attribute) and func.attr in ["get", "post", "put", "delete", "patch", "route"]:
                    if dec.args and isinstance(dec.args[0], ast.Constant):
                        return True, f"{func.attr.upper()} {dec.args[0].value}"
        return False, ""

    def _analyze_polyglot_regex(self, rel_path: str, content: str, ext: str, line_count: int) -> ModuleAnalysis:
        """
        Regex-based signature parser for JavaScript, TypeScript, Go, Rust, and Shell.

        Operational Mechanics:
        Uses compiled regular expressions to match function declarations, class definitions,
        export signatures, and route handlers across non-Python source files.
        """
        classes: List[CodeEntity] = []
        functions: List[CodeEntity] = []

        # JavaScript / TypeScript Function & Class Patterns
        if ext in [".js", ".ts", ".jsx", ".tsx"]:
            # Functions
            fn_matches = re.finditer(r'(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)', content)
            for m in fn_matches:
                fn_name = m.group(1)
                params = [p.strip() for p in m.group(2).split(",") if p.strip()]
                comment = self._synthesize_functional_commentary(fn_name, "function", "")
                functions.append(CodeEntity(
                    name=fn_name,
                    entity_type="function",
                    file_path=rel_path,
                    parameters=params,
                    commentary=comment
                ))

            # Classes
            cls_matches = re.finditer(r'(?:export\s+)?class\s+([a-zA-Z0-9_]+)', content)
            for m in cls_matches:
                cls_name = m.group(1)
                comment = self._synthesize_functional_commentary(cls_name, "class", "")
                classes.append(CodeEntity(
                    name=cls_name,
                    entity_type="class",
                    file_path=rel_path,
                    commentary=comment
                ))

        # Go Function Patterns (func Name(params) returnType)
        elif ext == ".go":
            fn_matches = re.finditer(r'func\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\(([^)]*)\)', content)
            for m in fn_matches:
                fn_name = m.group(1)
                comment = self._synthesize_functional_commentary(fn_name, "go_func", "")
                functions.append(CodeEntity(
                    name=fn_name,
                    entity_type="go_func",
                    file_path=rel_path,
                    commentary=comment
                ))

        # Rust Function Patterns (fn name(params))
        elif ext == ".rs":
            fn_matches = re.finditer(r'(?:pub\s+)?fn\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)', content)
            for m in fn_matches:
                fn_name = m.group(1)
                comment = self._synthesize_functional_commentary(fn_name, "rust_fn", "")
                functions.append(CodeEntity(
                    name=fn_name,
                    entity_type="rust_fn",
                    file_path=rel_path,
                    commentary=comment
                ))

        return ModuleAnalysis(
            file_path=rel_path,
            language=ext.replace(".", "").upper(),
            total_lines=line_count,
            classes=classes,
            functions=functions
        )

    def _synthesize_functional_commentary(self, entity_name: str, entity_type: str, docstring: str, parent_class: str = "") -> str:
        """
        Generates clean, human-readable commentary describing what a function/class does.

        Operational Mechanics:
        1. If the author provided a clear docstring, sanitizes the first paragraph.
        2. If no docstring exists, parses the naming conventions (snake_case, camelCase, verbs)
           to intelligently deduce and describe the operational purpose of the function:
           - 'get_*' -> Retrieves or fetches resource
           - 'set_*' / 'update_*' -> Mutates or modifies internal state
           - 'is_*' / 'has_*' -> Evaluates boolean condition
           - 'test_*' -> Verifies unit assertion
           - 'calculate_*' / 'compute_*' -> Performs quantitative computation
           - 'format_*' / 'serialize_*' -> Transforms data representation
        """
        # Rule 1: Use first line of explicit docstring if present and substantial
        if docstring:
            first_line = docstring.strip().split("\n")[0].strip()
            if len(first_line) > 12:
                return first_line

        # Rule 2: Derive human-readable commentary from semantic verb prefixes
        clean_name = entity_name.split(".")[-1]
        tokens = re.findall(r'[a-z]+|[A-Z][a-z]*', clean_name)
        joined_words = " ".join([t.lower() for t in tokens])

        if clean_name.startswith("test_"):
            return f"Automated test case verifying: {joined_words.replace('test ', '')}."
        elif clean_name.startswith("get_") or clean_name.startswith("fetch_"):
            return f"Retrieves and returns {joined_words.replace('get ', '').replace('fetch ', '')}."
        elif clean_name.startswith("set_") or clean_name.startswith("update_"):
            return f"Updates and persists {joined_words.replace('set ', '').replace('update ', '')} state."
        elif clean_name.startswith("is_") or clean_name.startswith("has_") or clean_name.startswith("can_"):
            return f"Evaluates whether {joined_words} condition holds true."
        elif clean_name.startswith("calculate_") or clean_name.startswith("compute_"):
            return f"Computes quantitative value for {joined_words.replace('calculate ', '').replace('compute ', '')}."
        elif clean_name.startswith("format_") or clean_name.startswith("to_"):
            return f"Formats and serializes {joined_words} into standard representation."
        elif clean_name.startswith("init_") or clean_name == "__init__":
            target = parent_class or "instance"
            return f"Initializes operational state and default parameters for {target}."
        elif clean_name.startswith("parse_") or clean_name.startswith("extract_"):
            return f"Parses and extracts structured data from {joined_words.replace('parse ', '').replace('extract ', '')}."
        elif clean_name.startswith("run_") or clean_name.startswith("execute_"):
            return f"Executes the lifecycle workflow for {joined_words.replace('run ', '').replace('execute ', '')}."

        # Default fallback description
        if parent_class:
            base_comment = f"Member method of {parent_class} providing {joined_words} capabilities."
        else:
            base_comment = f"Core {entity_type} implementing {joined_words} operations."

        # Rule 3: If Gemini AI enhancer is active and function lacked a docstring, enrich with AI
        if self.enhancer and getattr(self.enhancer, "is_available", lambda: False)():
            return self.enhancer.enhance_commentary(entity_name, f"{entity_type} {entity_name}", base_comment)

        return base_comment
