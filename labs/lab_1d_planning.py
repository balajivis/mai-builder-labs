# -*- coding: utf-8 -*-
"""Lab 1d — PLANNING: how the agent decides

Modern AI Pro · Level 3 · AI Builder · Day 1

Three architectures, one task, one table. The point is NOT how to implement
ReWOO. It is which shape of problem each planner suits, and what each costs:

    ReAct              think between every action. Adapts. Pays a model call per step.
    Plan-and-Execute   commit to the whole route first, run it, then synthesise.
                       Cheap. Blind to anything the plan did not anticipate.
    ReWOO              plan with #E placeholders, execute with the model OUT of the
                       loop, solve once at the end. Fewest calls. Blind in the same way.

The task has a surprise in it — the honest answer is NO, on settlement — which
is exactly the condition under which an adaptive planner earns its cost.

    python labs/lab_1d_planning.py           guided walkthrough in the terminal
    python labs/lab_1d_planning.py --web     knobs in the browser
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _kit import Stage, banner, chat, client, meter, say, stages     # noqa: E402
from _lab1 import (MUST_MENTION, PROFILES, SCHEMA, TASK, Probe,      # noqa: E402
                   call_tool, react)
from _web import (Knob, Panel, answer, note, port_from, section,     # noqa: E402
                  serve, step, table, wants_web)

CATALOG = "\n".join(f"- {s['function']['name']}: {s['function']['description']}"
                    for s in SCHEMA)


def _json_array(raw: str) -> list[dict]:
    """Models fence JSON even when told not to. Recover rather than crash the lab."""
    m = re.search(r"\[.*\]", raw or "", re.S)
    if not m:
        return []
    try:
        out = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return [s for s in out if isinstance(s, dict)]


# ── the three planners ───────────────────────────────────────────────────────

def plan_react(cli, task: str, profile: str, on_step) -> str:
    return react(cli, task, profile=profile, budget=8, on_step=on_step)


def plan_and_execute(cli, task: str, profile: str, on_step) -> str:
    raw = chat(cli, [
        {"role": "system", "content": "You plan tool calls. Output ONLY a JSON array of "
         '{"tool":..., "args":{...}} — no prose, no markdown fence.'},
        {"role": "user", "content": f"Tools:\n{CATALOG}\n\nTask: {task}\n\n"
                                    "Plan every call needed, in order."}], label="plan")
    steps = _json_array(raw)
    on_step("warn", f"planned {len(steps)} call(s) up front", "before seeing any result")
    obs = []
    for s in steps:
        args = s.get("args") or {}
        out = call_tool(s.get("tool", ""), args)
        on_step("", f"{s.get('tool')}({json.dumps(args)[:52]})", out[:84])
        obs.append(f"{s.get('tool')}({json.dumps(args)}) -> {out}")
    return chat(cli, [
        {"role": "system", "content": profile},
        {"role": "user", "content": f"Task: {task}\n\nObservations:\n" + "\n".join(obs)
                                    + "\n\nAnswer the task."}], label="synthesise")


def rewoo(cli, task: str, profile: str, on_step) -> str:
    raw = chat(cli, [
        {"role": "system", "content":
            'You write a ReWOO plan: a JSON array of {"id":"#E1","tool":...,"args":{...}}. '
            'An arg may reference an earlier result by its id, e.g. "#E1". '
            "Output ONLY the JSON array."},
        {"role": "user", "content": f"Tools:\n{CATALOG}\n\nTask: {task}"}], label="plan")
    steps, results = _json_array(raw), {}
    on_step("warn", f"planned {len(steps)} step(s) with placeholders",
            "the model now leaves the loop entirely")
    for i, s in enumerate(steps, 1):
        args = {k: (results.get(v, v) if isinstance(v, str) else v)
                for k, v in (s.get("args") or {}).items()}
        out = call_tool(s.get("tool", ""), args)
        results[s.get("id") or f"#E{i}"] = out
        on_step("", f"{s.get('tool')}({json.dumps(args)[:52]})", out[:84])
    evidence = "\n".join(f"{k} = {v}" for k, v in results.items())
    return chat(cli, [
        {"role": "system", "content": profile},
        {"role": "user", "content": f"Task: {task}\n\nEvidence:\n{evidence}\n\n"
                                    "Answer the task."}], label="solve")


PLANNERS = {"ReAct": plan_react, "Plan-and-Execute": plan_and_execute, "ReWOO": rewoo}


def run_one(cli, name: str, task: str, profile: str, on_step) -> dict:
    p = Probe()
    try:
        out = PLANNERS[name](cli, task, profile, on_step) or ""
    except Exception as e:  # noqa: BLE001
        on_step("bad", f"{name} failed", str(e)[:120])
        out = ""
    return {"name": name, **p.done(out)}


# ── web ──────────────────────────────────────────────────────────────────────

def run_web(cli, v: dict) -> str:
    task = (v.get("task") or "").strip() or TASK
    profile = (v.get("profile") or "").strip() or PROFILES["operations"]
    chosen = v.get("planner") or "all"
    names = list(PLANNERS) if chosen == "all" else [chosen]

    body, results = "", []
    for name in names:
        steps: list[str] = []
        r = run_one(cli, name, task, profile,
                    lambda k, lab, det: steps.append(step(lab, det, k)))
        results.append(r)
        body += section(
            f"{name} · {r['calls']} LLM calls · {r['tokens']} tok · {r['secs']}s",
            "".join(steps) + answer(r["answer"] or "(no answer)"))

    if len(results) > 1:
        best = min(range(len(results)),
                   key=lambda i: (-results[i]["hits"], results[i]["tokens"]))
        body += section("the comparison", table(
            ["planner", "LLM calls", "tokens", "secs", f"facts (of {len(MUST_MENTION)})"],
            [[r["name"], r["calls"], r["tokens"], f"{r['secs']}s", r["hits"]] for r in results],
            highlight=best))
    for r in results:
        if r["missed"]:
            body += note(f"{r['name']} missed: {', '.join(r['missed'])}", "warn")

    body += section("read this", note(
        "Read the table as a trade, not a ranking. The cheap planners are right when the "
        "route is knowable up front. ReAct earns its cost exactly when a step can "
        "surprise you — and this task has a surprise in it, because the honest answer is "
        "NO on settlement. The facts column is what makes this a measurement rather than "
        "an opinion: those four were frozen before any planner ran. If a cheap planner "
        "scores the same, take the cheap planner."))
    return body


def web(cli, port: int) -> None:
    serve(Panel(
        title="Planning — how it decides",
        subtitle="One task, four tools, three architectures. Only the planner moves. "
                 "The scorecard was frozen before any of them ran.",
        intro="Run <b>all three</b> first and read the table. Then try a task with NO "
              "surprise in it (\"What is C-2288's limit?\") and watch ReAct's advantage "
              "disappear — that is the whole lesson. The four facts being scored: "
              "notional ≈ $177k · over the $50k desk-head threshold · within the $250k "
              "client limit · same-day refused because AXR-7 settles T+2.",
        knobs=[
            Knob("planner", "Architecture", "select", default="all",
                 options=[("all", "all three — compare"), ("ReAct", "ReAct only"),
                          ("Plan-and-Execute", "Plan-and-Execute only"), ("ReWOO", "ReWOO only")]),
            Knob("task", "The task", "textarea", default=TASK,
                 help="The scorecard only fits the default task — change it and the "
                      "facts column stops meaning anything."),
            Knob("profile", "Profile", "textarea", default=PROFILES["operations"]),
        ],
        run=run_web, button="Run the bake-off",
    ), cli, port=port)


# ── cli ──────────────────────────────────────────────────────────────────────

def stage_bakeoff(cli):
    say("One task, three architectures, the same four tools.\n")
    say(f"[dim]{TASK}[/dim]\n")
    results = []
    for name in PLANNERS:
        say(f"[bold yellow]── {name} ──[/bold yellow]")
        r = run_one(cli, name, TASK, PROFILES["operations"],
                    lambda k, lab, det: say(
                        f"  [{'green' if k == 'good' else 'red' if k == 'bad' else 'yellow' if k == 'warn' else 'dim'}]"
                        f"{'✓' if k == 'good' else '⛔' if k == 'bad' else '→'}[/] {lab}"))
        results.append(r)
        say(f"  [dim]{r['calls']} calls · {r['tokens']} tok · {r['secs']}s[/dim]")
        say(f"  {(r['answer'] or '(no answer)')[:240]}\n")

    say(f"[bold]  planner              calls   tokens    secs   facts/{len(MUST_MENTION)}[/bold]")
    for r in results:
        say(f"  {r['name']:<20} {r['calls']:>5}   {r['tokens']:>6}   {r['secs']:>5}   {r['hits']}")
    say()
    for r in results:
        if r["missed"]:
            say(f"  [yellow]{r['name']} missed:[/yellow] {', '.join(r['missed'])}")


if __name__ == "__main__":
    cli = client()
    if wants_web():
        web(cli, port_from(default=7863))
        sys.exit(0)
    banner("Level 3 · AI Builder · Day 1", "Lab 1d · Planning — how it decides")
    say("[dim]Tip: --web runs the same bake-off with the task editable.[/dim]\n")
    stages(cli, [
        Stage("Three architectures, one scorecard",
              why="ReAct thinks between every action, so it adapts — and pays a full "
                  "model call per step. Plan-and-Execute commits to the whole route "
                  "before it sees anything, which is cheap and brittle. ReWOO plans with "
                  "placeholders and executes with the model OUT of the loop: the fewest "
                  "calls of the three, and blind to surprise in the same way. Same task, "
                  "same tools; only the architecture moves.",
              fn=stage_bakeoff,
              logic="Read the table as a trade, not a ranking. The cheapest planner is "
                    "right when the route is knowable up front; ReAct earns its cost "
                    "exactly when a step can surprise you — and this task has a surprise "
                    "in it, because the honest answer is NO on settlement. The facts "
                    "column is what makes this a measurement rather than an opinion: "
                    "those four were frozen before any planner ran. If a cheap planner "
                    "scores the same, take the cheap planner."),
    ])
    meter.show()
