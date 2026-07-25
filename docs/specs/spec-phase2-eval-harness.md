# Phase 2 spec — eval harness in CI

Goal: a golden-set + rubric evaluation harness that runs in CI and demonstrably catches a seeded regression. Converts talk-track 20 (LLM-as-judge calibration, offline evals) from study-tier to owned, and turns your golden-examples practice (S3) into running code.

## Golden set — 10 QA pairs

Follow the established MCP-eval methodology:
- **Independent** (no question depends on another), **read-only**, **complex** (each requires 2+ tool calls), **realistic** (questions a network owner would actually ask), **verifiable** (single answer checkable by string/number comparison), **stable** (answer won't drift as new data arrives — pin time windows).
- Process: inspect tools → explore data read-only → draft questions → **solve each by hand first** and record the verified answer.
- Format: XML `<evaluation><qa_pair><question/><answer/></qa_pair>…</evaluation>` — the ecosystem-standard shape.

Example shape (calibrate difficulty to this): "During the chaos event closest to [pinned date], which probe type degraded first, and how many minutes before the speedtest probe showed impact?" — multi-tool, verifiable, stable.

## Rubric layer — for non-exact outputs

`towerwatch_diagnose_symptom` and `analyze_window` return prose. Score them your way:
- Golden example + rubric per task (the ADR-guidelines pattern, applied): required elements present, no fabricated metrics, correct causal ordering.
- **Programmatic checks first** (element presence, number matching), **LLM-as-judge second** — and calibrate the judge: score 10 outputs by hand, run the judge on the same 10, report agreement %. That agreement number is the talk-track-20 data point.

## CI integration

- GitHub Actions: harness runs on every PR; fails the build under threshold (suggest: 8/10 exact QA + rubric mean ≥ threshold you set after baseline).
- **Seeded-regression test (the showpiece):** on a branch, deliberately degrade one tool definition — rename a parameter or blur its description. The PR must fail with the eval output showing which questions broke. The receipt is the failing CI run link. This is "evals as stateless gates" — your principles framework, executable.

## Metrics to emit (per run)

Task success rate · tool-selection accuracy per question (did it call the right tools) · turns per task · tokens per task. Persist as a CSV per run so Phase 3 can diff against baselines.

## Acceptance criteria (stateless gates)

- [ ] 10 QA pairs committed in XML, each with a hand-verified answer noted in a solutions file.
- [ ] Rubric files committed for the two prose tools; judge-vs-hand agreement % reported.
- [ ] CI runs the harness on PR; green run linked in README.
- [ ] Seeded-regression PR exists, failed CI linked, then closed unmerged.
- [ ] Metrics CSV emitted per run.

## Writeup

3+ surprises (judge calibration usually supplies at least one), threshold rationale, and what a production version adds (online sampling, drift detection — name them, don't build them).
