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

      real names + MISLEADING description        5.5/6  (noisier: [6,5])

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
                   build_schema, first_tool, react, real_name)
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

# The five interfaces the same four functions can wear. Ask ONE question and see
# where they disagree — divergence is the whole finding, and it is far more
# legible on a question you wrote than on a battery someone else froze.
VARIANTS = [
    ("real names + description", dict()),
    ("real names, NO description", dict(describe=False)),
    ("tool_a…, description", dict(anonymise=True)),
    ("tool_a…, NO description", dict(anonymise=True, describe=False)),
    ("real names + MISLEADING description", dict(overrides=MISLEADING)),
]


def ask_variants(cli, question: str, expected: str | None) -> tuple[list[list], set]:
    """Route one question through every interface. Returns rows + the distinct picks."""
    rows, picks = [], set()
    for label, kw in VARIANTS:
        anon = kw.get("anonymise", False)
        got = first_tool(cli, question, build_schema(**kw))
        canon = real_name(got)          # tool_d and check_refund_window are the same function
        picks.add(canon)
        mark = "" if expected is None else ("✓" if canon == expected else "✗")
        rows.append([mark, label, got, canon if anon else ""])
    return rows, picks


def run_web(cli, v: dict) -> str:
    question = (v.get("question") or "").strip()
    if not question:
        return section("ask it something", note(
            "Type a question, or tap one of the suggestions under the box. Anything "
            "the four Orbit tools could plausibly answer — or deliberately something "
            "none of them can."))

    expected = (v.get("expected") or "").strip() or None
    if expected == "(let me judge)":
        expected = None

    rows, picks = ask_variants(cli, question, expected)
    headers = ["", "interface", "it reached for", "= which function"]
    body = section(f"“{question}”", table(headers, rows))

    if len(picks) == 1:
        body += note(f"All five interfaces agreed: {picks.pop()}. Routing held even with "
                     "the names stripped to tool_a and the descriptions pointing the wrong "
                     "way. Most questions do this — try to find one that breaks it.", "good")
    else:
        body += note(f"They disagree — {len(picks)} different functions across five "
                     f"interfaces: {', '.join(sorted(picks))}. This is the question worth "
                     "keeping. Read the rows that differ and ask what signal they lost.", "warn")

    if _truthy(v.get("battery")):
        cells = []
        for label, kw in VARIANTS:
            anon = kw.get("anonymise", False)
            r = sum(real_name(first_tool(cli, q, build_schema(**kw))) == want
                    for q, want in ROUTING_6)
            cells.append([label, f"{r}/{len(ROUTING_6)}"])
        body += section("the same five interfaces over six fixed questions",
                        table(["interface", "routed correctly"], cells))
        body += note("Three of the five usually tie. Either the name or the description "
                     "alone carries it; only losing BOTH — or being actively misled — "
                     "costs a question.", "")

    if _truthy(v.get("full")):
        steps: list[str] = []
        out = react(cli, question, profile=PROFILES["support"],
                    schema=build_schema(), budget=6,
                    on_step=lambda k, lab, det: steps.append(step(lab, det, k)))
        body += section("the full agent run (good interface)", "".join(steps) + answer(out))

    body += section("read this", note(
        "The functions never change — not one line, in any row. Only the strings the "
        "model reads. When every row agrees, the interface has redundancy: the name and "
        "the description are two signals for the same thing and either will do. When the "
        "rows split, you have found a question where one signal was doing all the work — "
        "and the MISLEADING row is the one to watch, because its names are still perfect "
        "and it can still be wrong. You may be terse. You may not be wrong."))
    return body


def web(cli, port: int) -> None:
    serve(Panel(
        title="Tools — what it can tell apart",
        subtitle="Ask one question. It is routed through five different interfaces over "
                 "the SAME four functions — names stripped, descriptions stripped, "
                 "descriptions pointing the wrong way — and you see where they disagree.",
        intro="Type a question or tap a suggestion, then press Route it. Most questions "
              "come back with all five rows agreeing: that is redundancy, and it is the "
              "first finding. Your job is to find a question that <b>splits</b> them — "
              "then work out which signal the losing rows were relying on. Try one no "
              "tool can answer (<i>what is the weather?</i>), or one that two tools could "
              "both plausibly serve (<i>can Priya get her money back?</i>).",
        knobs=[
            Knob("question", "Your question", "combo", default="",
                 options=[q for q, _ in ROUTING_6],
                 help="Type anything, or tap one below to load it."),
            Knob("expected", "Which tool SHOULD it pick? (optional)", "select",
                 default="(let me judge)",
                 options=["(let me judge)", "search_policy", "get_customer",
                          "get_order", "check_refund_window"],
                 help="Set this and the rows get ticked or crossed for you."),
            Knob("battery", "Also score all six fixed questions", "select", default="false",
                 options=[("false", "no — just my question"),
                          ("true", "yes — the full table (30 calls)")]),
            Knob("full", "Also run the agent to a final answer", "select", default="false",
                 options=[("false", "no — first tool only"), ("true", "yes — full loop")]),
        ],
        run=run_web, button="Route it",
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
                  "one cost? Here get_customer is described as carrying 'their standing "
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
