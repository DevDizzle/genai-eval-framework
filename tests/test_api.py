from fastapi.testclient import TestClient
from src.api import app
from src.contracts import EvalRunRequest

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_demo_ui_loads():
    response = client.get("/demo")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Evaluation Gate Infrastructure" in response.text

def test_eval_run_pass():
    payload = {
        "suite_id": "default",
        "task_type": "summary",
        "input": {
            "prompt": "Summarize this",
            "source": "The stock market went up today due to tech earnings."
        },
        "candidate": {
            "id": "v2",
            "output": "Tech earnings drove the stock market up today."
        },
        "baseline": {
            "id": "v1",
            "output": "The stock market went up today."
        },
        "thresholds": {
            "min_score": 0.5,
            "block_on_flags": ["critical_error"]
        }
    }
    response = client.post("/eval/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "aggregate_score" in data
    assert "decision" in data
    # Might pass or human_review depending on scores, but should return a valid decision
    assert data["decision"] in ["pass", "fail", "human_review"]

def test_decision_logic_fail():
    from src.decision_engine import make_promotion_decision
    from src.contracts import EvalRunRequest
    
    req = EvalRunRequest(**{
        "suite_id": "test",
        "task_type": "summary",
        "input": {"prompt": "test", "source": "test"},
        "candidate": {"id": "c1", "output": "test"},
        "thresholds": {"min_score": 0.8, "block_on_flags": ["toxic"]}
    })
    
    # Force a failure due to threshold
    decision, reason = make_promotion_decision(req, {}, [], 0.5, 0.9)
    assert decision == "fail"
    assert "below minimum threshold" in reason
    
    # Force a failure due to flag
    decision, reason = make_promotion_decision(req, {}, ["toxic"], 0.9, 0.8)
    assert decision == "fail"
    assert "Blocked on critical flag" in reason

def test_runs_history_api():
    # First, list runs to get current length
    resp1 = client.get("/eval/runs")
    assert resp1.status_code == 200
    initial_runs = len(resp1.json())
    
    # Trigger a run to insert into memory
    payload = {
        "suite_id": "test_history",
        "task_type": "summary",
        "input": {"prompt": "p", "source": "s"},
        "candidate": {"id": "c", "output": "o"},
        "thresholds": {"min_score": 0.0},
        "store_full_payloads": False,
        "version_metadata": {
            "suite_version": "v1.0",
            "prompt_version": "v2.1"
        }
    }
    run_resp = client.post("/eval/run", json=payload)
    run_id = run_resp.json()["run_id"]
    
    # Check that list size increased
    resp2 = client.get("/eval/runs")
    assert resp2.status_code == 200
    assert len(resp2.json()) == initial_runs + 1
    
    # Fetch specific run
    resp3 = client.get(f"/eval/runs/{run_id}")
    assert resp3.status_code == 200
    run_data = resp3.json()
    assert run_data["run_id"] == run_id
    assert run_data["version_metadata"]["suite_version"] == "v1.0"
    assert run_data["version_metadata"]["prompt_version"] == "v2.1"
    assert "input" not in run_data
    assert run_data["input_redacted"] is True

def test_get_missing_run():
    resp = client.get("/eval/runs/does_not_exist_123")
    assert resp.status_code == 404
