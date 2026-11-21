"""
Safety & File Preservation Controller
=====================================
Enforces non-destructive safety guardrails. Checks for existing README documentation
and guarantees that existing files are never overwritten without explicit permission.

All functions contain comprehensive educational commentary on safe file lifecycle handling.
"""

import os
from typing import Tuple, Optional


class ReadmeSafetyController:
    """
    Guarantees non-destructive operation when inspecting and generating documentation.
    """

    README_VARIANTS = [
        "README.md", "readme.md", "README.markdown", "Readme.md",
        "README.rst", "README.txt", "readme.txt"
    ]

    def __init__(self, repo_path: str):
        """
        Initializes the safety controller.

        Args:
            repo_path: Filesystem path to root directory of the inspected repository.
        """
        self.repo_path = os.path.abspath(repo_path)

    def check_existing_readme(self) -> Tuple[bool, Optional[str]]:
        """
        Checks whether any variant of a README file already exists in the repository.

        Operational Mechanics:
        1. Iterates through common uppercase, lowercase, and markdown/rst filename variants.
        2. Tests filesystem existence using os.path.isfile.
        3. Returns a tuple: (has_existing_readme: bool, existing_path: Optional[str]).

        Returns:
            Tuple containing boolean existence flag and absolute path to existing file if found.
        """
        for variant in self.README_VARIANTS:
            candidate_path = os.path.join(self.repo_path, variant)
            if os.path.isfile(candidate_path):
                return True, candidate_path
        return False, None

    def resolve_target_output_path(self, force_overwrite: bool = False, custom_output_name: Optional[str] = None) -> Tuple[str, bool, bool]:
        """
        Determines the safe filesystem path where the generated README will be saved.

        Operational Mechanics:
        1. If a custom output filename is explicitly requested by the caller, uses that path.
        2. If NO existing README is present in the repository, safely returns 'README.md'.
        3. If an existing README IS PRESENT:
           - If force_overwrite is True (via explicit --force flag): targets 'README.md'
             with overwrite warning.
           - If force_overwrite is False (DEFAULT SAFE BEHAVIOR): preserves the existing
             original README untouched and targets 'README.generated.md' instead.
        4. Returns a 3-element tuple:
           (target_path, was_overwritten, saved_as_alternate).

        Args:
            force_overwrite: Boolean flag indicating if caller explicitly permitted overwriting.
            custom_output_name: Optional custom output filename.

        Returns:
            Tuple of (output_path: str, will_overwrite: bool, is_alternate: bool).
        """
        if custom_output_name:
            target_path = os.path.join(self.repo_path, custom_output_name)
            return target_path, False, False

        has_readme, existing_path = self.check_existing_readme()

        if not has_readme:
            # Safe default: no previous file exists, standard README.md is created
            target_path = os.path.join(self.repo_path, "README.md")
            return target_path, False, False

        # Existing README detected!
        if force_overwrite:
            # Caller explicitly authorized overwriting the existing file
            target_path = existing_path or os.path.join(self.repo_path, "README.md")
            return target_path, True, False

        # Non-destructive default: preserve existing README, save as README.generated.md
        safe_alternate_path = os.path.join(self.repo_path, "README.generated.md")
        return safe_alternate_path, False, True
