"""
Hallucination Evaluator
========================

Detects hallucinated content by comparing generated text against source
documents using two complementary methods:

1. **NLI Entailment** — A cross-encoder NLI model scores each generated
   sentence as entailed, neutral, or contradicted by the source.
2. **Semantic Similarity** — Sentence embeddings measure drift between
   generated content and source material.

The final hallucination score (0 = all hallucinated, 1 = fully grounded)
is a weighted combination of both signals.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.evaluators import BaseEvaluator, EvalResult, Flag, Severity, register


# ---------------------------------------------------------------------------
# Sentence splitter (lightweight, no spaCy dependency required)
# ---------------------------------------------------------------------------

_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences using a simple regex heuristic."""
    sents = _SENT_RE.split(text.strip())
    return [s.strip() for s in sents if len(s.strip()) > 10]


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

@register
class HallucinationEvaluator(BaseEvaluator):
    """Detect hallucinations via NLI entailment and semantic similarity.

    Config keys:
        nli_model (str): HuggingFace cross-encoder model for NLI.
            Default: ``cross-encoder/nli-deberta-v3-base``
        embedding_model (str): Sentence-transformer model for similarity.
            Default: ``sentence-transformers/all-MiniLM-L6-v2``
        entailment_weight (float): Weight for NLI score. Default: 0.6
        similarity_weight (float): Weight for similarity score. Default: 0.4
        contradiction_threshold (float): NLI score below which a sentence is
            flagged as contradicted. Default: 0.3
        similarity_threshold (float): Cosine similarity below which a sentence
            is flagged as drifted. Default: 0.5
    """

    name = "hallucination"

    # Label indices for cross-encoder/nli-deberta-v3-base
    _CONTRADICTION = 0
    _ENTAILMENT = 1
    _NEUTRAL = 2

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._nli_model = None
        self._embed_model = None

    # ------------------------------------------------------------------
    # Setup — lazy-load heavy models
    # ------------------------------------------------------------------

    def setup(self) -> None:
        from sentence_transformers import CrossEncoder, SentenceTransformer

        nli_name = self.config.get(
            "nli_model", "cross-encoder/nli-deberta-v3-base"
        )
        embed_name = self.config.get(
            "embedding_model", "sentence-transformers/all-MiniLM-L6-v2"
        )

        self._nli_model = CrossEncoder(nli_name, max_length=512)
        self._embed_model = SentenceTransformer(embed_name)

    # ------------------------------------------------------------------
    # Core scoring methods
    # ------------------------------------------------------------------

    def _nli_scores(
        self, sentences: List[str], source: str
    ) -> List[Dict[str, Any]]:
        """Score each sentence against the source using NLI.

        Returns per-sentence dicts with keys:
            sentence, label, entailment_prob, contradiction_prob
        """
        if not sentences:
            return []

        pairs = [(source, sent) for sent in sentences]
        logits = self._nli_model.predict(pairs, apply_softmax=True)

        results = []
        for sent, probs in zip(sentences, logits):
            probs = np.array(probs)
            label_idx = int(np.argmax(probs))
            label_map = {
                self._CONTRADICTION: "contradiction",
                self._ENTAILMENT: "entailment",
                self._NEUTRAL: "neutral",
            }
            results.append(
                {
                    "sentence": sent,
                    "label": label_map.get(label_idx, "neutral"),
                    "entailment_prob": float(probs[self._ENTAILMENT]),
                    "contradiction_prob": float(probs[self._CONTRADICTION]),
                    "neutral_prob": float(probs[self._NEUTRAL]),
                }
            )
        return results

    def _semantic_similarity(
        self, sentences: List[str], source: str
    ) -> List[float]:
        """Compute cosine similarity between each sentence and the source."""
        if not sentences:
            return []

        from sentence_transformers.util import cos_sim

        source_emb = self._embed_model.encode([source], convert_to_tensor=True)
        sent_embs = self._embed_model.encode(sentences, convert_to_tensor=True)

        sims = cos_sim(sent_embs, source_emb).cpu().numpy().flatten()
        return [float(s) for s in sims]

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
        """Evaluate generated text for hallucinations against the source.

        Args:
            generated: The AI-generated text to evaluate.
            source: The reference / grounding document.
            prompt: The original prompt (used for context, not scored).

        Returns:
            EvalResult with score 0–1 (1 = fully grounded).
        """
        if not source:
            return EvalResult(
                evaluator=self.name,
                score=0.0,
                details={"error": "No source document provided for grounding."},
                flags=[
                    Flag(
                        category="hallucination",
                        message="Cannot assess hallucination without source document.",
                        severity=Severity.WARNING,
                    )
                ],
            )

        sentences = _split_sentences(generated)
        if not sentences:
            return EvalResult(
                evaluator=self.name,
                score=1.0,
                details={"note": "No scoreable sentences in generated text."},
            )

        # --- NLI Entailment ---
        nli_results = self._nli_scores(sentences, source)
        entailment_scores = [r["entailment_prob"] for r in nli_results]
        avg_entailment = float(np.mean(entailment_scores))

        # --- Semantic Similarity ---
        similarities = self._semantic_similarity(sentences, source)
        avg_similarity = float(np.mean(similarities))

        # --- Weighted composite ---
        ew = self.config.get("entailment_weight", 0.6)
        sw = self.config.get("similarity_weight", 0.4)
        composite = ew * avg_entailment + sw * avg_similarity

        # --- Flag problematic sentences ---
        flags: List[Flag] = []
        contradiction_thresh = self.config.get("contradiction_threshold", 0.3)
        similarity_thresh = self.config.get("similarity_threshold", 0.5)

        sentence_details = []
        for i, (nli, sim) in enumerate(zip(nli_results, similarities)):
            entry = {
                "sentence": nli["sentence"],
                "nli_label": nli["label"],
                "entailment_prob": round(nli["entailment_prob"], 4),
                "contradiction_prob": round(nli["contradiction_prob"], 4),
                "similarity": round(sim, 4),
            }
            sentence_details.append(entry)

            if nli["label"] == "contradiction":
                flags.append(
                    Flag(
                        category="hallucination:contradiction",
                        message=f"Sentence contradicts source: \"{nli['sentence'][:80]}...\"",
                        severity=Severity.CRITICAL,
                        evidence=nli["sentence"],
                    )
                )
            elif nli["entailment_prob"] < contradiction_thresh and sim < similarity_thresh:
                flags.append(
                    Flag(
                        category="hallucination:unsupported",
                        message=f"Sentence appears unsupported by source: \"{nli['sentence'][:80]}...\"",
                        severity=Severity.WARNING,
                        evidence=nli["sentence"],
                    )
                )

        return EvalResult(
            evaluator=self.name,
            score=round(composite, 4),
            sub_scores={
                "entailment": round(avg_entailment, 4),
                "semantic_similarity": round(avg_similarity, 4),
            },
            flags=flags,
            details={
                "num_sentences": len(sentences),
                "num_contradictions": sum(
                    1 for r in nli_results if r["label"] == "contradiction"
                ),
                "num_unsupported": sum(
                    1
                    for r, s in zip(nli_results, similarities)
                    if r["entailment_prob"] < contradiction_thresh
                    and s < similarity_thresh
                ),
                "sentence_results": sentence_details,
            },
        )
