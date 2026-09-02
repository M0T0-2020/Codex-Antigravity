#!/usr/bin/env python3
"""Tests for structured output parsing."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from antigravity_delegate import parse_structured_output  # type: ignore


class TestOutputParser(unittest.TestCase):
    def test_parse_standard_headings(self):
        sample = """SUMMARY:
This is a concise summary of the findings.

FINDINGS:
- Finding number 1
- Finding number 2
* Finding number 3 with asterisk
1. Finding number 4 with number

SOURCES:
- https://example.com/docs
- https://github.com/repo/releases

UNCERTAINTIES:
- Version 2.0 breaking changes remain unverified.
"""
        result = parse_structured_output(sample)
        self.assertEqual(result["summary"], "This is a concise summary of the findings.")
        self.assertEqual(len(result["findings"]), 4)
        self.assertIn("Finding number 1", result["findings"])
        self.assertIn("Finding number 4 with number", result["findings"])
        self.assertEqual(len(result["sources"]), 2)
        self.assertIn("https://example.com/docs", result["sources"])
        self.assertEqual(len(result["uncertainties"]), 1)
        self.assertIn("Version 2.0 breaking changes remain unverified.", result["uncertainties"])

    def test_parse_markdown_headings(self):
        sample = """## SUMMARY
Markdown heading summary.

### FINDINGS
- Item A
- Item B

### SOURCES
- https://docs.python.org/3/

### UNCERTAINTIES
- None noted.
"""
        result = parse_structured_output(sample)
        self.assertEqual(result["summary"], "Markdown heading summary.")
        self.assertEqual(result["findings"], ["Item A", "Item B"])
        self.assertEqual(result["sources"], ["https://docs.python.org/3/"])
        self.assertEqual(result["uncertainties"], ["None noted."])

    def test_parse_raw_text_fallback(self):
        sample = "Direct answer line 1\nSecond detail line\nThird detail line with https://example.com"
        result = parse_structured_output(sample)
        self.assertEqual(result["summary"], "Direct answer line 1")
        self.assertTrue(len(result["findings"]) >= 1)
        self.assertIn("https://example.com", result["sources"])

    def test_parse_json_wrapped_output(self):
        raw_inner = "SUMMARY:\nInner summary\n\nFINDINGS:\n- Subtask done\n\nSOURCES:\n- https://test.org"
        wrapped = json.dumps({"response": raw_inner})
        result = parse_structured_output(wrapped)
        self.assertEqual(result["summary"], "Inner summary")
        self.assertIn("Subtask done", result["findings"])
        self.assertIn("https://test.org", result["sources"])

    def test_max_chars_truncation(self):
        long_text = "A" * 500
        result = parse_structured_output(long_text, max_chars=100)
        self.assertTrue(len(result["raw_text"]) > 100)
        self.assertIn("[Output truncated at max_output_chars limit]", result["raw_text"])

    def test_parse_claims_section(self):
        sample = """SUMMARY:
ONNX Runtime analysis complete.

CLAIMS:
- Claim: ONNX Runtime 1.18 requires cuDNN 9.x
  Source: https://onnxruntime.ai/docs
  Confidence: high
- Claim: Python 3.8 is deprecated in the latest release
  Source: https://github.com/microsoft/onnxruntime/releases
  Confidence: medium

FINDINGS:
- ONNX Runtime 1.18 requires cuDNN 9.x
- Python 3.8 is deprecated in the latest release

SOURCES:
- https://onnxruntime.ai/docs
- https://github.com/microsoft/onnxruntime/releases
"""
        result = parse_structured_output(sample)
        self.assertIn("claims", result)
        self.assertEqual(len(result["claims"]), 2)
        c1 = result["claims"][0]
        self.assertEqual(c1["claim"], "ONNX Runtime 1.18 requires cuDNN 9.x")
        self.assertEqual(c1["source"], "https://onnxruntime.ai/docs")
        self.assertEqual(c1["confidence"], "high")
        self.assertTrue(c1["verified"])

    def test_parse_claims_synthesized_when_omitted(self):
        sample = """SUMMARY:
Test summary.

FINDINGS:
- Direct finding without explicit claims block

SOURCES:
- https://example.com/source
"""
        result = parse_structured_output(sample)
        self.assertIn("claims", result)
        self.assertEqual(len(result["claims"]), 1)
        self.assertEqual(result["claims"][0]["claim"], "Direct finding without explicit claims block")
        self.assertEqual(result["claims"][0]["source"], "https://example.com/source")


if __name__ == "__main__":
    unittest.main()
