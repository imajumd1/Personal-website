#!/usr/bin/env python3
"""Agent EVAL harness: run golden-case suites across a registry of agents.

Example:
  python eval_runner.py --agents wac,aurora
  python eval_runner.py --list
  python eval_runner.py --agents travel-agent --save-baseline
  python eval_runner.py --agents wac --llm-judge
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config" / "agents.yaml"
REPORTS_DIR = ROOT / "reports"
BASELINES_DIR = ROOT / "baselines"

PII_PATTERNS = [
    re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),  # US phone-ish
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN-ish
]


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "PyYAML is required to read config/agents.yaml.\n"
            "  pip install -r requirements.txt\n"
            f"Original error: {exc}"
        ) from exc
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid registry (expected mapping): {path}")
    return data


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


@dataclass
class DimensionScore:
    name: str
    score: float  # 0.0 - 1.0
    passed: bool
    notes: str = ""


@dataclass
class CaseResult:
    case_id: str
    agent_id: str
    passed: bool
    overall_score: float
    latency_ms: float
    dimensions: list[DimensionScore] = field(default_factory=list)
    output_excerpt: str = ""
    error: str = ""


@dataclass
class AgentReport:
    agent_id: str
    name: str
    passed: bool
    pass_rate: float
    mean_score: float
    cases: list[CaseResult] = field(default_factory=list)
    notes: str = ""


def render_template(template: str, values: dict[str, str]) -> str:
    out = template
    for key, val in values.items():
        out = out.replace("{{" + key + "}}", val)
    return out


def invoke_agent(agent: dict[str, Any], case: dict[str, Any]) -> tuple[str, float, str]:
    """Return (output, latency_ms, error)."""
    invoke = agent.get("invoke") or {}
    mode = (invoke.get("mode") or "fixture").lower()
    started = time.perf_counter()
    error = ""

    if mode == "fixture":
        output = str(case.get("fixture_output") or "")
        if not output:
            error = "fixture mode but case has empty fixture_output"
        latency = (time.perf_counter() - started) * 1000
        # Simulate a small floor so latency checks are meaningful in dry runs
        latency = max(latency, float(case.get("simulated_latency_ms") or 50))
        return output, latency, error

    if mode == "command":
        cmd = invoke.get("command") or ""
        if not cmd:
            return "", 0.0, "invoke.mode=command but command is empty"
        cmd = render_template(cmd, {"input": str(case.get("input") or "")})
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=agent.get("path") or None,
                capture_output=True,
                text=True,
                timeout=float(invoke.get("timeout_sec") or 120),
            )
            latency = (time.perf_counter() - started) * 1000
            output = proc.stdout or ""
            if proc.returncode != 0:
                error = (proc.stderr or f"exit {proc.returncode}").strip()
            return output, latency, error
        except Exception as exc:  # noqa: BLE001
            latency = (time.perf_counter() - started) * 1000
            return "", latency, str(exc)

    if mode == "http":
        url = invoke.get("url") or ""
        if not url:
            return "", 0.0, "invoke.mode=http but url is empty"
        method = (invoke.get("method") or "POST").upper()
        body = render_template(
            invoke.get("body_template") or '{"message": "{{input}}"}',
            {"input": str(case.get("input") or "")},
        )
        headers = {"Content-Type": "application/json"}
        headers.update(invoke.get("headers") or {})
        req = urllib.request.Request(
            url, data=body.encode("utf-8") if method != "GET" else None, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=float(invoke.get("timeout_sec") or 60)) as resp:
                output = resp.read().decode("utf-8", errors="replace")
            latency = (time.perf_counter() - started) * 1000
            return output, latency, ""
        except urllib.error.URLError as exc:
            latency = (time.perf_counter() - started) * 1000
            return "", latency, str(exc)

    return "", 0.0, f"unknown invoke.mode: {mode}"


def score_contains(output: str, needles: list[str] | None, want_present: bool) -> tuple[float, str]:
    if not needles:
        return 1.0, "no contains checks"
    missing = []
    found = []
    lower = output.lower()
    for n in needles:
        hit = n.lower() in lower
        if want_present and not hit:
            missing.append(n)
        if not want_present and hit:
            found.append(n)
    if want_present:
        if not missing:
            return 1.0, "all required phrases present"
        return 0.0, "missing: " + ", ".join(missing)
    if not found:
        return 1.0, "forbidden phrases absent"
    return 0.0, "found forbidden: " + ", ".join(found)


def score_pii(output: str, expect: dict[str, Any]) -> tuple[float, str]:
    if not expect.get("must_not_contain_pii_patterns"):
        return 1.0, "PII pattern check not required"
    hits = []
    for pat in PII_PATTERNS:
        m = pat.search(output)
        if m:
            hits.append(m.group(0))
    if hits:
        return 0.0, "PII-like patterns found: " + ", ".join(hits[:3])
    return 1.0, "no obvious PII patterns"


def score_groundedness(output: str, expect: dict[str, Any]) -> tuple[float, str]:
    phrases = expect.get("grounded_phrases") or []
    if not phrases:
        # If refuse expected, groundedness = refusal quality already covered elsewhere
        return 1.0, "no grounded_phrases specified"
    present = [p for p in phrases if p.lower() in output.lower()]
    ratio = len(present) / len(phrases)
    note = f"{len(present)}/{len(phrases)} grounded phrases present"
    return ratio, note


def score_latency(latency_ms: float, budget_ms: float) -> tuple[float, str]:
    if budget_ms <= 0:
        return 1.0, "no budget"
    if latency_ms <= budget_ms:
        return 1.0, f"{latency_ms:.0f}ms <= {budget_ms:.0f}ms"
    # Soft fail: score decays after budget
    over = latency_ms / budget_ms
    score = max(0.0, 1.0 - (over - 1.0))
    return score, f"{latency_ms:.0f}ms over budget {budget_ms:.0f}ms"


def score_task_success(output: str, expect: dict[str, Any], error: str) -> tuple[float, str]:
    if error:
        return 0.0, f"invoke error: {error}"
    if not output.strip():
        return 0.0, "empty output"
    must_ok, must_note = score_contains(output, expect.get("must_contain"), True)
    forbid_ok, forbid_note = score_contains(output, expect.get("must_not_contain"), False)
    refuse = bool(expect.get("refuse"))
    refuse_score = 1.0
    refuse_note = "refusal not required"
    if refuse:
        refusal_markers = ["cannot", "can't", "do not", "don't", "unable", "not able", "refuse"]
        if any(m in output.lower() for m in refusal_markers):
            refuse_note = "refusal language present"
        else:
            refuse_score = 0.0
            refuse_note = "expected refusal language missing"
    scores = [must_ok, forbid_ok, refuse_score]
    note = "; ".join([must_note, forbid_note, refuse_note])
    return sum(scores) / len(scores), note


def optional_llm_judge(case: dict[str, Any], output: str) -> tuple[float | None, str]:
    """Optional OpenAI-compatible judge. Returns (score or None, notes)."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None, "OPENAI_API_KEY not set; skipped"
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    rubric = (
        "Score 0 to 1 for task completion given the expected behavior. "
        "Reply JSON only: {\"score\": number, \"notes\": string}."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": rubric},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "input": case.get("input"),
                        "expect": case.get("expect"),
                        "output": output[:4000],
                    }
                ),
            },
        ],
        "temperature": 0,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text = body["choices"][0]["message"]["content"]
        # tolerate fenced JSON
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S)
        parsed = json.loads(text)
        return float(parsed.get("score", 0)), str(parsed.get("notes", ""))
    except Exception as exc:  # noqa: BLE001
        return None, f"llm-judge failed: {exc}"


def load_baseline(agent_id: str) -> dict[str, Any] | None:
    path = BASELINES_DIR / f"{agent_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def score_regression(agent_id: str, case_id: str, overall: float) -> tuple[float, str]:
    baseline = load_baseline(agent_id)
    if not baseline:
        return 1.0, "no baseline on disk (first run or use --save-baseline)"
    cases = {c["case_id"]: c for c in baseline.get("cases", [])}
    prev = cases.get(case_id)
    if not prev:
        return 1.0, "case not in baseline"
    prev_score = float(prev.get("overall_score", 0))
    # Allow 0.05 absolute drop
    if overall + 0.05 >= prev_score:
        return 1.0, f"ok vs baseline {prev_score:.2f}"
    drop = prev_score - overall
    return max(0.0, 1.0 - drop), f"regressed {drop:.2f} from baseline {prev_score:.2f}"


def evaluate_case(
    agent: dict[str, Any],
    case: dict[str, Any],
    defaults: dict[str, Any],
    use_llm_judge: bool,
) -> CaseResult:
    agent_id = agent["id"]
    case_id = case.get("id") or "unnamed"
    expect = case.get("expect") or {}
    budget = float(
        case.get("latency_budget_ms")
        or agent.get("latency_budget_ms")
        or defaults.get("latency_budget_ms")
        or 15000
    )

    output, latency_ms, error = invoke_agent(agent, case)
    dims: list[DimensionScore] = []

    task_score, task_note = score_task_success(output, expect, error)
    dims.append(DimensionScore("task_success", task_score, task_score >= 0.7, task_note))

    g_score, g_note = score_groundedness(output, expect)
    dims.append(DimensionScore("groundedness", g_score, g_score >= 0.7, g_note))

    p_score, p_note = score_pii(output, expect)
    dims.append(DimensionScore("safety_pii", p_score, p_score >= 1.0, p_note))

    l_score, l_note = score_latency(latency_ms, budget)
    dims.append(DimensionScore("latency", l_score, l_score >= 0.7, l_note))

    # provisional overall for regression compare
    provisional = sum(d.score for d in dims) / len(dims)
    r_score, r_note = score_regression(agent_id, case_id, provisional)
    dims.append(DimensionScore("regression", r_score, r_score >= 0.7, r_note))

    if use_llm_judge:
        j_score, j_note = optional_llm_judge(case, output)
        if j_score is not None:
            dims.append(DimensionScore("llm_judge", j_score, j_score >= 0.7, j_note))
        else:
            dims.append(DimensionScore("llm_judge", 0.0, True, j_note))  # skipped != fail

    overall = sum(d.score for d in dims if d.name != "llm_judge" or "skipped" not in d.notes.lower()) / max(
        1, len([d for d in dims if not (d.name == "llm_judge" and "skipped" in d.notes.lower())])
    )
    # Recompute without skipped llm_judge
    scored = [d for d in dims if not (d.name == "llm_judge" and ("skipped" in d.notes.lower() or "not set" in d.notes.lower()))]
    if not scored:
        scored = dims
    overall = sum(d.score for d in scored) / len(scored)
    passed = all(d.passed for d in scored if d.name != "llm_judge" or d.score > 0 or "failed" in d.notes.lower())
    # Clearer pass rule: core dims must pass
    core = {d.name: d for d in dims}
    passed = all(
        core[n].passed
        for n in ("task_success", "groundedness", "safety_pii", "latency", "regression")
        if n in core
    )

    return CaseResult(
        case_id=case_id,
        agent_id=agent_id,
        passed=passed,
        overall_score=round(overall, 3),
        latency_ms=round(latency_ms, 1),
        dimensions=dims,
        output_excerpt=(output[:280] + ("..." if len(output) > 280 else "")),
        error=error,
    )


def load_cases(agent: dict[str, Any]) -> list[dict[str, Any]]:
    rel = agent.get("golden") or f"golden/{agent['id']}/cases.json"
    path = ROOT / rel
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("cases") or [])


def evaluate_agent(
    agent: dict[str, Any],
    defaults: dict[str, Any],
    use_llm_judge: bool,
) -> AgentReport:
    cases = load_cases(agent)
    results = [evaluate_case(agent, c, defaults, use_llm_judge) for c in cases]
    if not results:
        return AgentReport(
            agent_id=agent["id"],
            name=agent.get("name") or agent["id"],
            passed=False,
            pass_rate=0.0,
            mean_score=0.0,
            cases=[],
            notes="No golden cases found",
        )
    pass_rate = sum(1 for r in results if r.passed) / len(results)
    mean_score = sum(r.overall_score for r in results) / len(results)
    threshold = float(defaults.get("pass_threshold") or 0.7)
    return AgentReport(
        agent_id=agent["id"],
        name=agent.get("name") or agent["id"],
        passed=pass_rate >= threshold and all(r.passed for r in results),
        pass_rate=round(pass_rate, 3),
        mean_score=round(mean_score, 3),
        cases=results,
        notes=agent.get("success") or "",
    )


def to_jsonable(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    return obj


def write_reports(reports: list[AgentReport], stamp: str) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agents": [to_jsonable(r) for r in reports],
        "summary": {
            "agents": len(reports),
            "passed": sum(1 for r in reports if r.passed),
            "failed": sum(1 for r in reports if not r.passed),
        },
    }
    json_path = REPORTS_DIR / f"eval-{stamp}.json"
    md_path = REPORTS_DIR / f"eval-{stamp}.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# Agent EVAL report ({stamp})",
        "",
        f"Agents: **{payload['summary']['passed']}/{payload['summary']['agents']}** passed",
        "",
    ]
    for r in reports:
        badge = "PASS" if r.passed else "FAIL"
        lines.append(f"## {r.name} (`{r.agent_id}`) - {badge}")
        lines.append("")
        lines.append(f"- Pass rate: {r.pass_rate:.0%} | Mean score: {r.mean_score:.2f}")
        if r.notes:
            lines.append(f"- Success criteria: {r.notes}")
        lines.append("")
        lines.append("| Case | Result | Score | Latency | Notes |")
        lines.append("|---|---|---:|---:|---|")
        for c in r.cases:
            dim_notes = "; ".join(f"{d.name}={d.score:.2f}" for d in c.dimensions)
            err = c.error or dim_notes
            lines.append(
                f"| `{c.case_id}` | {'PASS' if c.passed else 'FAIL'} | {c.overall_score:.2f} | "
                f"{c.latency_ms:.0f}ms | {err[:120]} |"
            )
        lines.append("")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def save_baselines(reports: list[AgentReport]) -> None:
    BASELINES_DIR.mkdir(parents=True, exist_ok=True)
    for r in reports:
        path = BASELINES_DIR / f"{r.agent_id}.json"
        payload = {
            "agent_id": r.agent_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "mean_score": r.mean_score,
            "cases": [
                {"case_id": c.case_id, "overall_score": c.overall_score, "passed": c.passed}
                for c in r.cases
            ],
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Saved baseline: {path}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run EVAL suites across registered agents.")
    p.add_argument(
        "--agents",
        help="Comma-separated agent ids (default: all). Example: wac,aurora,travel-agent",
    )
    p.add_argument("--list", action="store_true", help="List agents in the registry and exit")
    p.add_argument("--config", default=str(CONFIG_PATH), help="Path to agents.yaml")
    p.add_argument("--llm-judge", action="store_true", help="Enable optional OpenAI LLM-as-judge")
    p.add_argument("--save-baseline", action="store_true", help="Write baselines from this run")
    p.add_argument("--bucket", choices=["personal", "enterprise"], help="Filter by AI Builds bucket")
    return p.parse_args()


def main() -> int:
    load_dotenv(ROOT / ".env")
    args = parse_args()
    registry = load_yaml(Path(args.config))
    defaults = registry.get("defaults") or {}
    agents = list(registry.get("agents") or [])

    if args.bucket:
        agents = [a for a in agents if a.get("bucket") == args.bucket]

    if args.list:
        for a in agents:
            print(f"{a['id']:24}  {a.get('bucket', ''):10}  {a.get('name', '')}")
        return 0

    if args.agents:
        wanted = {x.strip() for x in args.agents.split(",") if x.strip()}
        missing = wanted - {a["id"] for a in agents}
        if missing:
            print("Unknown agent id(s):", ", ".join(sorted(missing)), file=sys.stderr)
            return 2
        agents = [a for a in agents if a["id"] in wanted]

    if not agents:
        print("No agents selected.", file=sys.stderr)
        return 2

    reports = [evaluate_agent(a, defaults, args.llm_judge) for a in agents]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json_path, md_path = write_reports(reports, stamp)
    if args.save_baseline:
        save_baselines(reports)

    print(f"Report (markdown): {md_path}")
    print(f"Report (json):     {json_path}")
    print()
    for r in reports:
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.agent_id:24} pass_rate={r.pass_rate:.0%} mean={r.mean_score:.2f}")

    return 0 if all(r.passed for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
