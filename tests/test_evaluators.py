"""
Unit tests for GenAI Evaluation Framework evaluators.

Tests cover:
- Base classes and result models
- Each evaluator's core logic
- Edge cases (empty input, missing source, etc.)
- Brand alignment and PII detection utilities
- Claim extraction
"""

import json
import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluators import (
    BaseEvaluator,
    EvalResult,
    Flag,
    Severity,
    register,
    get_evaluator,
    available_evaluators,
)


# ===========================================================================
# Result model tests
# ===========================================================================

class TestEvalResult:
    def test_basic_creation(self):
        result = EvalResult(evaluator="test", score=0.85)
        assert result.evaluator == "test"
        assert result.score == 0.85
        assert result.passed is True

    def test_critical_flag_fails(self):
        result = EvalResult(
            evaluator="test",
            score=0.9,
            flags=[Flag(category="bad", message="problem", severity=Severity.CRITICAL)],
        )
        assert result.passed is False

    def test_warning_flag_passes(self):
        result = EvalResult(
            evaluator="test",
            score=0.5,
            flags=[Flag(category="minor", message="meh", severity=Severity.WARNING)],
        )
        assert result.passed is True

    def test_to_dict(self):
        result = EvalResult(
            evaluator="test",
            score=0.7777,
            sub_scores={"a": 0.8, "b": 0.75},
            flags=[Flag(category="x", message="y")],
            details={"key": "value"},
        )
        d = result.to_dict()
        assert d["score"] == 0.7777
        assert d["passed"] is True
        assert len(d["flags"]) == 1
        assert d["sub_scores"]["a"] == 0.8

    def test_flag_to_dict(self):
        flag = Flag(
            category="test",
            message="found it",
            severity=Severity.CRITICAL,
            span=(10, 20),
            evidence="the evidence",
        )
        d = flag.to_dict()
        assert d["severity"] == "critical"
        assert d["span"] == [10, 20]


# ===========================================================================
# Safety evaluator — unit-testable without models
# ===========================================================================

class TestPIIDetection:
    def test_detects_email(self):
        from src.evaluators.safety import detect_pii
        findings = detect_pii("Contact us at john.doe@example.com for details.")
        assert any(f["type"] == "email" for f in findings)

    def test_detects_phone(self):
        from src.evaluators.safety import detect_pii
        findings = detect_pii("Call us at (555) 123-4567 today.")
        assert any(f["type"] == "phone_us" for f in findings)

    def test_detects_ssn(self):
        from src.evaluators.safety import detect_pii
        findings = detect_pii("SSN: 123-45-6789")
        assert any(f["type"] == "ssn" for f in findings)

    def test_detects_credit_card(self):
        from src.evaluators.safety import detect_pii
        findings = detect_pii("Card: 4111 1111 1111 1111")
        assert any(f["type"] == "credit_card" for f in findings)

    def test_no_pii(self):
        from src.evaluators.safety import detect_pii
        findings = detect_pii("The stock rose 5% on Tuesday.")
        # IP-like patterns in normal text shouldn't appear here
        assert not any(f["type"] in ("email", "phone_us", "ssn", "credit_card") for f in findings)


class TestBrandAlignment:
    def test_clean_text(self):
        from src.evaluators.safety import check_brand_alignment
        score, violations = check_brand_alignment(
            "The market showed strong performance today.",
            forbidden_terms=["kill"],
            forbidden_topics=["politics"],
        )
        assert score == 1.0
        assert violations == []

    def test_forbidden_term(self):
        from src.evaluators.safety import check_brand_alignment
        score, violations = check_brand_alignment(
            "This will kill the competition.",
            forbidden_terms=["kill"],
        )
        assert score < 1.0
        assert any(v["type"] == "forbidden_term" for v in violations)

    def test_competitor_mention(self):
        from src.evaluators.safety import check_brand_alignment
        score, violations = check_brand_alignment(
            "Unlike Netflix, our service is better.",
            competitor_names=["Netflix"],
        )
        assert any(v["type"] == "competitor_mention" for v in violations)

    def test_multiple_violations(self):
        from src.evaluators.safety import check_brand_alignment
        score, violations = check_brand_alignment(
            "The politics of murder in gambling are complex.",
            forbidden_terms=["murder"],
            forbidden_topics=["politics", "gambling"],
        )
        assert len(violations) == 3
        assert score == 0.7  # 1.0 - 0.1 * 3


class TestContentRating:
    def test_g_rating(self):
        from src.evaluators.safety import compute_content_rating
        assert compute_content_rating({"toxicity": 0.05}, 0, 0) == "G"

    def test_pg_rating(self):
        from src.evaluators.safety import compute_content_rating
        assert compute_content_rating({"toxicity": 0.2}, 1, 0) == "PG"

    def test_r_rating(self):
        from src.evaluators.safety import compute_content_rating
        assert compute_content_rating({"toxicity": 0.8}, 5, 2) == "R"


# ===========================================================================
# Factual evaluator — claim extraction tests
# ===========================================================================

class TestClaimExtraction:
    def test_extracts_textual_claims(self):
        from src.evaluators.factual import extract_claims
        text = "Revenue was $81.8 billion. The company grew 2% year-over-year."
        claims = extract_claims(text)
        textual = [c for c in claims if c.claim_type == "textual"]
        assert len(textual) >= 1

    def test_extracts_numerical_claims(self):
        from src.evaluators.factual import extract_claims
        text = "Revenue was $81.8 billion. EPS came in at $1.26."
        claims = extract_claims(text)
        numerical = [c for c in claims if c.claim_type == "numerical"]
        assert len(numerical) >= 2

    def test_handles_percentages(self):
        from src.evaluators.factual import extract_claims
        text = "Growth was 14% year-over-year, a strong result."
        claims = extract_claims(text)
        numerical = [c for c in claims if c.claim_type == "numerical"]
        assert any(c.value == 14.0 for c in numerical)

    def test_empty_text(self):
        from src.evaluators.factual import extract_claims
        claims = extract_claims("")
        assert claims == []


# ===========================================================================
# Quality evaluator — heuristic fallback tests
# ===========================================================================

class TestQualityHeuristic:
    def test_heuristic_returns_scores(self):
        from src.evaluators.quality import _heuristic_quality
        result = _heuristic_quality(
            "The market performed well. Furthermore, earnings exceeded expectations. "
            "Additionally, the company raised guidance for the next quarter.",
            prompt="Analyze the market",
        )
        assert "coherence" in result
        assert "fluency" in result
        assert "relevance" in result
        assert 1 <= result["coherence"] <= 5
        assert result["method"] == "heuristic"

    def test_heuristic_no_prompt(self):
        from src.evaluators.quality import _heuristic_quality
        result = _heuristic_quality("A simple sentence here.")
        assert result["relevance"] == 3  # default when no prompt


# ===========================================================================
# Hallucination evaluator — sentence splitting
# ===========================================================================

class TestSentenceSplitting:
    def test_splits_sentences(self):
        from src.evaluators.hallucination import _split_sentences
        text = "This is sentence one. This is sentence two. And this is the third one."
        sents = _split_sentences(text)
        assert len(sents) >= 2

    def test_filters_short(self):
        from src.evaluators.hallucination import _split_sentences
        text = "Hi. This is a longer sentence that should be kept."
        sents = _split_sentences(text)
        assert all(len(s) > 10 for s in sents)


# ===========================================================================
# Integration-style tests with mocked models
# ===========================================================================

class TestHallucinationEvaluatorMocked:
    """Test hallucination evaluator with mocked ML models."""

    def test_no_source_returns_zero(self):
        from src.evaluators.hallucination import HallucinationEvaluator
        ev = HallucinationEvaluator()
        ev._ready = True  # skip setup
        result = ev.evaluate(generated="Some text here.", source="")
        assert result.score == 0.0
        assert len(result.flags) > 0

    def test_empty_generated(self):
        from src.evaluators.hallucination import HallucinationEvaluator
        ev = HallucinationEvaluator()
        ev._ready = True
        result = ev.evaluate(generated="", source="Source document text here.")
        assert result.score == 1.0  # no sentences to check


class TestFactualEvaluatorMocked:
    """Test factual evaluator with mocked models."""

    def test_no_source(self):
        from src.evaluators.factual import FactualAccuracyEvaluator
        ev = FactualAccuracyEvaluator()
        ev._ready = True
        result = ev.evaluate(generated="Claims here.", source="")
        assert result.score == 0.0


class TestSafetyEvaluatorMocked:
    """Test safety evaluator with mocked toxicity model."""

    def test_with_mocked_detoxify(self):
        from src.evaluators.safety import ContentSafetyEvaluator
        ev = ContentSafetyEvaluator(config={"pii_is_critical": True})
        ev._ready = True
        ev._toxicity_model = MagicMock()
        ev._toxicity_model.predict.return_value = {
            "toxicity": 0.05,
            "severe_toxicity": 0.01,
            "obscene": 0.02,
            "threat": 0.01,
            "insult": 0.03,
            "identity_attack": 0.01,
        }

        result = ev.evaluate(
            generated="The stock rose 5% on strong earnings.",
            source="Earnings report.",
        )
        assert result.score > 0.9
        assert result.details["content_rating"] == "G"

    def test_pii_detection_flags(self):
        from src.evaluators.safety import ContentSafetyEvaluator
        ev = ContentSafetyEvaluator(config={"pii_is_critical": True})
        ev._ready = True
        ev._toxicity_model = MagicMock()
        ev._toxicity_model.predict.return_value = {
            "toxicity": 0.02, "severe_toxicity": 0.01,
            "obscene": 0.01, "threat": 0.01,
            "insult": 0.01, "identity_attack": 0.01,
        }

        result = ev.evaluate(
            generated="Contact john@example.com or call 555-123-4567.",
        )
        assert result.details["pii_count"] >= 2
        assert any(f.severity == Severity.CRITICAL for f in result.flags)


class TestQualityEvaluatorMocked:
    def test_heuristic_mode(self):
        from src.evaluators.quality import QualityEvaluator
        ev = QualityEvaluator(config={"use_heuristic": True})
        result = ev(
            generated="The market performed well. Furthermore, guidance was raised.",
            prompt="Analyze market conditions",
        )
        assert 0 < result.score <= 1.0
        assert result.details["method"] == "heuristic"


# ===========================================================================
# Registry tests
# ===========================================================================

class TestRegistry:
    def test_available_evaluators(self):
        names = available_evaluators()
        assert "hallucination" in names
        assert "factual_accuracy" in names
        assert "content_safety" in names
        assert "quality" in names

    def test_get_evaluator(self):
        ev = get_evaluator("quality", config={"use_heuristic": True})
        assert ev.name == "quality"

    def test_unknown_evaluator_raises(self):
        with pytest.raises(KeyError):
            get_evaluator("nonexistent")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
