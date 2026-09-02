#!/usr/bin/env python3
"""Tests for Codebase Analyzer."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from codebase_analyzer import (  # type: ignore
    analyze_codebase,
    detect_project_stack,
    detect_test_setup,
    format_codebase_context,
    get_directory_tree,
    get_git_status_summary,
)


class TestCodebaseAnalyzer(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.proj_dir = self.tmp_dir.name

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_detect_project_stack_python(self):
        with open(os.path.join(self.proj_dir, "pyproject.toml"), "w") as f:
            f.write('[project]\nname = "demo"\ndependencies = ["fastapi", "pydantic"]\n')

        stack = detect_project_stack(self.proj_dir)
        self.assertIn("Python", stack["languages"])
        self.assertIn("pyproject.toml", stack["manifests"])
        self.assertIn("fastapi", stack["frameworks"])
        self.assertEqual(stack["test_runner"], "pytest")

    def test_detect_project_stack_rust(self):
        with open(os.path.join(self.proj_dir, "Cargo.toml"), "w") as f:
            f.write('[package]\nname = "demo"\n[dependencies]\ntokio = "1.0"\n')

        stack = detect_project_stack(self.proj_dir)
        self.assertIn("Rust", stack["languages"])
        self.assertIn("Cargo.toml", stack["manifests"])
        self.assertIn("tokio", stack["frameworks"])
        self.assertEqual(stack["test_runner"], "cargo test")

    def test_get_directory_tree(self):
        os.makedirs(os.path.join(self.proj_dir, "src", "core"))
        with open(os.path.join(self.proj_dir, "src", "main.py"), "w") as f:
            f.write("print('hello')\n")
        with open(os.path.join(self.proj_dir, "src", "core", "utils.py"), "w") as f:
            f.write("pass\n")

        tree = get_directory_tree(self.proj_dir, max_depth=3)
        tree_text = "\n".join(tree)
        self.assertIn("src/", tree_text)
        self.assertIn("core/", tree_text)
        self.assertIn("main.py", tree_text)

    def test_detect_test_setup(self):
        os.makedirs(os.path.join(self.proj_dir, "tests"))
        with open(os.path.join(self.proj_dir, "tests", "test_app.py"), "w") as f:
            f.write("def test_ok(): pass\n")

        test_info = detect_test_setup(self.proj_dir)
        self.assertTrue(test_info["has_tests"])
        self.assertIn("tests", test_info["test_dirs"])
        self.assertEqual(test_info["test_count"], 1)

    def test_format_codebase_context(self):
        analysis = {
            "project_name": "sample-project",
            "project_dir": "/path/to/sample",
            "stack": {
                "languages": ["Python", "Rust"],
                "frameworks": ["fastapi"],
                "manifests": ["pyproject.toml"],
                "test_runner": "pytest",
            },
            "git": {
                "is_git": True,
                "branch": "main",
                "dirty": False,
                "modified_files": [],
            },
            "tests": {
                "has_tests": True,
                "test_count": 8,
            },
            "tree": ["├── src/", "└── README.md"],
        }
        ctx = format_codebase_context(analysis)
        self.assertIn("sample-project", ctx)
        self.assertIn("Python, Rust", ctx)
        self.assertIn("fastapi", ctx)
        self.assertIn("branch `main`", ctx)
        self.assertIn("8 test files detected", ctx)
        self.assertIn("├── src/", ctx)


if __name__ == "__main__":
    unittest.main()
