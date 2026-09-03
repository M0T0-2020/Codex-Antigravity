#!/usr/bin/env python3
"""Tests for Quality Gate."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from quality_gate import evaluate_quality, QualityDecision  # type: ignore


class TestQualityGate(unittest.TestCase):
    def test_quality_gate_high_quality_pass(self):
        good_result = {
            "success": True,
            "summary": "ONNX Runtime latest version 1.18.0 verified with CUDA 12.x support.",
            "claims": [
                {
                    "claim": "ONNX Runtime 1.18.0 requires CUDA 12.x",
                    "source": "https://onnxruntime.ai/docs/requirements",
                    "confidence": "high",
                    "self_confidence": "high",
                    "verification_status": "source_retrieved",
                    "evidence": {"type": "official_docs", "source": "https://onnxruntime.ai/docs/requirements"},
                },
                {
                    "claim": "cuDNN 9.x is required for GPU acceleration in ORT 1.18",
                    "source": "https://github.com/microsoft/onnxruntime/releases/tag/v1.18.0",
                    "confidence": "high",
                    "self_confidence": "high",
                    "verification_status": "source_retrieved",
                    "evidence": {"type": "official_docs", "source": "https://github.com/microsoft/onnxruntime/releases/tag/v1.18.0"},
                },
                {
                    "claim": "Python 3.12 wheel packages are officially distributed on PyPI",
                    "source": "https://pypi.org/project/onnxruntime",
                    "confidence": "high",
                    "self_confidence": "high",
                    "verification_status": "source_provided",
                    "evidence": {"type": "web", "source": "https://pypi.org/project/onnxruntime"},
                },
            ],
            "findings": [
                "ONNX Runtime 1.18.0 requires CUDA 12.x",
                "cuDNN 9.x is required",
                "Python 3.12 wheel packages available",
            ],
            "sources": [
                "https://onnxruntime.ai/docs/requirements",
                "https://github.com/microsoft/onnxruntime/releases/tag/v1.18.0",
                "https://pypi.org/project/onnxruntime",
            ],
            "uncertainties": [],
        }

        res = evaluate_quality(good_result)
        self.assertGreaterEqual(res.score, 0.70)
        self.assertEqual(res.decision, QualityDecision.PASS)
        self.assertEqual(res.metrics["uncertainty_ratio"], 0.0)

    def test_quality_gate_moderate_quality_needs_review(self):
        moderate_result = {
            "success": True,
            "summary": "Basic findings with partial documentation.",
            "claims": [
                {
                    "claim": "Library works on Linux with flag --compat",
                    "source": "https://github.com/example/repo",
                    "confidence": "medium",
                    "self_confidence": "medium",
                    "verification_status": "source_retrieved",
                    "evidence": {"type": "github_repo", "source": "https://github.com/example/repo"},
                },
                {
                    "claim": "Secondary note from user forum",
                    "source": "https://example.com/forum",
                    "confidence": "medium",
                    "self_confidence": "medium",
                    "verification_status": "source_provided",
                    "evidence": {"type": "web", "source": "https://example.com/forum"},
                },
            ],
            "findings": ["Finding 1", "Finding 2"],
            "sources": ["https://github.com/example/repo", "https://example.com/forum"],
            "uncertainties": ["Check version 2 details"],
        }

        res = evaluate_quality(moderate_result)
        self.assertGreaterEqual(res.score, 0.40)
        self.assertLess(res.score, 0.70)
        self.assertEqual(res.decision, QualityDecision.NEEDS_REVIEW)

    def test_quality_gate_low_quality_poor(self):
        poor_result = {
            "success": True,
            "summary": "Vague answer with no primary documentation.",
            "claims": [
                {
                    "claim": "Maybe some CUDA version works",
                    "source": "",
                    "confidence": "low",
                    "self_confidence": "low",
                    "verification_status": "unverified",
                    "evidence": {"type": "inferred", "source": ""},
                },
            ],
            "findings": ["Uncertain findings"],
            "sources": [],
            "uncertainties": [
                "Not sure about CUDA 12 support",
                "Release notes were not checked",
                "Compatibility is unknown",
            ],
        }

        res = evaluate_quality(poor_result)
        self.assertLess(res.score, 0.40)
        self.assertEqual(res.decision, QualityDecision.POOR)
        self.assertTrue(len(res.reasons) > 0)


if __name__ == "__main__":
    unittest.main()
