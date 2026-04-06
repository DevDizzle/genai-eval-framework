import uuid
import os
import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any

from src.contracts import EvalRunRequest, EvalRunResult
from src.decision_engine import make_promotion_decision
from src.benchmark import BenchmarkRunner, load_config, ModelOutput
from src.persistence import storage

app = FastAPI(
    title="GenAI Eval Framework API",
    description="Evaluation gate infrastructure for AI release confidence."
)

base_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(base_dir, "templates")
static_dir = os.path.join(base_dir, "static")

# Fallback in case folders don't exist yet
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir, exist_ok=True)
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
    
templates = Jinja2Templates(directory=templates_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Initialize evaluators
try:
    config = load_config("configs/eval_config.yaml")
except Exception:
    config = {"evaluators": {}}
runner = BenchmarkRunner(config)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
@app.get("/demo", response_class=HTMLResponse)
def demo_ui(request: Request):
    example = {
        "prompt": "Summarize the key points of the meeting.",
        "source": "The meeting started at 10 AM. Alice discussed the Q3 marketing budget, which was increased by 15%. Bob mentioned that the engineering team is blocked on the new deployment pipeline due to an AWS outage. Charlie suggested we delay the release by one week.",
        "baseline_output": "The meeting covered the Q3 budget and engineering blockers. The release is delayed.",
        "candidate_output": "Alice noted a 15% increase in the Q3 marketing budget. Bob reported the engineering team is blocked by an AWS outage. Charlie proposed a one-week release delay.",
        "gold_output": "Alice discussed a 15% increase in the Q3 marketing budget. Bob stated engineering is blocked by an AWS outage. Charlie suggested delaying the release by one week."
    }
    recent_runs = []
    try:
        recent_runs = storage.get_recent_runs(limit=5)
    except Exception:
        pass
        
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"example": example, "recent_runs": recent_runs}
    )

@app.post("/eval/run", response_model=EvalRunResult)
def run_eval(request: EvalRunRequest):
    run_id = str(uuid.uuid4())
    
    # Evaluate candidate
    candidate_out = ModelOutput(
        prompt=request.input.prompt,
        generated=request.candidate.output,
        source=request.input.source
    )
    res_candidate = runner.evaluate_sample(candidate_out)
    subscores = {name: r.score for name, r in res_candidate.items()}
    aggregate_score = sum(subscores.values()) / max(len(subscores), 1)
    
    # Collect flags (from evaluators)
    flags = []
    for r in res_candidate.values():
        for flag in r.flags:
            flags.append(flag.category)
            
    # Hardcoded simulation of flags if evaluators don't produce any but score is low
    if "hallucination" in subscores and subscores["hallucination"] < 0.5:
        if "hallucination" not in flags:
            flags.append("hallucination")
    
    baseline_agg = None
    if request.baseline:
        baseline_out = ModelOutput(
            prompt=request.input.prompt,
            generated=request.baseline.output,
            source=request.input.source
        )
        res_baseline = runner.evaluate_sample(baseline_out)
        baseline_subscores = {name: r.score for name, r in res_baseline.items()}
        baseline_agg = sum(baseline_subscores.values()) / max(len(baseline_subscores), 1)

    decision, reason = make_promotion_decision(
        request, 
        subscores, 
        flags, 
        aggregate_score, 
        baseline_agg
    )
    
    evaluator_method = "Deterministic Only"
    if "quality" in res_candidate and res_candidate["quality"].details:
        q_method = res_candidate["quality"].details.get("method")
        if q_method == "gemini_judge":
            evaluator_method = f"Deterministic + {runner.config.get('evaluators', {}).get('quality', {}).get('model', 'Gemini')} Judge"
        elif q_method == "heuristic":
            evaluator_method = "Deterministic + Heuristic Fallback"
            
    result = EvalRunResult(
        run_id=run_id,
        status="completed",
        aggregate_score=aggregate_score,
        subscores=subscores,
        flags=flags,
        decision=decision,
        reason=reason,
        evaluator_method=evaluator_method
    )

    # Persist the run
    run_data = {
        "run_id": run_id,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "suite_id": request.suite_id,
        "task_type": request.task_type,
        "candidate_id": request.candidate.id,
        "baseline_id": request.baseline.id if request.baseline else None,
        "aggregate_score": aggregate_score,
        "subscores": subscores,
        "flags": flags,
        "decision": decision,
        "reason": reason,
        "metadata": request.metadata,
        "version_metadata": request.version_metadata.model_dump() if request.version_metadata else {},
        "evaluator_method": evaluator_method,
    }
    
    if request.store_full_payloads:
        run_data["input"] = request.input.model_dump()
        run_data["candidate_output"] = request.candidate.output
        if request.baseline:
            run_data["baseline_output"] = request.baseline.output
    else:
        run_data["input_redacted"] = True
        run_data["output_redacted"] = True
        
    try:
        storage.save_run(run_id, run_data)
    except Exception as e:
        print(f"Error saving run to storage: {e}")

    return result


@app.get("/eval/runs", response_model=List[Dict[str, Any]])
def list_runs(limit: int = 10):
    try:
        return storage.get_recent_runs(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch runs: {str(e)}")

@app.get("/eval/runs/{run_id}", response_model=Dict[str, Any])
def get_run(run_id: str):
    try:
        run = storage.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return run
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch run: {str(e)}")
