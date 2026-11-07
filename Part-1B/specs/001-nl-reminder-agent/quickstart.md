# Quickstart & Validation Guide

**Feature**: [spec.md](spec.md) | **Interfaces**: [contracts/interfaces.md](contracts/interfaces.md)

Run all commands from `Part-1B/` in Git Bash (or PowerShell with equivalent syntax).

## 1. Setup

```bash
py -3.11 -m venv .venv
source .venv/Scripts/activate            # PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
cp .env.example .env                     # then set ANTHROPIC_API_KEY=... (only needed for live runs)
git check-ignore .env                    # must print ".env" (Constitution IX)
```

## 2. Offline validation (no API key, no cost)

| Step | Command | Expected |
|------|---------|----------|
| Unit tests (stubbed client) | `python -m pytest` | All pass. The suite covers AC-01 to AC-60 with scripted model replies. Network access is never needed. |
| Quality gates | `python .harness/run_harness.py` | ruff PASS, bandit PASS, pytest PASS, clock-ban PASS, secret-scan PASS. Exit 0. Evidence is in `evidence/harness-results/<stamp>/`. |
| Dataset check | `python .harness/evaluate.py check-dataset` | Exit 0. Reports at least 18 cases and every category minimum met (FR-032, FR-034). |
| Input error | `reminder-agent --text "hi" --now 2026-11-10T10:00:00+05:30 --timezone Mars/Olympus; echo $?` | stderr `{"status":"input_error","category":"invalid_timezone",...}`, exit `3`, and no model call (AC-16). |
| Empty input | `reminder-agent --text "" --now 2026-11-10T10:00:00+05:30 --timezone Asia/Kolkata` | stdout clarify decision, exit `0`, and no model call (AC-22). |

## 3. Live smoke test (costs well under $0.01)

```bash
reminder-agent --text "remind me to call mom tomorrow at 9am" \
  --now 2026-11-10T10:00:00+05:30 --timezone Asia/Kolkata
```

Expected: `{"intent":"create","task":"call mom","due_at":"2026-11-11T09:00:00+05:30","target_id":null,"snooze_minutes":null,"clarification_question":null,"refusal_reason":null}` (AC-01; the exact task wording may differ but must contain "call" and "mom").

DST check (AC-08):

```bash
reminder-agent --text "remind me tomorrow at 9am to call the bank" \
  --now 2026-10-31T12:00:00-04:00 --timezone America/New_York
```

Expected: `due_at` is `2026-11-01T09:00:00-05:00`.

## 4. Evaluation run

```bash
python .harness/evaluate.py live                 # live run; prints the pre-flight cost estimate first
python .harness/evaluate.py replay --run evidence/eval-runs/<run_id>   # zero API calls
```

Expected:

- `evidence/eval-runs/<run_id>/` contains `raw/*.json`, `eval-results.json` (valid per [contracts/eval_results.schema.json](contracts/eval_results.schema.json)) and `summary.md`.
- The report shows model `claude-haiku-5-5`, `max_tokens` 300, `temperature` null (not sent), `dataset_sha256`, and threshold `0.85 / 1.0 / 2 / 0.9`.
- Estimated cost is about $0.005 per run and always ≤ $0.50.
- The replay reproduces every case status and the verdict exactly (AC-50).
- `grep -r "sk-ant-" evidence/` finds nothing (AC-49, SC-007).

Final submission run:

```bash
python .harness/run_harness.py --final
python .harness/evaluate.py live --final         # copies eval-results.json to evidence/, appends harness-log.md
python .harness/evaluate.py replay --run evidence/eval-runs/<final_run_id> --final
```

PASS means SC-001 is met. On FAIL, `summary.md` lists each failing case as
`<case_id> <layer> <FR-id>: <message>` for feeding back to the coding agent. The dataset,
expected values and threshold MUST NOT be edited to make a run pass (Constitution V, FR-043).
