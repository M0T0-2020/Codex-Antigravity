#!/usr/bin/env python3
"""Tests for Evidence Merger and Conflict Detection."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from evidence_merger import merge_evidence, ClaimStatus  # type: ignore


class TestEvidenceMerger(unittest.TestCase):
    def test_evidence_merge_deduplication(self):
        subtasks = [
            {
                "task": "research_1",
                "summary": "ORT CUDA support findings",
                "claims": [
                    {
                        "claim": "ONNX Runtime supports CUDA 12.x on Linux",
                        "source": "https://onnxruntime.ai/docs",
                        "confidence": "high",
                    }
                ],
                "findings": ["ONNX Runtime supports CUDA 12.x on Linux"],
                "sources": ["https://onnxruntime.ai/docs"],
                "uncertainties": [],
            },
            {
                "task": "research_2",
                "summary": "GitHub release inspection",
                "claims": [
                    {
                        "claim": "ONNX Runtime supports CUDA 12.x on Linux x86_64",
                        "source": "https://github.com/microsoft/onnxruntime/releases",
                        "confidence": "high",
                    }
                ],
                "findings": ["ONNX Runtime supports CUDA 12.x on Linux x86_64"],
                "sources": ["https://github.com/microsoft/onnxruntime/releases"],
                "uncertainties": [],
            },
        ]

        packet = merge_evidence(subtasks)
        self.assertFalse(packet.has_conflicts)
        self.assertEqual(len(packet.claims), 1)  # Deduplicated into 1 claim
        self.assertEqual(len(packet.claims[0].sources), 2)  # Sources aggregated
        self.assertIn("research_1", packet.claims[0].subtasks)
        self.assertIn("research_2", packet.claims[0].subtasks)

    def test_conflict_detection_version_discrepancy(self):
        subtasks = [
            {
                "task": "scout_a",
                "summary": "Doc scout",
                "claims": [
                    {
                        "claim": "Library requires Python 3.12 for all features",
                        "source": "https://example.com/docs",
                        "confidence": "high",
                    }
                ],
                "findings": [],
                "sources": [],
                "uncertainties": [],
            },
            {
                "task": "scout_b",
                "summary": "Issue scout",
                "claims": [
                    {
                        "claim": "Library requires Python 3.9 for all features",
                        "source": "https://github.com/example/issues/100",
                        "confidence": "high",
                    }
                ],
                "findings": [],
                "sources": [],
                "uncertainties": [],
            },
        ]

        packet = merge_evidence(subtasks)
        self.assertTrue(packet.has_conflicts)
        self.assertEqual(len(packet.conflicts), 1)
        self.assertIn("Conflicting versions", packet.conflicts[0]["reason"])
        self.assertEqual(packet.claims[0].status, ClaimStatus.CONFLICTING)

    def test_conflict_detection_polarity(self):
        subtasks = [
            {
                "task": "scout_a",
                "summary": "Release scout",
                "claims": [
                    {
                        "claim": "CUDA execution provider is supported and enabled",
                        "source": "https://example.com/docs",
                    }
                ],
                "findings": [],
                "sources": [],
                "uncertainties": [],
            },
            {
                "task": "scout_b",
                "summary": "Deprecation scout",
                "claims": [
                    {
                        "claim": "CUDA execution provider is unsupported and deprecated",
                        "source": "https://example.com/changelog",
                    }
                ],
                "findings": [],
                "sources": [],
                "uncertainties": [],
            },
        ]

        packet = merge_evidence(subtasks)
        self.assertTrue(packet.has_conflicts)
        self.assertIn("Polarity contradiction", packet.conflicts[0]["reason"])

    def test_packet_to_markdown_rendering(self):
        subtasks = [
            {
                "task": "test_scout",
                "summary": "Scout finished successfully.",
                "claims": [{"claim": "Core algorithm is O(log n)", "source": "https://docs.algo.org"}],
                "findings": ["Core algorithm is O(log n)"],
                "sources": ["https://docs.algo.org"],
                "uncertainties": ["Worst case on degenerate tree is O(n)"],
            }
        ]
        packet = merge_evidence(subtasks)
        md = packet.to_markdown()
        self.assertIn("Research Evidence Packet", md)
        self.assertIn("Core algorithm is O(log n)", md)
        self.assertIn("https://docs.algo.org", md)
        self.assertIn("Worst case on degenerate tree is O(n)", md)


if __name__ == "__main__":
    unittest.main()
