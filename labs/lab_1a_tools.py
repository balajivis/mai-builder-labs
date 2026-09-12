# -*- coding: utf-8 -*-
"""Lab 1a — TOOLS: what the agent can tell apart

Modern AI Pro · Level 3 · AI Builder · Day 1

Everyone will tell you to write good tool descriptions. This lab measures
whether that is true, which is a different and more useful activity.

Two knobs — the NAME and the DESCRIPTION — turned independently over six
questions, three runs per cell. Measured on the class model 2026-09-12, and it
came back dead stable ([6,6,6], [5,5,5]) so you will reproduce it:

                        good description    no description
      real names              6.0/6              6.0/6
      tool_a, tool_b …        6.0/6              5.0/6

      real names + MISLEADING description        5.0/6

The answer is not the one the advice implies. Name and description are REDUNDANT
signals for the same thing — either alone routes perfectly, and only removing
BOTH costs a question. Routing is robust.

But a description that points the WRONG way costs exactly as much as removing
both signals, and it does that while the names are still perfect. A wrong
description OVERRIDES a right name.

    You may be terse. You may not be wrong.

    python labs/lab_1a_tools.py           guided walkthrough in the terminal
    python labs/lab_1a_tools.py --web     turn the knobs yourself
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _kit import Stage, banner, client, meter, say, stages           # noqa: E402
from _lab1 import (ANON_NAMES, MISLEADING, PROFILES, ROUTING_6,      # noqa: E402
                   build_schema, first_tool, react)
from _web import (Knob, Panel, answer, note, port_from, section,     # noqa: E402
                  serve, step, table, wants_web)


def score_schema(cli, schema, anonymised: bool) -> tuple[int, list]:
    rows = []
    right = 0
    for q, want in ROUTING_6:
        target = ANON_NAMES[want] if anonymised else want
        got = first_tool(cli, q, schema)
        ok = got == target
        right += ok
        rows.append([("✓" if ok else "✗"), q, got, target])
    return right, rows


def _truthy(v) -> bool:
    return v in (True, "true", "on", "yes", 1, "1")


# ── web ──────────────────────────────────────────────────────────────────────

def run_web(cli, v: dict) -> str:
    anon = _truthy(v.get("anonymise"))
    describe = not _truthy(v.get("strip"))
    overrides = None
    raw = (v.get("descriptions") or "").strip()
    if raw == "__misleading__":
        overrides = MISLEADING
    elif raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                overrides = parsed
        except json.JSONDecodeError:
            pass

    schema = build_schema(anonymise=anon, describe=describe, overrides=overrides)
    right, rows = score_schema(cli, schema, anon)

    label = ("tool_a…" if anon else "real names") + " + " + ("no description" if not describe
                                                             else "misleading description" if raw == "__misleading__"
                                                             else "description")
    body = section(f"routing · {label} · {right}/{len(ROUTING_6)} correct",
                   table(["", "question", "it picked", "should be"], rows))

    if _truthy(v.get("grid")):
        cells = []
        for an in (False, True):
            for de in (True, False):
                r, _ = score_schema(cli, build_schema(anonymise=an, describe=de), an)
                cells.append([("tool_a, tool_b …" if an else "real names"),
                              ("description" if de else "no description"),
                              f"{r}/{len(ROUTING_6)}"])
        body += section("the 2×2 — which knob carries the signal?",
                        table(["names", "descriptions", "routed correctly"], cells))

    if v.get("task"):
        steps: list[str] = []
        out = react(cli, v["task"], profile=PROFILES["operations"], schema=schema, budget=6,
                    on_step=lambda k, lab, det: steps.append(step(lab, det, k)))
        body += section("a full run on this variant", "".join(steps) + answer(out))

    body += section("read this", note(
        "The functions behind these tools never change — not one line, in any variant. "
        "Only the strings the model reads. Over three runs a cell: either signal alone "
        "routes 6/6, and only removing BOTH drops it to 5/6. Routing is robust. But the "
        "misleading preset — perfect names, descriptions pointing the wrong way — also "
        "scores 5/6, so a wrong description costs as much as having no interface at all. "
        "You may be terse. You may not be wrong. A single run of any cell is noisy; run "
        "it a few times before you believe a one-question difference."))
    return body


def web(cli, port: int) -> None:
    serve(Panel(
        title="Tools — what it can tell apart",
        subtitle="Two knobs, turned independently: the tool's NAME and its DESCRIPTION. "
                 "Same six questions, same four functions underneath. Which one is "
                 "actually carrying the routing?",
        intro="Tick <b>run the 2×2</b> first — that is the whole experiment in one table. "
              "Write down your prediction before you press it. Then load the "
              "<b>__misleading__</b> preset, which keeps every tool's perfect name and "
              "only points its description the wrong way. One run per cell is noisy; the "
              "published numbers are three runs each.",
        knobs=[
            Knob("grid", "Run the 2×2 grid", "select", default="true",
                 options=[("true", "yes — all four cells (8 calls)"), ("false", "no — just this one")]),
            Knob("anonymise", "Tool names", "select", default="false",
                 options=[("false", "real names — search_policy, check_limits…"),
                          ("true", "anonymous — tool_a, tool_b, tool_c, tool_d")]),
            Knob("strip", "Descriptions", "select", default="false",
                 options=[("false", "keep them"), ("true", "strip them entirely")]),
            Knob("descriptions", "Override descriptions (JSON, or the word __misleading__)",
                 "textarea", default="",
                 help='Try __misleading__ for the measured 5.0/6 case, or paste '
                      '{"check_limits": "…"} to write your own.'),
            Knob("task", "Optional: run a full task on this variant", "text", default=""),
        ],
        run=run_web, button="Score the routing",
    ), cli, port=port)


# ── cli ──────────────────────────────────────────────────────────────────────

def _show(cli, schema, anon, label):
    right, rows = score_schema(cli, schema, anon)
    say(f"[bold yellow]── {label} ──[/bold yellow]")
    for mark, q, got, want in rows:
        colour = "green" if mark == "✓" else "red"
        say(f"  [{colour}]{mark}[/{colour}] {q[:44]:<46} → [bold]{got}[/bold]"
            + ("" if mark == "✓" else f" [dim](wanted {want})[/dim]"))
    say(f"  [bold]{right}/{len(ROUTING_6)}[/bold]\n")
    return right


def stage_grid(cli):
    say("Two knobs, turned independently. Six questions each.\n")
    cells = {}
    for anon in (False, True):
        for desc in (True, False):
            label = ("tool_a…" if anon else "real names") + " + " + ("description" if desc else "NO description")
            cells[(anon, desc)] = _show(cli, build_schema(anonymise=anon, describe=desc), anon, label)
    say("[bold]                      description   no description[/bold]")
    say(f"  real names          {cells[(False, True)]:>9}/6   {cells[(False, False)]:>9}/6")
    say(f"  tool_a, tool_b …    {cells[(True, True)]:>9}/6   {cells[(True, False)]:>9}/6")


def stage_misleading(cli):
    say("Now a description that points the wrong way — the case nobody expects.\n")
    _show(cli, build_schema(overrides=MISLEADING), False, "misleading descriptions")
    say("[dim]Compare that against the no-description row above.[/dim]")


if __name__ == "__main__":
    cli = client()
    if wants_web():
        web(cli, port_from(default=7860))
        sys.exit(0)
    banner("Level 3 · AI Builder · Day 1", "Lab 1a · Tools — what it can tell apart")
    say("[dim]Tip: --web lets you turn both knobs and edit descriptions live.[/dim]\n")
    stages(cli, [
        Stage("Which knob carries the routing?",
              why="Everyone says write good tool descriptions. Measure it instead. Two "
                  "knobs — the NAME and the DESCRIPTION — turned independently over the "
                  "same six questions, with the same four functions underneath. Before "
                  "it runs, write down which you think matters more.",
              fn=stage_grid,
              logic="Not the answer the advice implies. The name and the description are "
                    "REDUNDANT — either one alone routes everything, and only removing "
                    "BOTH costs a question. Routing is more robust than tool-writing "
                    "guides suggest, and polishing a description that already sits under "
                    "a clear name buys you nothing measurable. Which makes the next "
                    "stage the one that matters."),
        Stage("Worse than nothing",
              why="If a missing description costs you one question, what does a WRONG "
                  "one cost? Here lookup_client is described as carrying 'their standing "
                  "limit value' — true, and exactly the phrase that makes the model reach "
                  "for it when asked whether an amount fits.",
              fn=stage_misleading,
              logic="It cost exactly as much as deleting BOTH signals — and it did that "
                    "while every tool still had a perfect name. A wrong description "
                    "overrides a right name; absence does not. So the rule is not 'write "
                    "rich descriptions', it is: you may be terse, you may not be wrong. "
                    "The fix is never in the prompt and never in a bigger model — read "
                    "your tool list as if you were the one being asked to choose from it, "
                    "and delete every phrase that could send you to the wrong tool."),
    ])
    meter.show()
