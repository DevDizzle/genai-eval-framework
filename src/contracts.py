from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any

class Thresholds(BaseModel):
    min_score: float = 0.8
    block_on_flags: List[str] = Field(default_factory=list)

class Reference(BaseModel):
    gold_output: Optional[str] = None
    rubric: Optional[Dict[str, Any]] = None

class ModelPayload(BaseModel):
    id: str = "default"
    output: str

class InputData(BaseModel):
    prompt: str
    source: str = ""

class VersionMetadata(BaseModel):
    suite_version: Optional[str] = None
    prompt_version: Optional[str] = None
    agent_version: Optional[str] = None
    model_version: Optional[str] = None
    evaluator_version: Optional[str] = None
    app_version: Optional[str] = None
    commit_sha: Optional[str] = None

class EvalRunRequest(BaseModel):
    suite_id: str = "default-quality-gate"
    task_type: str = "summary"
    input: InputData
    candidate: ModelPayload
    baseline: Optional[ModelPayload] = None
    reference: Optional[Reference] = None
    thresholds: Thresholds = Field(default_factory=Thresholds)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    version_metadata: Optional[VersionMetadata] = Field(default_factory=VersionMetadata)
    store_full_payloads: bool = False

class EvalRunResult(BaseModel):
    run_id: str
    status: str
    aggregate_score: float
    subscores: Dict[str, float]
    flags: List[str]
    decision: str  # pass, fail, human_review
    reason: str
    evaluator_method: Optional[str] = None
