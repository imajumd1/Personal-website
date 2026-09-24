# Agent EVAL harness

Config-driven EVAL for agents Ishita has built (AI Builds catalog). Point it at one or more agents, run golden cases, and get a markdown + JSON scoreboard.

## What it measures

| Dimension | Meaning |
|---|---|
| `task_success` | Did the agent complete the job (required phrases, refusals, forbidden content)? |
| `groundedness` | Did the output stay tied to allowed evidence phrases? |
| `safety_pii` | Optional check that phone/email/SSN-like patterns stay out of the output |
| `latency` | End-to-end time vs per-case / per-agent budget |
| `regression` | Score vs last saved baseline (`--save-baseline`) |
| `llm_judge` | Optional OpenAI judge (`--llm-judge`) |

## Setup

```bash
cd agent-eval
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # only needed for --llm-judge
```

Dependencies are light: **stdlib + PyYAML**. LLM-as-judge needs an API key in `.env` (never commit `.env`).

## Run

List agents:

```bash
python eval_runner.py --list
```

EVAL selected agents (fixture mode uses recorded outputs in golden cases):

```bash
python eval_runner.py --agents wac,aurora
python eval_runner.py --agents travel-agent --save-baseline
python eval_runner.py --bucket enterprise
python eval_runner.py --agents wac --llm-judge
```

Reports land in `reports/eval-<timestamp>.md` and `.json`. Exit code `0` if all selected agents pass.

## Wire a live agent

In `config/agents.yaml`, set `invoke`:

**Command**

```yaml
invoke:
  mode: command
  command: 'python run_eval_case.py --input "{{input}}"'
  timeout_sec: 60
```

**HTTP**

```yaml
invoke:
  mode: http
  url: https://your-agent.up.railway.app/api/chat
  method: POST
  body_template: '{"message": "{{input}}"}'
  timeout_sec: 60
```

Until live invoke is ready, leave `mode: fixture` and edit `fixture_output` in `golden/<agent>/cases.json`.

## Add or edit golden cases

1. Open `golden/<agent-id>/cases.json`
2. Add `input`, `fixture_output` (or rely on live invoke), and `expect` rules:
   - `must_contain` / `must_not_contain`
   - `grounded_phrases`
   - `must_not_contain_pii_patterns: true`
   - `refuse: true` when the agent should decline
3. Re-run the suite. Use `--save-baseline` when you trust a green run.

Starter suites with real-shaped cases: **wac**, **aurora**, **travel-agent**. Other catalog agents have one placeholder case each.

## CI / preflight idea

```bash
python eval_runner.py --agents wac,aurora,travel-agent
```

Gate merge or Railway promote on exit code 0. Pair with Agent Preflight before any public share.

## Layout

```
agent-eval/
  eval_runner.py
  config/agents.yaml
  golden/<agent>/cases.json
  baselines/          # written by --save-baseline
  reports/            # generated reports (gitignored)
  .env.example
  requirements.txt
```
