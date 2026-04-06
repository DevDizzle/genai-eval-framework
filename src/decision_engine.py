from src.contracts import EvalRunRequest
from typing import Dict, List, Tuple

def make_promotion_decision(
    request: EvalRunRequest,
    subscores: Dict[str, float],
    flags: List[str],
    aggregate_score: float,
    baseline_aggregate_score: float = None
) -> Tuple[str, str]:
    """
    Returns (decision, reason)
    decision can be 'pass', 'fail', 'human_review'
    """
    # 1. Check blocker flags
    for flag in flags:
        if flag in request.thresholds.block_on_flags:
            return "fail", f"Blocked on critical flag: {flag}"
    
    # 2. Check aggregate score vs min_score threshold
    if aggregate_score < request.thresholds.min_score:
        return "fail", f"Aggregate score {aggregate_score:.2f} is below minimum threshold {request.thresholds.min_score:.2f}"
        
    # 3. Check baseline comparison regression
    if baseline_aggregate_score is not None:
        if aggregate_score < baseline_aggregate_score - 0.05:
            return "fail", f"Regression detected: Candidate ({aggregate_score:.2f}) is significantly worse than Baseline ({baseline_aggregate_score:.2f})"
        elif aggregate_score < baseline_aggregate_score:
            return "human_review", f"Slight regression: Candidate ({aggregate_score:.2f}) vs Baseline ({baseline_aggregate_score:.2f}). Requires review."
            
    # 4. Review advisory flags (flags not in block_on_flags but present)
    if flags:
        return "human_review", f"Passed thresholds but flagged for review: {', '.join(flags)}"

    # Default Pass
    if baseline_aggregate_score is not None and aggregate_score >= baseline_aggregate_score:
        return "pass", "Candidate meets or exceeds baseline aggregate score with no critical regressions."
    return "pass", "Candidate meets all promotion criteria."
