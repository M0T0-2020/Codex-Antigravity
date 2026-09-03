#!/usr/bin/env python3
"""Evidence Merger and Conflict Detection for Codex-Antigravity.

Aggregates findings and claims across multiple parallel research and codebase
reconnaissance subtasks, deduplicating assertions, cross-referencing sources,
and flagging contradictions or version discrepancies.
"""

from enum import Enum
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple


class ClaimStatus(str, Enum):
    SUPPORTED = "supported"
    PROVISIONAL = "provisional"
    CONFLICTING = "conflicting"
    CONTRADICTED = "contradicted"


class MergedClaim:
    """Aggregated factual assertion with multi-agent support and conflict tracking."""

    def __init__(
        self,
        claim: str,
        sources: List[str],
        confidence: str = "high",
        status: ClaimStatus = ClaimStatus.SUPPORTED,
        subtasks: Optional[List[str]] = None,
        conflicts: Optional[List[str]] = None,
    ):
        self.claim = claim
        self.sources = list(dict.fromkeys(sources))
        self.confidence = confidence
        self.status = status
        self.subtasks = subtasks or []
        self.conflicts = conflicts or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "status": self.status.value,
            "confidence": self.confidence,
            "support": self.sources,
            "subtasks": self.subtasks,
            "conflicts": self.conflicts,
        }


def _tokenize(text: str) -> Set[str]:
    """Extract normalized word tokens for similarity scoring."""
    words = re.findall(r"[a-zA-Z0-9_.]+", text.lower())
    stop_words = {"the", "a", "an", "is", "are", "and", "or", "to", "in", "for", "with", "of", "on"}
    return {w for w in words if w not in stop_words and len(w) > 1}


def _jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    return len(set_a.intersection(set_b)) / len(set_a.union(set_b))


def _detect_claim_conflict(claim_a: str, claim_b: str) -> Optional[str]:
    """Detect potential factual contradictions between two claims.

    Looks for conflicting versions, requirements, or negative/positive assertions
    on the same topic.
    """
    tok_a = _tokenize(claim_a)
    tok_b = _tokenize(claim_b)
    overlap = tok_a.intersection(tok_b)

    # Must share at least 2 significant topic tokens (e.g. ['cuda', 'onnxruntime'])
    if len(overlap) < 2:
        return None

    # Check for version discrepancies (e.g. 12.4 vs 11.8)
    versions_a = set(re.findall(r"\b\d+\.\d+(?:\.\d+)?\b", claim_a))
    versions_b = set(re.findall(r"\b\d+\.\d+(?:\.\d+)?\b", claim_b))

    if versions_a and versions_b and versions_a != versions_b:
        # If one version is not a subset/prefix of the other
        diff = versions_a.symmetric_difference(versions_b)
        if diff:
            return f"Conflicting versions mentioned: {', '.join(versions_a)} vs {', '.join(versions_b)}"

    # Check for polarity opposition (supported vs deprecated / unsupported)
    pos_terms = {"support", "supported", "required", "compatible", "enabled", "available"}
    neg_terms = {"unsupported", "deprecated", "removed", "incompatible", "disabled", "not"}

    has_pos_a = bool(tok_a.intersection(pos_terms))
    has_neg_a = bool(tok_a.intersection(neg_terms))
    has_pos_b = bool(tok_b.intersection(pos_terms))
    has_neg_b = bool(tok_b.intersection(neg_terms))

    if (has_pos_a and has_neg_b) or (has_neg_a and has_pos_b):
        return f"Polarity contradiction on shared topic '{', '.join(overlap)}'"

    return None


class EvidencePacket:
    """Consolidated evidence packet ready for Codex consumption."""

    def __init__(
        self,
        summary: str,
        claims: List[MergedClaim],
        conflicts: List[Dict[str, Any]],
        findings: List[str],
        sources: List[str],
        uncertainties: List[str],
        subtask_count: int,
    ):
        self.summary = summary
        self.claims = claims
        self.conflicts = conflicts
        self.findings = findings
        self.sources = list(dict.fromkeys(sources))
        self.uncertainties = uncertainties
        self.subtask_count = subtask_count

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "has_conflicts": self.has_conflicts,
            "claims": [c.to_dict() for c in self.claims],
            "conflicts": self.conflicts,
            "findings": self.findings,
            "sources": self.sources,
            "uncertainties": self.uncertainties,
            "subtask_count": self.subtask_count,
        }

    def to_markdown(self) -> str:
        """Render a clean, structured Markdown report for Codex implementation context."""
        lines = [
            "### Research Evidence Packet",
            f"**Synthesis Summary**: {self.summary}\n",
        ]

        if self.conflicts:
            lines.append("#### ⚠️ Detected Conflicts & Ambiguities:")
            for conf in self.conflicts:
                lines.append(f"- **Issue**: {conf.get('reason')}")
                lines.append(f"  - Claim A: \"{conf.get('claim_a')}\"")
                lines.append(f"  - Claim B: \"{conf.get('claim_b')}\"")
            lines.append("")

        lines.append("#### Verified Claims & Findings:")
        for c in self.claims:
            icon = "✓" if c.status == ClaimStatus.SUPPORTED else ("⚠️" if c.status == ClaimStatus.CONFLICTING else "•")
            src_str = f" [Sources: {', '.join(c.sources[:2])}]" if c.sources else ""
            lines.append(f"- {icon} **{c.claim}**{src_str}")

        if self.uncertainties:
            lines.append("\n#### Caveats & Uncertainties:")
            for u in self.uncertainties:
                lines.append(f"- ? {u}")

        if self.sources:
            lines.append("\n#### Reference Sources:")
            for s in self.sources:
                lines.append(f"- {s}")

        return "\n".join(lines)


def merge_evidence(subtask_results: List[Dict[str, Any]]) -> EvidencePacket:
    """Merge evidence from multiple research subtask outputs with conflict detection."""
    all_raw_claims: List[Tuple[Dict[str, Any], str]] = []
    all_findings: List[str] = []
    all_sources: List[str] = []
    all_uncertainties: List[str] = []
    summaries: List[str] = []

    for res in subtask_results:
        task_label = res.get("task", "subtask")
        if res.get("summary"):
            summaries.append(f"[{task_label}] {res['summary']}")

        for f in res.get("findings", []):
            all_findings.append(f"[{task_label}] {f}")

        for s in res.get("sources", []):
            if s and s not in all_sources:
                all_sources.append(s)

        for u in res.get("uncertainties", []):
            all_uncertainties.append(f"[{task_label}] {u}")

        for c in res.get("claims", []):
            all_raw_claims.append((c, task_label))

    # Deduplicate and group claims by token similarity
    merged_claims: List[MergedClaim] = []
    grouped_indices: Set[int] = set()

    for i, (c_i, task_i) in enumerate(all_raw_claims):
        if i in grouped_indices:
            continue

        c_text = c_i.get("claim", "").strip()
        if not c_text:
            continue

        sources = [c_i.get("source")] if c_i.get("source") else []
        subtasks = [task_i]
        confidence = c_i.get("self_confidence", c_i.get("confidence", "high"))
        tok_i = _tokenize(c_text)

        # Check for matching/supporting claims in remaining items
        for j in range(i + 1, len(all_raw_claims)):
            if j in grouped_indices:
                continue
            c_j, task_j = all_raw_claims[j]
            c_j_text = c_j.get("claim", "").strip()
            tok_j = _tokenize(c_j_text)

            sim = _jaccard_similarity(tok_i, tok_j)
            conflict = _detect_claim_conflict(c_text, c_j_text)
            if sim >= 0.70 and not conflict:  # High similarity and non-conflicting: merge into same claim
                grouped_indices.add(j)
                if c_j.get("source") and c_j.get("source") not in sources:
                    sources.append(c_j.get("source"))
                if task_j not in subtasks:
                    subtasks.append(task_j)

        merged_claims.append(
            MergedClaim(
                claim=c_text,
                sources=sources,
                confidence=confidence,
                status=ClaimStatus.SUPPORTED,
                subtasks=subtasks,
            )
        )

    # Detect conflicts across merged claims
    conflicts: List[Dict[str, Any]] = []
    for idx_a in range(len(merged_claims)):
        for idx_b in range(idx_a + 1, len(merged_claims)):
            ca = merged_claims[idx_a]
            cb = merged_claims[idx_b]

            conflict_reason = _detect_claim_conflict(ca.claim, cb.claim)
            if conflict_reason:
                ca.status = ClaimStatus.CONFLICTING
                cb.status = ClaimStatus.CONFLICTING
                ca.conflicts.append(cb.claim)
                cb.conflicts.append(ca.claim)
                conflicts.append({
                    "reason": conflict_reason,
                    "claim_a": ca.claim,
                    "claim_b": cb.claim,
                    "sources_a": ca.sources,
                    "sources_b": cb.sources,
                })

    joint_summary = "\n".join(summaries) if summaries else "Synthesized findings across subtasks."

    return EvidencePacket(
        summary=joint_summary,
        claims=merged_claims,
        conflicts=conflicts,
        findings=all_findings,
        sources=all_sources,
        uncertainties=all_uncertainties,
        subtask_count=len(subtask_results),
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Merge research evidence and detect conflicts across subtasks.")
    parser.add_argument("--inputs", type=str, nargs="+", required=True, help="JSON files containing subtask results")
    parser.add_argument("--json", action="store_true", default=False, help="Output JSON result")
    parser.add_argument("--markdown", action="store_true", default=False, help="Output Markdown report")
    args = parser.parse_args()

    results = []
    for p in args.inputs:
        with open(p, "r", encoding="utf-8") as f:
            results.append(json.load(f))

    packet = merge_evidence(results)
    if args.markdown:
        print(packet.to_markdown())
    elif args.json:
        print(json.dumps(packet.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(packet.to_markdown())


if __name__ == "__main__":
    main()
