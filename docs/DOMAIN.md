# DOMAIN.md

## Core Concepts

### Evaluation Run
A single scoring pass over a candidate output or batch of outputs.

### Eval Suite
A configured set of evaluators and thresholds applied together.

### Baseline
The currently accepted output version, model version, prompt version, or agent version.

### Candidate
The proposed new version being tested against the baseline and acceptance rules.

### Golden Dataset
A set of representative tasks with source inputs, references, and expected constraints.

### Rubric
A structured quality specification used by deterministic logic, model judges, or both.

### Promotion Decision
A top-level action result such as `pass`, `fail`, or `human_review`.

## Evaluation Modes
- Single-output scoring via API (`POST /eval/run`)
- Interactive UI Demo scoring
- Batch benchmark run
- Baseline vs candidate comparison
- Policy-only validation
- Future runtime spot-check mode

## Domain Principle
This project is not just about assigning scores. It is about producing reliable decisions from evaluation evidence.

## Important Domain Questions
- Which metrics are blockers vs advisory?
- What thresholds define a regression?
- How are judge scores calibrated against deterministic checks?
- When should a run be escalated to human review?
