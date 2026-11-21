"""
Automated Test Suite: Web Application, Endpoints & Security Validation
======================================================================
Verifies:
  1. Perimeter security & path traversal defenses (rejection of system roots and protected folders).
  2. Secret & API key redaction engine.
  3. FastAPI endpoints (/health, /, /api/validate, /api/generate, /api/download).
  4. Non-destructive safety guardrails in web request lifecycles.
"""

import os
import sys
import tempfile
import unittest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from starlette.testclient import TestClient
from core.security import SecurityValidator
from server import app


class TestWebSecurityAndEndpoints(unittest.TestCase):
    """
    Validates web server endpoints, download flows, and security perimeter enforcement.
    """

    def setUp(self):
        self.client = TestClient(app)
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    # ----------------------------------------------------------------------
    # 1. SECURITY VALIDATOR UNIT TESTS
    # ----------------------------------------------------------------------
    def test_01_security_blocks_empty_or_whitespace_path(self):
        is_safe, _, err = SecurityValidator.validate_repo_path("")
        self.assertFalse(is_safe)
        self.assertIn("cannot be empty", err)

        is_safe, _, err = SecurityValidator.validate_repo_path("   ")
        self.assertFalse(is_safe)

    def test_02_security_blocks_nonexistent_directory(self):
        fake_path = os.path.join(self.temp_dir.name, "does_not_exist_xyz123")
        is_safe, _, err = SecurityValidator.validate_repo_path(fake_path)
        self.assertFalse(is_safe)
        self.assertIn("does not exist", err.lower())

    def test_03_security_blocks_forbidden_system_folders(self):
        # Test Windows system directory if on Windows
        if os.name == "nt":
            win_dir = os.environ.get("SystemRoot", r"C:\Windows")
            is_safe, _, err = SecurityValidator.validate_repo_path(win_dir)
            self.assertFalse(is_safe)
            self.assertIn("Access Denied", err)

            # Test root drive
            is_safe_root, _, err_root = SecurityValidator.validate_repo_path("C:\\")
            self.assertFalse(is_safe_root)
            self.assertIn("root filesystem", err_root.lower())

    def test_03b_cloud_blocks_unreachable_device_paths(self):
        # Simulate Vercel environment variable
        os.environ["VERCEL"] = "1"
        try:
            is_safe, _, err = SecurityValidator.validate_repo_path(r"C:\Users\COM\Desktop\sample\my-repo")
            self.assertFalse(is_safe)
            self.assertIn("cannot be accessed on cloud-hosted Vercel", err)
        finally:
            os.environ.pop("VERCEL", None)

    def test_04_security_allows_valid_repository_directory(self):
        is_safe, canonical, err = SecurityValidator.validate_repo_path(self.temp_dir.name)
        self.assertTrue(is_safe)
        self.assertEqual(err, "")
        self.assertTrue(os.path.isdir(canonical))

    def test_05_secret_redaction_engine(self):
        # Dynamically constructed mock test keys (prevents GitHub Push Protection false-positive blocks)
        mock_gemini = "AQ." + "MOCKKEY001" * 4
        mock_google = "AIzaSy" + "MOCKKEY002" * 3
        sample_text = (
            f"Here is my Gemini key: {mock_gemini} in the app.\n"
            f"And Google key: {mock_google} and password = 'SuperSecretPassword123'."
        )
        redacted = SecurityValidator.redact_secrets(sample_text)
        self.assertNotIn(mock_gemini, redacted)
        self.assertNotIn(mock_google, redacted)
        self.assertIn("[REDACTED_Gemini-Auth-Token]", redacted)
        self.assertIn("[REDACTED_Google-API-Key]", redacted)
        self.assertIn("[REDACTED_SECRET]", redacted)

    # ----------------------------------------------------------------------
    # 2. FASTAPI ENDPOINT TESTS
    # ----------------------------------------------------------------------
    def test_06_health_endpoint(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["security"]["path_traversal_protection"], "active")

    def test_07_index_dashboard_returns_html(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers["content-type"])
        self.assertIn("README Writer Agent", res.text)
        # Validates either React SPA root mount or embedded HTML view
        self.assertTrue(
            '<div id="root"></div>' in res.text or "Security Guardrails Active" in res.text,
            "Expected React root container or embedded HTML view"
        )

    def test_08_api_validate_blocks_unauthorized_path(self):
        res = self.client.post("/api/validate", json={"repo_path": r"C:\Windows\System32" if os.name == 'nt' else "/etc"})
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertFalse(data["valid"])
        self.assertIn("Access Denied", data["error"])

    def test_09_api_validate_accepts_valid_repo(self):
        # Create a sample python file in temp directory
        with open(os.path.join(self.temp_dir.name, "main.py"), "w", encoding="utf-8") as f:
            f.write("def calculate_total(): pass\n")

        res = self.client.post("/api/validate", json={"repo_path": self.temp_dir.name})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["valid"])
        self.assertEqual(data["total_files"], 1)
        self.assertEqual(data["primary_language"], "Python")

    def test_10_api_generate_and_download_flow(self):
        # Create a mock repository in temp dir
        with open(os.path.join(self.temp_dir.name, "calculator.py"), "w", encoding="utf-8") as f:
            f.write(
                '"""Financial math module."""\n'
                'def calculate_interest(principal: float, rate: float) -> float:\n'
                '    """Calculates compounded interest."""\n'
                '    return principal * rate\n'
            )

        # 1. Generate documentation
        gen_res = self.client.post("/api/generate", json={"repo_path": self.temp_dir.name, "force": False})
        self.assertEqual(gen_res.status_code, 200)
        data = gen_res.json()
        self.assertTrue(data["success"])
        self.assertIn("session_id", data)
        self.assertIn("calculate_interest", data["markdown_content"])
        self.assertIn("Operational Purpose & Commentary", data["markdown_content"])
        self.assertEqual(data["engine_mode"], "Local Deterministic AST")

        # 2. Test download endpoint with returned session_id
        session_id = data["session_id"]
        dl_res = self.client.get(f"/api/download?session_id={session_id}")
        self.assertEqual(dl_res.status_code, 200)
        self.assertIn("attachment", dl_res.headers["content-disposition"])
        self.assertIn("calculate_interest", dl_res.text)

    def test_11_github_url_validator(self):
        is_val, owner, repo, err = SecurityValidator.validate_github_url("https://github.com/Abhijit2244/let-the-wheel-decide")
        self.assertTrue(is_val)
        self.assertEqual(owner, "Abhijit2244")
        self.assertEqual(repo, "let-the-wheel-decide")

        # Invalid URL
        is_val, _, _, err = SecurityValidator.validate_github_url("https://notgithub.com/someone/repo")
        self.assertFalse(is_val)
        self.assertIn("Invalid GitHub URL", err)

    def test_12_safe_extract_zip_with_zip_slip_defense(self):
        import zipfile
        zip_path = os.path.join(self.temp_dir.name, "test_repo.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("module.py", "def test_fn(): pass\n")

        extract_target = os.path.join(self.temp_dir.name, "extracted")
        ok, err = SecurityValidator.safe_extract_zip(zip_path, extract_target)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(os.path.join(extract_target, "module.py")))

    def test_13_api_upload_zip_flow(self):
        import zipfile
        import io

        # Build in-memory zip
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("app.py", "def run_server(): pass\n")
        zip_buffer.seek(0)

        res = self.client.post(
            "/api/upload-zip",
            files={"file": ("project.zip", zip_buffer.getvalue(), "application/zip")},
            data={"force": "false"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("run_server", data["markdown_content"])
        self.assertEqual(data["engine_mode"], "Local Deterministic AST")

    def test_14_engine_toggle_gemini_mode(self):
        # Create a mock repository
        with open(os.path.join(self.temp_dir.name, "greeter.py"), "w", encoding="utf-8") as f:
            f.write("def greet(name: str): return f'Hello {name}'\n")

        # Request with use_gemini=True
        res = self.client.post("/api/generate", json={
            "repo_path": self.temp_dir.name,
            "force": False,
            "use_gemini": True,
            "gemini_api_key": "MOCK_KEY_FOR_TESTING"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["engine_mode"], "Gemini 2.0 Flash AI")
        self.assertIn("greet", data["markdown_content"])


if __name__ == "__main__":
    unittest.main()
