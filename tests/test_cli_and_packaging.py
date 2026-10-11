"""Tests for pre-commit hook definitions, pyproject.toml v2.0.0 packaging, and FastAPI version."""

import os
from app.main import app


def test_pre_commit_hooks_and_pyproject_v2():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    hooks_path = os.path.join(root, ".pre-commit-hooks.yaml")
    pyproject_path = os.path.join(root, "pyproject.toml")

    assert os.path.isfile(hooks_path)
    with open(hooks_path, "r", encoding="utf-8") as f:
        hooks_text = f.read()
    assert "id: greencode-audit" in hooks_text
    assert "id: greencode-iac" in hooks_text

    assert os.path.isfile(pyproject_path)
    with open(pyproject_path, "r", encoding="utf-8") as f:
        pyproject_text = f.read()
    assert 'version = "2.0.0"' in pyproject_text
    assert "Typing :: Typed" in pyproject_text
    assert app.version == "2.0.0"

