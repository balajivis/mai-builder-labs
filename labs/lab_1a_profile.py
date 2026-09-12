# -*- coding: utf-8 -*-
"""Lab 1a — PROFILE: who the agent is

Modern AI Pro · Level 3 · AI Builder · Day 1

The profile is the cheapest design surface you have. No code, no schema, no
deploy — one paragraph. It is also the surface most often written once and
never looked at again, which is why it is the first thing to play with.

Watch what it does and does NOT change. Measured on the class model 2026-09-12,
every profile — including "You are a helpful assistant" — reached for the same
two tools. Modern models use the tools you give them whether or not you told
them to, so the popular claim that a bare profile "answers from nothing" is just
not true, and this lab will not pretend otherwise.

What moved was the VERDICT, on identical facts:

    blank        "Yes — $180,000 is within C-1041's $250,000 trading limit."
    compliance   "It cannot proceed without desk-head approval."

Same tools, same lookups, same numbers, opposite headline. The profile is not
deciding what the agent knows. It is deciding what the agent thinks the question
was — and which of the true things it found is the one worth leading with.

    python labs/lab_1a_profile.py           guided walkthrough in the terminal
    python labs/lab_1a_profile.py --web     knobs in the browser  ← start here
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _kit import Stage, banner, client, meter, say, stages           # noqa: E402
from _lab1 import PROFILES, react                                    # noqa: E402
from _web import (Knob, Panel, answer, note, port_from, presets,     # noqa: E402
                  section, serve, step, wants_web)

QUESTION = "Can client C-1041 trade $180,000 today?"

# ── web ──────────────────────────────────────────────────────────────────────


def run_web(cli, v: dict) -> str:
    profile = (v.get("profile") or "").strip() or PROFILES["blank"]
    question = (v.get("question") or "").strip() or QUESTION
    budget = int(v.get("budget") or 5)

    steps: list[str] = []
    out = react(cli, question, profile=profile, budget=budget,
                on_step=lambda kind, label, detail: steps.append(step(label, detail, kind)))

    first = "—"
    for s in steps:
        if 'class="step "' in s or 'class="step"' in s:
            first = s.split('<span class="l">')[1].split("(")[0]
            break

    body = section("what it did", "".join(steps) or note("no tool calls at all"))
    body += section("what it said", answer(out or "(nothing — it ran out of budget)"))
    body += section("read this", note(
        f"It reached for {first} first, used {len(steps)} move(s), and answered in "
        f"{len(out.split())} words. Now run a different profile on the same question and "
        "compare the FIRST SENTENCE of each. The tool calls will probably be identical — "
        "what changes is which true fact the agent decided you were asking about. To the "
        "person reading it, that choice is the answer."))
    return body


def web(cli, port: int) -> None:
    serve(Panel(
        title="Profile — who the agent is",
        subtitle="One paragraph, four read-only tools, one question. Change only the "
                 "paragraph and watch which tool it reaches for first, whether it "
                 "checks policy at all, and what it thinks a good answer looks like.",
        intro="Hit <b>Run</b> with the profile as it stands, then load a preset and run "
              "again. After that, write your own. Things worth trying: make it refuse "
              "to answer without a second approver · make it answer in exactly one word "
              "· give it a risk appetite · tell it the client is its biggest account · "
              "remove the instruction to look things up and see what it invents.",
        knobs=[
            Knob("profile", "The profile (system prompt)", "textarea",
                 default=PROFILES["operations"],
                 help="The entire standing instruction. This is the knob."),
            Knob("question", "The question", "text", default=QUESTION),
            Knob("budget", "Step budget", "slider", default=5, min=1, max=8,
                 help="How many think→act rounds before it must stop."),
        ],
        run=run_web, button="Run the agent",
    ), cli, port=port, presets_html=presets("profile", [
        (k, v) for k, v in PROFILES.items()
    ]))


# ── cli ──────────────────────────────────────────────────────────────────────


def _run(cli, profile: str, label: str) -> None:
    say(f"[bold yellow]── {label} ──[/bold yellow]")
    say(f"[dim]{profile[:98]}{'…' if len(profile) > 98 else ''}[/dim]")
    out = react(cli, QUESTION, profile=profile, budget=5,
                on_step=lambda kind, lab, det: say(
                    f"  [{'green' if kind == 'good' else 'red' if kind == 'bad' else 'dim'}]"
                    f"{'✓' if kind == 'good' else '⛔' if kind == 'bad' else '→'}[/] {lab}"))
    say(f"  {out}\n" if out else "")


def stage_compare(cli):
    say("Same question. Same four tools. Same model. Only the profile changes.\n")
    for name in ("blank", "operations", "compliance"):
        _run(cli, PROFILES[name], name)


def stage_yours(cli):
    if not sys.stdin.isatty():
        say("[dim](piped run — skipping the write-your-own prompt)[/dim]")
        return
    say("Write a profile and watch the same question land differently.")
    say("[dim]Try: refuse without a second approver · answer in one word · "
        "give it a risk appetite.[/dim]")
    own = input("  profile > ").strip()
    if own:
        say()
        _run(cli, own, "yours")


if __name__ == "__main__":
    cli = client()
    if wants_web():
        web(cli, port_from(default=7860))
        sys.exit(0)
    banner("Level 3 · AI Builder · Day 1", "Lab 1a · Profile — who the agent is")
    say("[dim]Tip: python labs/lab_1a_profile.py --web  gives you the same thing "
        "with knobs.[/dim]\n")
    stages(cli, [
        Stage("Three colleagues, one question",
              why="The profile is the cheapest design surface you have: no code, no "
                  "schema, no deploy. It is also the one most often written once and "
                  "never read again. Watch it change not just TONE but which tool the "
                  "agent reaches for and whether it is willing to answer at all.",
              fn=stage_compare,
              logic="Look at what did NOT move: every profile used the tools. A bare "
                    "'helpful assistant' still looked up the policy and the limit — so "
                    "the usual claim that a weak profile makes an agent hallucinate its "
                    "facts is not what happens here. What moved is the VERDICT on "
                    "identical facts: blank leads with 'yes, within limit', compliance "
                    "leads with 'cannot proceed without approval'. Both are true. The "
                    "profile is not deciding what the agent knows; it is deciding which "
                    "true thing it leads with — which, to the person reading the answer, "
                    "IS the answer. Before you add a tool or reach for a graph, ask "
                    "whether the profile you wrote is the one you meant."),
        Stage("Now write one",
              why="A profile is a product decision wearing a paragraph. Who does this "
                  "agent work for? What is it allowed to assume? What does it do when "
                  "it is not sure — guess, ask, or refuse? You are answering those "
                  "whether you write them down or not.",
              fn=stage_yours,
              logic="Whatever you wrote, the agent took literally — including the parts "
                    "you left out. That is the whole discipline: the profile is not "
                    "flavour text, it is the specification the model actually reads."),
    ])
    meter.show()
