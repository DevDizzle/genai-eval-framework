"""
GenAI Evaluation Framework — Evaluator Suite

Provides base classes, result models, and an evaluator registry for building
composable evaluation pipelines.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    """Flag severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Flag:
    """A single flagged issue found during evaluation."""
    category: str
    message: str
    severity: Severity = Severity.WARNING
    span: Optional[tuple[int, int]] = None  # character offsets in generated text
    evidence: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "message": self.message,
            "severity": self.severity.value,
            "span": list(self.span) if self.span else None,
            "evidence": self.evidence,
        }


@dataclass
class EvalResult:
    """Standardised output from any evaluator."""
    evaluator: str
    score: float  # 0.0 (worst) – 1.0 (best), or 1-5 for quality
    details: Dict[str, Any] = field(default_factory=dict)
    flags: List[Flag] = field(default_factory=list)
    sub_scores: Dict[str, float] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Whether any critical flags were raised."""
        return not any(f.severity == Severity.CRITICAL for f in self.flags)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluator": self.evaluator,
            "score": round(self.score, 4),
            "passed": self.passed,
            "sub_scores": {k: round(v, 4) for k, v in self.sub_scores.items()},
            "flags": [f.to_dict() for f in self.flags],
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Base evaluator
# ---------------------------------------------------------------------------

class BaseEvaluator(abc.ABC):
    """Abstract base for all evaluators.

    Subclasses must implement ``evaluate()``.  Optional ``setup()`` is called
    once before the first evaluation to load heavy resources (models, etc.).
    """

    name: str = "base"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._ready = False

    def setup(self) -> None:
        """Load models / resources.  Override in subclasses."""
        pass

    def _ensure_ready(self) -> None:
        if not self._ready:
            self.setup()
            self._ready = True

    @abc.abstractmethod
    def evaluate(
        self,
        generated: str,
        source: str = "",
        prompt: str = "",
        **kwargs: Any,
    ) -> EvalResult:
        """Run evaluation and return a standardised result."""
        ...

    def __call__(self, *args: Any, **kwargs: Any) -> EvalResult:
        self._ensure_ready()
        return self.evaluate(*args, **kwargs)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: Dict[str, Type[BaseEvaluator]] = {}


def register(cls: Type[BaseEvaluator]) -> Type[BaseEvaluator]:
    """Class decorator — adds an evaluator to the global registry."""
    _REGISTRY[cls.name] = cls
    return cls


def get_evaluator(name: str, config: Optional[Dict[str, Any]] = None) -> BaseEvaluator:
    """Instantiate a registered evaluator by name."""
    if name not in _REGISTRY:
        raise KeyError(
            f"Unknown evaluator '{name}'. Available: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[name](config=config)


def available_evaluators() -> List[str]:
    """Return names of all registered evaluators."""
    return list(_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Auto-register built-in evaluators on import
# ---------------------------------------------------------------------------

from src.evaluators.hallucination import HallucinationEvaluator  # noqa: E402, F401
from src.evaluators.factual import FactualAccuracyEvaluator  # noqa: E402, F401
from src.evaluators.safety import ContentSafetyEvaluator  # noqa: E402, F401
from src.evaluators.quality import QualityEvaluator  # noqa: E402, F401

__all__ = [
    "BaseEvaluator",
    "EvalResult",
    "Flag",
    "Severity",
    "register",
    "get_evaluator",
    "available_evaluators",
    "HallucinationEvaluator",
    "FactualAccuracyEvaluator",
    "ContentSafetyEvaluator",
    "QualityEvaluator",
]
