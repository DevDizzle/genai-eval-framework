"""
Factual Accuracy Evaluator
============================

Extracts verifiable claims from generated text and checks each against a
knowledge base or source document.  Two claim types are handled:

1. **Textual claims** — Statements verified via semantic similarity to source.
2. **Numerical claims** — Numbers extracted and compared within a configurable
   tolerance to ground-truth values.

The overall accuracy score is the fraction of claims verified as correct.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.evaluators import BaseEvaluator, EvalResult, Flag, Severity, register


# ---------------------------------------------------------------------------
# Claim extraction helpers
# ---------------------------------------------------------------------------

@dataclass
class Claim:
    """A single verifiable claim extracted from generated text."""
    text: str
    claim_type: str  # "textual" | "numerical"
    value: Optional[float] = None  # for numerical claims
    unit: Optional[str] = None
    span: Optional[Tuple[int, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"text": self.text, "type": self.claim_type}
        if self.value is not None:
            d["value"] = self.value
        if self.unit:
            d["unit"] = self.unit
        return d


# Regex for numbers with optional $ / % / units
_NUM_PATTERN = re.compile(
    r"(?:(?:approximately|about|around|roughly|nearly|over|under)\s+)?"
    r"(?P<sign>[+-])?"
    r"(?P<currency>\$|€|£)?"
    r"(?P<number>[\d,]+(?:\.\d+)?)"
    r"(?P<pct>\s*%?)?"
    r"(?:\s*(?P<unit>billion|million|thousand|bps|basis points|percent))?"
    ,
    re.IGNORECASE,
)

_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _split_sentences(text: str) -> List[str]:
    sents = _SENT_RE.split(text.strip())
    return [s.strip() for s in sents if len(s.strip()) > 10]


def extract_claims(text: str) -> List[Claim]:
    """Extract verifiable claims from generated text.

    Heuristic approach:
    - Every sentence is treated as a textual claim.
    - Sentences containing numbers additionally produce numerical claims.
    """
    claims: List[Claim] = []
    sentences = _split_sentences(text)

    for sent in sentences:
        claims.append(Claim(text=sent, claim_type="textual"))

        for m in _NUM_PATTERN.finditer(sent):
            raw = m.group("number").replace(",", "")
            try:
                value = float(raw)
            except ValueError:
                continue

            multiplier_map = {
                "billion": 1e9,
                "million": 1e6,
                "thousand": 1e3,
            }
            unit_str = (m.group("unit") or "").lower()
            if unit_str in multiplier_map:
                value *= multiplier_map[unit_str]

            unit = m.group("currency") or m.group("pct") or m.group("unit") or ""
            claims.append(
                Claim(
                    text=sent,
                    claim_type="numerical",
                    value=value,
                    unit=unit.strip(),
                    span=(m.start(), m.end()),
                )
            )

    return claims


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

@register
class FactualAccuracyEvaluator(BaseEvaluator):
    """Score factual accuracy of generated text against a knowledge base.

    Config keys:
        embedding_model (str): Sentence-transformer model.
            Default: ``sentence-transformers/all-MiniLM-L6-v2``
        textual_threshold (float): Min cosine similarity for a textual claim
            to be considered supported. Default: 0.65
        numerical_tolerance (float): Relative tolerance for numerical claims.
            Default: 0.05 (5%)
        knowledge_base (list[str]): Optional list of known-fact strings to
            verify against (in addition to the source document).
    """

    name = "factual_accuracy"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._embed_model = None

    def setup(self) -> None:
        from sentence_transformers import SentenceTransformer

        model_name = self.config.get(
            "embedding_model", "sentence-transformers/all-MiniLM-L6-v2"
        )
        self._embed_model = SentenceTransformer(model_name)

    # ------------------------------------------------------------------
    # Verification logic
    # ------------------------------------------------------------------

    def _verify_textual(
        self, claim: Claim, source_sentences: List[str], source_embeddings
    ) -> Tuple[bool, float, Optional[str]]:
        """Check a textual claim against source via embedding similarity."""
        from sentence_transformers.util import cos_sim

        claim_emb = self._embed_model.encode([claim.text], convert_to_tensor=True)
        sims = cos_sim(claim_emb, source_embeddings).cpu().numpy().flatten()
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])

        threshold = self.config.get("textual_threshold", 0.65)
        supported = best_sim >= threshold
        evidence = source_sentences[best_idx] if supported else None
        return supported, best_sim, evidence

    def _verify_numerical(
        self, claim: Claim, source: str
    ) -> Tuple[bool, Optional[float], Optional[str]]:
        """Check a numerical claim by finding close numbers in the source."""
        tolerance = self.config.get("numerical_tolerance", 0.05)

        source_numbers: List[Tuple[float, str]] = []
        for m in _NUM_PATTERN.finditer(source):
            raw = m.group("number").replace(",", "")
            try:
                val = float(raw)
            except ValueError:
                continue
            unit_str = (m.group("unit") or "").lower()
            multiplier_map = {"billion": 1e9, "million": 1e6, "thousand": 1e3}
            if unit_str in multiplier_map:
                val *= multiplier_map[unit_str]
            source_numbers.append((val, m.group(0)))

        if claim.value is None or not source_numbers:
            return False, None, None

        for src_val, src_text in source_numbers:
            if src_val == 0:
                if claim.value == 0:
                    return True, src_val, src_text
                continue
            rel_diff = abs(claim.value - src_val) / abs(src_val)
            if rel_diff <= tolerance:
                return True, src_val, src_text

        return False, None, None

    # ------------------------------------------------------------------
    # Main evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        generated: str,
        source: str = "",
        prompt: str = "",
        **kwargs: Any,
    ) -> EvalResult:
        if not source:
            return EvalResult(
                evaluator=self.name,
                score=0.0,
                details={"error": "No source / knowledge base provided."},
                flags=[
                    Flag(
                        category="factual",
                        message="Cannot verify facts without a source document.",
                        severity=Severity.WARNING,
                    )
                ],
            )

        claims = extract_claims(generated)
        if not claims:
            return EvalResult(
                evaluator=self.name,
                score=1.0,
                details={"note": "No verifiable claims found."},
            )

        # Prepare source embeddings once
        source_sents = _split_sentences(source)
        if not source_sents:
            source_sents = [source]
        source_embs = self._embed_model.encode(source_sents, convert_to_tensor=True)

        # Optionally include extra knowledge base facts
        kb_facts: List[str] = self.config.get("knowledge_base", [])
        if kb_facts:
            kb_embs = self._embed_model.encode(kb_facts, convert_to_tensor=True)
            import torch
            source_sents = source_sents + kb_facts
            source_embs = torch.cat([source_embs, kb_embs], dim=0)

        verified = 0
        claim_results: List[Dict[str, Any]] = []
        flags: List[Flag] = []

        for claim in claims:
            if claim.claim_type == "numerical":
                ok, src_val, evidence = self._verify_numerical(claim, source)
                result = {
                    **claim.to_dict(),
                    "verified": ok,
                    "source_value": src_val,
                    "evidence": evidence,
                }
            else:
                ok, sim, evidence = self._verify_textual(
                    claim, source_sents, source_embs
                )
                result = {
                    **claim.to_dict(),
                    "verified": ok,
                    "similarity": round(sim, 4),
                    "evidence": evidence,
                }

            claim_results.append(result)

            if ok:
                verified += 1
            else:
                flags.append(
                    Flag(
                        category=f"factual:{claim.claim_type}",
                        message=f"Unverified {claim.claim_type} claim: \"{claim.text[:80]}...\"",
                        severity=Severity.WARNING,
                        evidence=claim.text,
                    )
                )

        accuracy = verified / len(claims) if claims else 1.0
        textual_claims = [c for c in claim_results if c["type"] == "textual"]
        numerical_claims = [c for c in claim_results if c["type"] == "numerical"]

        return EvalResult(
            evaluator=self.name,
            score=round(accuracy, 4),
            sub_scores={
                "textual_accuracy": round(
                    sum(1 for c in textual_claims if c["verified"]) / max(len(textual_claims), 1), 4
                ),
                "numerical_accuracy": round(
                    sum(1 for c in numerical_claims if c["verified"]) / max(len(numerical_claims), 1), 4
                ),
            },
            flags=flags,
            details={
                "total_claims": len(claims),
                "verified_claims": verified,
                "unverified_claims": len(claims) - verified,
                "claim_results": claim_results,
            },
        )
