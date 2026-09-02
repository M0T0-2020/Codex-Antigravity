#!/usr/bin/env python3
"""Tests for Antigravity MCP Server."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mcp"))
from server import handle_json_rpc, TOOLS, SERVER_INFO  # type: ignore


class TestMCPServer(unittest.TestCase):
    def test_initialize(self):
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        }
        res = handle_json_rpc(req)
        self.assertEqual(res["id"], 1)
        self.assertEqual(res["result"]["serverInfo"]["name"], "antigravity-mcp-server")
        self.assertIn("tools", res["result"]["capabilities"])

    def test_tools_list(self):
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
        }
        res = handle_json_rpc(req)
        self.assertEqual(res["id"], 2)
        tools = res["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        self.assertIn("antigravity_research", tool_names)
        self.assertIn("antigravity_list_models", tool_names)
        self.assertIn("antigravity_compare", tool_names)
        self.assertIn("antigravity_inspect_docs", tool_names)
        self.assertIn("antigravity_inspect_repo", tool_names)
        self.assertIn("antigravity_inspect_codebase", tool_names)
        self.assertIn("antigravity_run_tests", tool_names)
        self.assertIn("antigravity_diagnose_failure", tool_names)

    def test_tools_call_list_models(self):
        req = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "antigravity_list_models",
                "arguments": {
                    "query": "flash",
                },
            },
        }
        res = handle_json_rpc(req, mock=True)
        self.assertEqual(res["id"], 10)
        self.assertFalse(res["result"]["isError"])
        content = res["result"]["content"][0]["text"]
        self.assertIn("Summary", content)

    def test_tools_call_research(self):
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "antigravity_research",
                "arguments": {
                    "query": "What is the latest ONNX runtime version?",
                    "depth": "quick",
                    "model": "flash",
                },
            },
        }
        res = handle_json_rpc(req, mock=True)
        self.assertEqual(res["id"], 3)
        self.assertFalse(res["result"]["isError"])
        content = res["result"]["content"][0]["text"]
        self.assertIn("### Summary", content)
        self.assertIn("### Findings", content)
        self.assertIn("### Sources", content)

    def test_tools_call_compare(self):
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "antigravity_compare",
                "arguments": {
                    "item_a": "FastAPI",
                    "item_b": "Flask",
                },
            },
        }
        res = handle_json_rpc(req, mock=True)
        self.assertEqual(res["id"], 4)
        self.assertFalse(res["result"]["isError"])

    def test_tools_call_inspect_codebase(self):
        req = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "antigravity_inspect_codebase",
                "arguments": {
                    "path": ".",
                    "focus": "codebase",
                },
            },
        }
        res = handle_json_rpc(req, mock=True)
        self.assertEqual(res["id"], 5)
        self.assertFalse(res["result"]["isError"])
        content = res["result"]["content"][0]["text"]
        self.assertIn("Codebase", content)

    def test_tools_call_run_tests(self):
        req = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "antigravity_run_tests",
                "arguments": {
                    "path": ".",
                },
            },
        }
        res = handle_json_rpc(req, mock=True)
        self.assertEqual(res["id"], 6)
        self.assertFalse(res["result"]["isError"])
        content = res["result"]["content"][0]["text"]
        self.assertIn("Test Execution Status", content)

    def test_tools_call_diagnose_failure(self):
        req = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "antigravity_diagnose_failure",
                "arguments": {
                    "error_trace": "AssertionError: 200 != 404 in test_api",
                },
            },
        }
        res = handle_json_rpc(req, mock=True)
        self.assertEqual(res["id"], 7)
        self.assertFalse(res["result"]["isError"])

    def test_tools_call_run_tests_structured(self):
        req = {
            "jsonrpc": "2.0",
            "id": 61,
            "method": "tools/call",
            "params": {
                "name": "antigravity_run_tests",
                "arguments": {
                    "path": ".",
                    "runner": "pytest",
                    "args": ["-v", "tests/test_routing.py"],
                },
            },
        }
        res = handle_json_rpc(req, mock=True)
        self.assertEqual(res["id"], 61)
        self.assertFalse(res["result"]["isError"])
        content = res["result"]["content"][0]["text"]
        self.assertIn("Test Execution Status", content)

    def test_tools_call_run_tests_boundary_violation(self):
        req = {
            "jsonrpc": "2.0",
            "id": 62,
            "method": "tools/call",
            "params": {
                "name": "antigravity_run_tests",
                "arguments": {
                    "path": "../../outside",
                },
            },
        }
        res = handle_json_rpc(req, mock=False)
        self.assertEqual(res["id"], 62)
        content = res["result"]["content"][0]["text"]
        self.assertIn("boundary violation", content.lower())

    def test_tools_call_research_renders_claims(self):
        req = {
            "jsonrpc": "2.0",
            "id": 63,
            "method": "tools/call",
            "params": {
                "name": "antigravity_research",
                "arguments": {
                    "query": "Check API stability",
                },
            },
        }
        res = handle_json_rpc(req, mock=True)
        self.assertEqual(res["id"], 63)
        self.assertFalse(res["result"]["isError"])
        content = res["result"]["content"][0]["text"]
        self.assertIn("Claims & Evidence", content)

    def test_unknown_method(self):
        req = {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "non_existent_method",
        }
        res = handle_json_rpc(req)
        self.assertEqual(res["error"]["code"], -32601)

    def test_invalid_rpc(self):
        req = {"not": "rpc"}
        res = handle_json_rpc(req)
        self.assertEqual(res["error"]["code"], -32600)


if __name__ == "__main__":
    unittest.main()
