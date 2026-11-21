"""
Comprehensive Automated Test Suite for README Writer Agent
==========================================================
Verifies:
  1. Repository Scanning & Directory Tree Generation
  2. Tech Stack & Framework Detection
  3. Python AST Parsing & Function Commentary Generation
  4. Non-Destructive Safety Guardrails (Never overwrites existing README)
  5. Force Overwrite Authorization Mode
  6. Mermaid Architecture & Table Generation
  7. End-to-End Agent Lifecycle
"""

import os
import sys
import shutil
import tempfile

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.models import RepositoryMetadata, CodeEntity, ModuleAnalysis
from core.scanner import RepositoryScanner
from core.analyzer import CodeAnalyzer
from core.safety import ReadmeSafetyController
from core.generator import ReadmeGenerator
from core.agent import ReadmeWriterAgent


def test_01_scanner_filters_and_tree():
    """Validates that scanner ignores junk directories and builds clean ASCII trees."""
    temp_dir = tempfile.mkdtemp(prefix="test_repo_scanner_")
    try:
        # Create sample directory structure
        os.makedirs(os.path.join(temp_dir, "core"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, ".git"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "node_modules"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "__pycache__"), exist_ok=True)

        # Create files
        with open(os.path.join(temp_dir, "main.py"), "w") as f:
            f.write("print('hello')\n")
        with open(os.path.join(temp_dir, "core", "logic.py"), "w") as f:
            f.write("def calculate(): pass\n")
        with open(os.path.join(temp_dir, ".git", "config"), "w") as f:
            f.write("[core]\n")
        with open(os.path.join(temp_dir, "node_modules", "junk.js"), "w") as f:
            f.write("// junk\n")

        scanner = RepositoryScanner(temp_dir)
        files = scanner.scan_files()

        # Assert ignored folders were skipped
        assert "main.py" in files
        assert "core/logic.py" in files
        assert not any(".git" in f for f in files)
        assert not any("node_modules" in f for f in files)

        tree = scanner.generate_ascii_tree(files)
        assert "main.py" in tree
        assert "core/" in tree
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_02_tech_stack_detection():
    """Validates framework and dependency detection from manifest files."""
    temp_dir = tempfile.mkdtemp(prefix="test_repo_stack_")
    try:
        req_file = os.path.join(temp_dir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("fastapi>=0.100.0\nuvicorn\npytest>=7.0\npydantic\n")

        with open(os.path.join(temp_dir, "main.py"), "w") as f:
            f.write("import fastapi\n")

        scanner = RepositoryScanner(temp_dir)
        files = scanner.scan_files()
        stack = scanner.detect_tech_stack(files)

        assert stack.primary_language == "Python"
        assert "pip" in stack.package_managers
        assert any("Fastapi" in fw or "FastAPI" in fw for fw in stack.frameworks)
        assert any("pytest" in t for t in stack.testing_tools)
        assert "fastapi" in stack.dependencies
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_03_ast_analyzer_python():
    """Validates Python AST parsing, docstrings, parameters, and generated commentary."""
    sample_code = '''
"""Module docstring for sample math module."""

class DataProcessor:
    """Manages data transformation pipelines."""

    def __init__(self, buffer_size: int = 1024):
        self.buffer_size = buffer_size

    def calculate_metrics(self, data_list):
        """Computes statistical metrics over input list."""
        return sum(data_list)

def fetch_remote_records(endpoint: str, timeout: int = 10):
    """Retrieves remote dataset records from specified HTTP endpoint."""
    return []

def is_valid_payload(payload):
    return bool(payload)
'''
    temp_dir = tempfile.mkdtemp(prefix="test_repo_ast_")
    try:
        test_file = os.path.join(temp_dir, "processor.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(sample_code)

        analyzer = CodeAnalyzer(temp_dir)
        analysis = analyzer.analyze_file("processor.py")

        assert analysis is not None
        assert analysis.language == "Python"
        assert len(analysis.classes) == 1
        assert analysis.classes[0].name == "DataProcessor"

        # Check methods
        fn_names = [fn.name for fn in analysis.functions]
        assert "DataProcessor.__init__" in fn_names
        assert "DataProcessor.calculate_metrics" in fn_names
        assert "fetch_remote_records" in fn_names
        assert "is_valid_payload" in fn_names

        # Check function commentary
        fetch_fn = next(fn for fn in analysis.functions if fn.name == "fetch_remote_records")
        assert "Retrieves remote dataset" in fetch_fn.commentary

        valid_fn = next(fn for fn in analysis.functions if fn.name == "is_valid_payload")
        assert "Evaluates whether" in valid_fn.commentary or "valid" in valid_fn.commentary.lower()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_04_safety_guardrail_preserves_existing_readme():
    """
    CRITICAL SAFETY TEST:
    Verifies that if a README.md already exists, the agent NEVER replaces it by default,
    and instead writes to README.generated.md!
    """
    temp_dir = tempfile.mkdtemp(prefix="test_repo_safety_")
    try:
        original_readme = os.path.join(temp_dir, "README.md")
        original_content = "# Original Sacred Readme\nDo NOT touch this content!"
        with open(original_readme, "w", encoding="utf-8") as f:
            f.write(original_content)

        with open(os.path.join(temp_dir, "app.py"), "w", encoding="utf-8") as f:
            f.write("def start_server(): pass\n")

        # Run agent without --force
        agent = ReadmeWriterAgent(verbose=False)
        result = agent.run(temp_dir, force=False)

        # 1. Assert original README is 100% UNTOUCHED
        with open(original_readme, "r", encoding="utf-8") as f:
            assert f.read() == original_content

        # 2. Assert output was redirected safely to README.generated.md
        assert result.saved_as_alternate is True
        assert result.was_overwritten is False
        assert os.path.basename(result.output_path) == "README.generated.md"
        assert os.path.exists(result.output_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_05_safety_guardrail_force_overwrite():
    """Verifies that with force=True, overwriting is permitted when explicitly requested."""
    temp_dir = tempfile.mkdtemp(prefix="test_repo_force_")
    try:
        original_readme = os.path.join(temp_dir, "README.md")
        with open(original_readme, "w", encoding="utf-8") as f:
            f.write("# Old Outdated Readme")

        with open(os.path.join(temp_dir, "app.py"), "w", encoding="utf-8") as f:
            f.write("def start_server(): pass\n")

        agent = ReadmeWriterAgent(verbose=False)
        result = agent.run(temp_dir, force=True)

        assert result.was_overwritten is True
        assert result.saved_as_alternate is False
        assert os.path.basename(result.output_path) == "README.md"

        # Assert content was updated
        with open(original_readme, "r", encoding="utf-8") as f:
            new_content = f.read()
            assert "# Old Outdated Readme" not in new_content
            assert "start_server" in new_content
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_06_markdown_generator_sections():
    """Validates that generated markdown includes Mermaid architecture and function table."""
    mock_entity = CodeEntity(
        name="optimize_parameters",
        entity_type="function",
        file_path="optimizer.py",
        line_number=42,
        parameters=["learning_rate", "epochs"],
        commentary="Computes optimized gradient parameters."
    )
    mock_module = ModuleAnalysis(
        file_path="optimizer.py",
        language="Python",
        total_lines=100,
        functions=[mock_entity]
    )
    metadata = RepositoryMetadata(
        repo_name="smart-optimizer",
        repo_path="/mock/smart-optimizer",
        modules=[mock_module],
        all_entities=[mock_entity],
        file_tree_ascii="smart-optimizer/\n└── optimizer.py",
        entry_points=["optimizer.py"]
    )

    generator = ReadmeGenerator(metadata)
    md = generator.generate_markdown()

    assert "# 🚀 Smart Optimizer" in md
    assert "```mermaid" in md
    assert "flowchart TD" in md
    assert "optimizer.py" in md
    assert "optimize_parameters()" in md
    assert "Computes optimized gradient parameters." in md
    assert "## 🛠️ Tech Stack" in md
    assert "## 🚀 Getting Started" in md
    assert "### Prerequisites" in md
    assert "## 📁 Project Structure" in md
    assert "## 🔍 Function & Component Reference Guide" in md
    assert "## 🧭 How to Use" in md
    assert "## 🔮 Future Improvements" in md
    assert "## 🤝 Contributing" in md
    assert "## 📄 License" in md
    assert "## 👨‍💻 Author" in md


def test_07_end_to_end_agent_execution():
    """Tests full end-to-end agent execution on a newly created multi-file repository."""
    temp_dir = tempfile.mkdtemp(prefix="test_repo_e2e_")
    try:
        os.makedirs(os.path.join(temp_dir, "services"), exist_ok=True)
        with open(os.path.join(temp_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write("def main():\n    '''Entry point application execution.'''\n    pass\n")
        with open(os.path.join(temp_dir, "services", "auth.py"), "w", encoding="utf-8") as f:
            f.write("def verify_token(token: str):\n    '''Validates user authentication token.'''\n    return True\n")
        with open(os.path.join(temp_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("requests\npytest\n")

        telemetry = []
        agent = ReadmeWriterAgent(verbose=True)
        agent.register_callback(lambda evt, data: telemetry.append(evt))

        # First run: no README exists -> creates README.md
        result = agent.run(temp_dir)

        assert result.output_path == os.path.join(temp_dir, "README.md")
        assert os.path.exists(result.output_path)
        assert result.entities_documented_count >= 2
        assert "START" in telemetry
        assert "SCAN_COMPLETE" in telemetry
        assert "ANALYSIS_COMPLETE" in telemetry
        assert "SAVED" in telemetry

        # Second run: README now exists -> MUST NOT replace it, must save as README.generated.md!
        result_second = agent.run(temp_dir, force=False)
        assert result_second.saved_as_alternate is True
        assert result_second.output_path == os.path.join(temp_dir, "README.generated.md")
        assert os.path.exists(result_second.output_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    print("=" * 78)
    print("🧪 RUNNING README WRITER AGENT COMPREHENSIVE TEST SUITE")
    print("=" * 78)

    tests = [
        ("Test 1: Repository Scanner & Tree Generation", test_01_scanner_filters_and_tree),
        ("Test 2: Tech Stack & Dependency Detection", test_02_tech_stack_detection),
        ("Test 3: Python AST Parsing & Function Commentary", test_03_ast_analyzer_python),
        ("Test 4: Non-Destructive Guardrail (Preserves Existing README)", test_04_safety_guardrail_preserves_existing_readme),
        ("Test 5: Force Overwrite Authorization Mode", test_05_safety_guardrail_force_overwrite),
        ("Test 6: Markdown Generator & Function Reference Table", test_06_markdown_generator_sections),
        ("Test 7: End-to-End Agent Lifecycle & Multi-File Execution", test_07_end_to_end_agent_execution),
    ]

    passed = 0
    for name, fn in tests:
        try:
            print(f"▶ [{passed + 1}/{len(tests)}] {name}...", end=" ", flush=True)
            fn()
            print("✅ PASS")
            passed += 1
        except Exception as e:
            print(f"❌ FAIL: {e}")
            raise e

    print("=" * 78)
    print(f"📊 Summary: All {passed}/{len(tests)} Tests Passed Successfully!")
    print("=" * 78)


if __name__ == "__main__":
    run_all_tests()
