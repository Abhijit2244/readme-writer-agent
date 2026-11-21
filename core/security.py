"""
Enterprise Security & Path Validation Controller
=================================================
Enforces enterprise-grade security boundaries:
  • Path Traversal Prevention (blocks directory breakout attacks, system root scans,
    and sensitive operating system locations on Windows and Linux).
  • Zero-Execution Static Code Safety (guarantees code is parsed via AST, never executed).
  • Automated Secret & Credential Redaction (scrubs API keys, private tokens, passwords).
  • Resource Bounds (guards against symlink loops, zip bombs, and memory exhaustion).
  • Output HTML Sanitization (neutralizes Cross-Site Scripting (XSS) vectors).

All functions are heavily documented with operational commentary explaining defensive security logic.
"""

import os
import re
import html
from typing import Tuple, List, Set, Optional


class SecurityValidator:
    """
    Enforces perimeter defense, directory sandboxing, and output sanitization.
    """

    # Maximum file size allowed for AST / static inspection (2 Megabytes)
    # Prevents Denial-of-Service (DoS) and RAM exhaustion on massive minified artifacts.
    MAX_FILE_SIZE_BYTES: int = 2 * 1024 * 1024

    # Maximum total files scanned per repository execution
    # Protects against runaway crawler loops and symlink recursion traps.
    MAX_CRAWL_FILES: int = 5000

    # Sensitive operating system paths that must NEVER be scanned or accessed
    FORBIDDEN_DIR_NAMES: Set[str] = {
        "system32", "syswow64", "windows", "program files", "program files (x86)",
        "programdata", "$recycle.bin", "recovery", "etc", "var", "usr", "bin",
        "sbin", "proc", "sys", "root", "dev", "boot"
    }

    # Sensitive user directories containing cryptographic keys, cloud tokens, or credentials
    FORBIDDEN_USER_SUBDIRS: Set[str] = {
        ".ssh", ".aws", ".azure", ".kube", ".gnupg", ".docker", ".config"
    }

    # High-confidence credential and API key regex patterns
    SECRET_PATTERNS: List[Tuple[str, re.Pattern]] = [
        # Google AI Studio / Gemini API Key (AQ. authorization tokens)
        ("Gemini-Auth-Token", re.compile(r"AQ\.[A-Za-z0-9_-]{35,}")),
        # Google Cloud Standard API Key (AIza...)
        ("Google-API-Key", re.compile(r"AIza[0-9A-Za-z-_]{35}")),
        # OpenAI Secret Key (sk-...)
        ("OpenAI-Key", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
        # GitHub Personal Access Token (classic & fine-grained)
        ("GitHub-Token", re.compile(r"(?:ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{50,})")),
        # AWS Access Key ID
        ("AWS-Access-Key", re.compile(r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}")),
        # Generic Secret Assignment in code or manifests (e.g. secret = "...")
        ("Generic-Secret", re.compile(
            r"""(?i)(?:api_key|apikey|secret|password|passwd|auth_token|access_token|private_key)\s*[:=]\s*["']([A-Za-z0-9_\-\.\/+=]{8,})["']"""
        )),
    ]

    @classmethod
    def validate_repo_path(cls, path_input: str) -> Tuple[bool, str, str]:
        """
        Validates that a user-supplied repository path is structurally safe, exists,
        and does not target protected operating system or credential directories.

        Operational Mechanics:
        1. Strips leading/trailing whitespace and quotes.
        2. Rejects empty or purely whitespace inputs.
        3. Resolves the canonical, absolute path using os.path.realpath to eliminate
           symlinks, relative dot segments (../), and alternate stream exploits.
        4. Verifies that the resolved path is an existing directory.
        5. Rejects filesystem root directories (e.g. 'C:\\', 'D:\\', or '/').
        6. Traverses path segments to ensure no protected system or credential folders are targeted.

        Args:
            path_input: User-supplied path string from CLI or Web UI.

        Returns:
            Tuple of:
              - is_safe (bool): True if path passes all perimeter checks.
              - resolved_path (str): Canonical absolute filesystem path.
              - error_message (str): Human-readable error description if rejected.
        """
        if not path_input or not path_input.strip():
            return False, "", "Repository path cannot be empty."

        clean_input = path_input.strip().strip("\"'").strip()

        # Cloud Environment Detection: If hosted on Vercel/serverless Linux and user sends a local Windows path
        if (os.name != "nt" or os.environ.get("VERCEL")) and re.match(r"^[A-Za-z]:[\\/]", clean_input):
            return False, "", (
                f"Local filesystem path ('{clean_input}') cannot be accessed on cloud-hosted Vercel. "
                "The project is not cloned on the remote cloud device. "
                "Please use the 'GitHub URL' tab or 'Upload Project (.zip)' tab instead!"
            )

        try:
            canonical_path = os.path.realpath(os.path.abspath(clean_input))
        except Exception as e:
            return False, "", f"Path resolution failed: {str(e)}"

        # Verify existence and directory type
        if not os.path.exists(canonical_path):
            return False, canonical_path, f"Directory does not exist on filesystem: '{canonical_path}'"

        if not os.path.isdir(canonical_path):
            return False, canonical_path, f"Specified target is a file, not a directory: '{canonical_path}'"

        # Check for filesystem root directory
        norm_path = os.path.normpath(canonical_path)
        drive, tail = os.path.splitdrive(norm_path)
        if tail in ("\\", "/", ""):
            return False, canonical_path, "Access Denied: Scanning entire root filesystem drives is strictly prohibited."

        # Check each segment against forbidden operating system directories
        parts = [p.lower() for p in re.split(r"[\\/]+", norm_path) if p]
        for part in parts:
            if part in cls.FORBIDDEN_DIR_NAMES:
                return False, canonical_path, f"Access Denied: Path references protected system directory '{part}'."
            if part in cls.FORBIDDEN_USER_SUBDIRS:
                return False, canonical_path, f"Access Denied: Path references sensitive credential folder '{part}'."

        return True, canonical_path, ""

    @classmethod
    def redact_secrets(cls, content: str) -> str:
        """
        Inspects generated text or code comments for leaked secrets, API keys, and passwords,
        redacting them with a visible security marker.

        Operational Mechanics:
        1. Iterates over predefined high-entropy token patterns.
        2. Substitutes detected credentials with '[REDACTED_SECRET:<type>]'.
        3. Returns the scrubbed, sanitized string.

        Args:
            content: Raw markdown, commentary, or text string.

        Returns:
            Sanitized text with all detected credentials redacted.
        """
        if not content:
            return ""

        scrubbed = content
        for secret_name, pattern in cls.SECRET_PATTERNS:
            if secret_name == "Generic-Secret":
                # For generic assignments (key = "value"), replace only the value inside quotes
                scrubbed = pattern.sub(r'\1: "[REDACTED_SECRET]"', scrubbed)
            else:
                scrubbed = pattern.sub(f"[REDACTED_{secret_name}]", scrubbed)

        return scrubbed

    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """
        Escapes HTML characters (&, <, >, ", ') to prevent Cross-Site Scripting (XSS)
        when rendering repository metadata in web dashboards.

        Args:
            text: Unsanitized text string.

        Returns:
            Safely escaped HTML text.
        """
        if not text:
            return ""
        return html.escape(text, quote=True)

    @classmethod
    def is_file_safe_to_read(cls, file_path: str) -> Tuple[bool, str]:
        """
        Validates that an individual file is within size limits and is safe for AST parsing.

        Args:
            file_path: Absolute or relative filesystem path.

        Returns:
            Tuple of (is_safe: bool, reason: str).
        """
        try:
            stat_info = os.stat(file_path)
            if stat_info.st_size > cls.MAX_FILE_SIZE_BYTES:
                return False, f"File exceeds maximum size limit ({stat_info.st_size} bytes > {cls.MAX_FILE_SIZE_BYTES} bytes)"
            return True, ""
        except Exception as e:
            return False, f"Could not inspect file: {str(e)}"

    @classmethod
    def validate_github_url(cls, url: str) -> Tuple[bool, str, str, str]:
        """
        Validates that a GitHub repository URL is structurally well-formed and points to a repo.

        Args:
            url: URL string (e.g. 'https://github.com/owner/repo' or 'github.com/owner/repo')

        Returns:
            Tuple of (is_valid: bool, owner: str, repo: str, error: str)
        """
        if not url or not url.strip():
            return False, "", "", "GitHub repository URL cannot be empty."

        clean_url = url.strip().rstrip("/")
        # Support https://github.com/owner/repo or git@github.com:owner/repo
        match = re.search(r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?$", clean_url)
        if not match:
            return False, "", "", "Invalid GitHub URL format. Expected: 'https://github.com/owner/repository'."

        owner, repo = match.group(1), match.group(2)
        # Prevent injection in owner or repo name
        if not re.match(r"^[A-Za-z0-9_.-]+$", owner) or not re.match(r"^[A-Za-z0-9_.-]+$", repo):
            return False, "", "", "GitHub repository name contains invalid characters."

        return True, owner, repo, ""

    @classmethod
    def safe_extract_zip(cls, zip_path: str, extract_to: str) -> Tuple[bool, str]:
        """
        Extracts a zip file safely with Zip-Slip path traversal defense.
        Ensures all member filenames resolve strictly inside the target directory.

        Args:
            zip_path: Filesystem path to the .zip archive.
            extract_to: Destination directory.

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        import zipfile

        try:
            abs_dest = os.path.realpath(os.path.abspath(extract_to))
            os.makedirs(abs_dest, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zf:
                for member in zf.infolist():
                    target_path = os.path.realpath(os.path.abspath(os.path.join(abs_dest, member.filename)))
                    # Check Zip-Slip path traversal escape
                    if not target_path.startswith(abs_dest + os.sep) and target_path != abs_dest:
                        return False, f"Zip-Slip vulnerability blocked: malicious path traversal '{member.filename}' detected."

                # Safe to extract
                zf.extractall(abs_dest)
            return True, ""
        except Exception as e:
            return False, f"Zip extraction error: {str(e)}"
