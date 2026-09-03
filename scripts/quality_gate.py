#!/usr/bin/env python3
"""Quality Gate for Codex-Antigravity.

Evaluates research results returned by Antigravity CLI according to objective
quality metrics: primary source ratio, claim coverage, confidence, freshness,
and uncertainty penalty.
"""

from enum import Enum
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config  # type: ignore


class QualityDecision(str, Enum):
    PASS = "PASS"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    POOR = "POOR"
    # Backward compatibility aliases
    CASCADE_PRO = "POOR"
    RETRY_WITH_CONTEXT = "NEEDS_REVIEW"


class QualityResult:
    """Detailed evaluation score and quality assessment for a research packet."""

    def __init__(
        self,
        score: float,
        decision: QualityDecision,
        metrics: Dict[str, float],
        reasons: List[str],
    ):
        self.score = round(max(0.0, min(1.0, score)), 3)
        self.decision = decision
        self.metrics = {k: round(v, 3) for k, v in metrics.items()}
        self.reasons = reasons

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "decision": self.decision.value,
            "metrics": self.metrics,
            "reasons": self.reasons,
        }


def evaluate_quality(
    research_result: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
) -> QualityResult:
    """Compute objective quality score based on verifiable claims, sources, and uncertainties.

    Formula:
      score = (primary_source_ratio * 0.35
             + claim_coverage * 0.25
             + confidence_score * 0.15
             + source_freshness * 0.15
             - uncertainty_ratio * 0.10)
    """
    cfg = config or load_config()
    q_cfg = cfg.get("quality_gate", {})

    pass_threshold = float(q_cfg.get("pass_threshold", 0.70))
    review_threshold = float(q_cfg.get("review_threshold", 0.40))

    if not research_result.get("success", False):
        return QualityResult(
            score=0.0,
            decision=QualityDecision.POOR,
            metrics={"primary_source_ratio": 0.0, "claim_coverage": 0.0, "confidence_score": 0.0, "source_freshness": 0.0, "uncertainty_ratio": 1.0},
            reasons=["Task failed or returned empty output."],
        )

    claims = research_result.get("claims", [])
    findings = research_result.get("findings", [])
    sources = research_result.get("sources", [])
    uncertainties = research_result.get("uncertainties", [])

    reasons: List[str] = []

    # 1. Primary Source Ratio (Weight: 0.35)
    if claims:
        retrieved_count = sum(
            1 for c in claims
            if c.get("verification_status") in ("source_retrieved", "cross_checked")
            or (isinstance(c.get("evidence"), dict) and c.get("evidence", {}).get("type") in ("official_docs", "github_repo", "local_code"))
        )
        primary_source_ratio = retrieved_count / len(claims)
    elif sources:
        official_sources = sum(
            1 for s in sources
            if any(dom in str(s).lower() for dom in ["docs.", "github.com", "microsoft.com", "pytorch.org", "python.org", "crates.io"])
        )
        primary_source_ratio = official_sources / len(sources)
    else:
        primary_source_ratio = 0.0

    if primary_source_ratio < 0.5:
        reasons.append(f"Low primary source ratio: {primary_source_ratio:.0%} of claims backed by authoritative sources.")

    # 2. Claim Coverage (Weight: 0.25)
    total_items = max(len(claims), len(findings))
    if total_items >= 3:
        claim_coverage = 1.0
    elif total_items == 2:
        claim_coverage = 0.75
    elif total_items == 1:
        claim_coverage = 0.50
    else:
        claim_coverage = 0.0
        reasons.append("No claims or findings returned.")

    # 3. Confidence Score (Weight: 0.15)
    conf_map = {"high": 1.0, "medium": 0.65, "low": 0.30}
    if claims:
        conf_sum = sum(conf_map.get(str(c.get("self_confidence", c.get("confidence", "medium"))).lower(), 0.5) for c in claims)
        confidence_score = conf_sum / len(claims)
    else:
        confidence_score = 0.5

    # 4. Source Freshness (Weight: 0.15)
    freshness_indicators = [
        re.compile(r"https?://[^\s]+"),
        re.compile(r"v?\d+\.\d+(?:\.\d+)?"),
        re.compile(r"\b(?:202[3-9]|latest|current)\b", re.IGNORECASE),
    ]
    freshness_hits = 0
    all_text = " ".join(sources + [c.get("claim", "") + " " + c.get("source", "") for c in claims])
    for pat in freshness_indicators:
        if pat.search(all_text):
            freshness_hits += 1
    source_freshness = min(1.0, freshness_hits / 2.0)

    # 5. Uncertainty Penalty (Weight: -0.10)
    unc_count = len(uncertainties)
    if claims or findings:
        uncertainty_ratio = min(1.0, unc_count / max(len(claims) + unc_count, 1))
    else:
        uncertainty_ratio = 1.0 if unc_count > 0 else 0.0

    if unc_count >= 3:
        reasons.append(f"High count of uncertainties or caveats ({unc_count} items).")

    # Composite Score
    score = (
        (primary_source_ratio * 0.35)
        + (claim_coverage * 0.25)
        + (confidence_score * 0.15)
        + (source_freshness * 0.15)
        - (uncertainty_ratio * 0.10)
    )
    score = max(0.0, min(1.0, score))

    metrics = {
        "primary_source_ratio": primary_source_ratio,
        "claim_coverage": claim_coverage,
        "confidence_score": confidence_score,
        "source_freshness": source_freshness,
        "uncertainty_ratio": uncertainty_ratio,
    }

    # Decision logic
    if score >= pass_threshold:
        decision = QualityDecision.PASS
    elif score >= review_threshold:
        decision = QualityDecision.NEEDS_REVIEW
        reasons.append("Score in moderate range: verify sources before implementation.")
    else:
        decision = QualityDecision.POOR
        reasons.append(f"Quality score {score:.2f} is below threshold {review_threshold:.2f}.")

    return QualityResult(
        score=score,
        decision=decision,
        metrics=metrics,
        reasons=reasons,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate Antigravity research output quality.")
    parser.add_argument("--input", type=str, required=True, help="Path to JSON file containing research result")
    parser.add_argument("--json", action="store_true", default=False, help="Output JSON result")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    res = evaluate_quality(data)
    if args.json:
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print("=" * 50)
        print(f"Quality Score : {res.score:.2f} / 1.00")
        print(f"Decision      : {res.decision.value}")
        print("Metrics       :")
        for k, v in res.metrics.items():
            print(f"  - {k:<22}: {v:.2f}")
        if res.reasons:
            print("Reasons / Notes:")
            for r in res.reasons:
                print(f"  * {r}")
        print("=" * 50)


if __name__ == "__main__":
    main()
