"""Static AST & CST Code Efficiency Analyzer."""

import os
from typing import Any, Dict
from app.parser import audit_file, audit_repository


class CodeAnalyzer:
    """Invokes AST multi-language parsing on project repositories."""

    @classmethod
    def scan_path(cls, path: str) -> Dict[str, Any]:
        """Perform static carbon and energy analysis on file or folder."""
        if os.path.isfile(path):
            return audit_file(path)
        elif os.path.isdir(path):
            return audit_repository(path)
        return {
            "total_files": 0,
            "total_lines": 0,
            "green_score": 100.0,
            "violations": [],
            "total_energy_joules": 0.05,
        }
