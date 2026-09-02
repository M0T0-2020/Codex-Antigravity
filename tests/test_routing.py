#!/usr/bin/env python3
"""Tests for configuration loading and routing heuristics."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from config_loader import load_config, parse_toml, deep_merge  # type: ignore
from models import resolve_model  # type: ignore


class TestRoutingAndConfig(unittest.TestCase):
    def test_load_default_config(self):
        cfg = load_config()
        self.assertTrue(cfg["antigravity"]["enabled"])
        self.assertEqual(cfg["antigravity"]["default_effort"], "low")
        self.assertEqual(cfg["antigravity"]["timeout_seconds"], 120)
        self.assertEqual(cfg["antigravity"]["max_parallel"], 3)
        self.assertTrue(cfg["routing"]["web_research"])
        self.assertTrue(cfg["routing"]["codebase_status"])
        self.assertTrue(cfg["routing"]["test_execution"])
        self.assertTrue(cfg["routing"]["test_failure_diagnosis"])
        self.assertFalse(cfg["routing"]["code_implementation"])
        self.assertTrue(cfg["safety"]["readonly_enforced"])
        self.assertTrue(cfg["codebase"]["enabled"])
        self.assertTrue(cfg["testing"]["enabled"])
        self.assertEqual(cfg["testing"]["default_timeout_seconds"], 180)

    def test_toml_parser_types(self):
        sample_toml = """
        [test_section]
        str_val = "hello"
        int_val = 42
        float_val = 3.14
        bool_val = true
        list_val = ["a", "b", "c"]
        """
        data = parse_toml(sample_toml)
        sec = data["test_section"]
        self.assertEqual(sec["str_val"], "hello")
        self.assertEqual(sec["int_val"], 42)
        self.assertEqual(sec["float_val"], 3.14)
        self.assertEqual(sec["bool_val"], True)
        self.assertEqual(sec["list_val"], ["a", "b", "c"])

    def test_deep_merge(self):
        base = {"a": 1, "nested": {"x": 10, "y": 20}}
        override = {"nested": {"y": 99, "z": 100}, "b": 2}
        merged = deep_merge(base, override)
        self.assertEqual(merged["a"], 1)
        self.assertEqual(merged["b"], 2)
        self.assertEqual(merged["nested"]["x"], 10)
        self.assertEqual(merged["nested"]["y"], 99)
        self.assertEqual(merged["nested"]["z"], 100)

    def test_model_resolution(self):
        # flash alias
        resolved_flash = resolve_model("flash")
        self.assertEqual(resolved_flash, "gemini-3.8-flash-high")

        # pro alias
        resolved_pro = resolve_model("pro")
        self.assertEqual(resolved_pro, "gemini-3.1-pro-high")

        # Config mapping override
        cfg_models = {"research": "gemini-flash-custom"}
        resolved_custom = resolve_model("research", config_models=cfg_models)
        self.assertEqual(resolved_custom, "gemini-flash-custom")


if __name__ == "__main__":
    unittest.main()
