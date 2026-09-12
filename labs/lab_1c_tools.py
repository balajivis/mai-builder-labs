# -*- coding: utf-8 -*-
"""Lab 1c — TOOLS: what the agent can tell apart

Modern AI Pro · Level 3 · AI Builder · Day 1

A tool is not the function you wrote. To the model, the tool IS its description
— that string is the entire interface, and it is the only thing the model reads
when choosing. Same four functions, same code, two sets of descriptions:

    vague   "Check limits."  — the way tools get written when nobody owns them
    good    says what it is FOR and when to reach for it

Nothing else moves. Watch the routing accuracy move anyway. Most "the agent
picked the wrong tool" bugs are interface failures, not reasoning failures —
and they are fixed in the description, not in the prompt and not by swapping
the model.

    python labs/lab_1c_tools.py           guided walkthrough in the terminal
    python labs/lab_1c_tools.py --web     knobs in the browser
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _kit import Stage, banner, client, meter, say, stages           # noqa: E402
from _lab1 import (ROUTING, SCHEMA, SCHEMAS, VAGUE_SCHEMA,           # noqa: E402
                   first_tool, react)
from _web import (Knob, Panel, answer, note, port_from, section,     # noqa: E402
                  serve, step, table, wants_web)


def route_all(cli, schema) -> tuple[int, list]:
    rows, right = [], 0
    for q, want in ROUTING:
        got = first_tool(cli, q, schema)
        ok = got == want
        right += ok
        rows.append([("✓" if ok else "✗"), q, got, want])
    return right, rows


def schema_from(v: dict):
    """The edited schema, if the student changed a description; else the preset."""
    raw = (v.get("descriptions") or "").strip()
    base = SCHEMAS.get(v.get("preset") or "good", SCHEMA)
    if not raw:
        return base
    try:
        edits = json.loads(raw)
    except json.JSONDecodeError:
        return base
    out = []
    for s in base:
        s2 = json.loads(json.dumps(s))  # deep copy — never mutate the shared schema
        name = s2["function"]["name"]
        if isinstance(edits, dict) and name in edits:
            s2["function"]["description"] = str(edits[name])
        out.append(s2)
    return out


def _descriptions_json(schema) -> str:
    return json.dumps({s["function"]["name"]: s["function"]["description"]
                       for s in schema}, indent=2)


# ── web ──────────────────────────────────────────────────────────────────────

def run_web(cli, v: dict) -> str:
    schema = schema_from(v)
    right, rows = route_all(cli, schema)
    body = section(
        f"routing · {right}/{len(ROUTING)} correct",
        table(["", "question", "it picked", "should be"],
              [[m, q, got, want] for m, q, got, want in rows]))

    if v.get("compare") in (True, "true", "on"):
        vr, _ = route_all(cli, VAGUE_SCHEMA)
        gr, _ = route_all(cli, SCHEMA)
        body += section("vague vs written as an interface", table(
            ["descriptions", "routed correctly"],
            [["vague", f"{vr}/{len(ROUTING)}"], ["interface", f"{gr}/{len(ROUTING)}"]]))

    if v.get("task"):
        steps: list[str] = []
        out = react(cli, v["task"], profile=v.get("profile") or
                    "You are an operations agent at Aurex Financial. Use tools to "
                    "establish facts before answering.",
                    schema=schema, budget=6,
                    on_step=lambda k, lab, det: steps.append(step(lab, det, k)))
        body += section("a full run on these descriptions", "".join(steps) + answer(out))

    body += section("read this", note(
        "The code behind these four tools never changed — not one line. Only the "
        "strings the model reads. If two descriptions could both plausibly answer a "
        "question, the model is guessing, and you wrote the coin it flips."))
    return body


def web(cli, port: int) -> None:
    serve(Panel(
        title="Tools — what it can tell apart",
        subtitle="Four functions, two sets of descriptions. The code is identical. "
                 "Only the strings the model reads are different.",
        intro="Run <b>vague</b> first and count the misroutes. Switch to <b>good</b> and "
              "run again. Then edit the JSON directly — try making two descriptions "
              "overlap on purpose (give <code>check_limits</code> and "
              "<code>lookup_client</code> both the word 'limit') and watch the routing "
              "collapse. That is the most common real-world tool bug, reproduced on demand.",
        knobs=[
            Knob("preset", "Description set", "select", default="good",
                 options=[("good", "good — written as an interface"),
                          ("vague", "vague — the way they usually get written")]),
            Knob("descriptions", "Edit the descriptions (JSON — blank uses the preset)",
                 "textarea", default="",
                 help="Paste {\"tool_name\": \"new description\"} to override any of them."),
            Knob("task", "Optional: run a full task on these tools", "text", default=""),
            Knob("compare", "Also score the other set", "select", default="false",
                 options=[("false", "no"), ("true", "yes — score both")]),
        ],
        run=run_web, button="Score the routing",
    ), cli, port=port)


# ── cli ──────────────────────────────────────────────────────────────────────

def stage_routing(cli):
    say("Identical tools, identical code, identical profile. Only the DESCRIPTIONS "
        "differ.\n")
    for label, schema in (("vague", VAGUE_SCHEMA), ("written as an interface", SCHEMA)):
        say(f"[bold yellow]── {label} ──[/bold yellow]")
        right, rows = route_all(cli, schema)
        for mark, q, got, want in rows:
            colour = "green" if mark == "✓" else "red"
            say(f"  [{colour}]{mark}[/{colour}] {q[:50]:<52} → [bold]{got}[/bold]"
                + ("" if mark == "✓" else f" [dim](wanted {want})[/dim]"))
        say(f"  [bold]{right}/{len(ROUTING)} routed correctly[/bold]\n")


def stage_overlap(cli):
    say("Now the bug you will actually ship: two tools whose descriptions overlap.\n")
    collide = json.loads(json.dumps(SCHEMA))
    for s in collide:
        if s["function"]["name"] in ("check_limits", "lookup_client"):
            s["function"]["description"] = "Look up a client's limit."
    right, rows = route_all(cli, collide)
    for mark, q, got, want in rows:
        colour = "green" if mark == "✓" else "red"
        say(f"  [{colour}]{mark}[/{colour}] {q[:50]:<52} → [bold]{got}[/bold]"
            + ("" if mark == "✓" else f" [dim](wanted {want})[/dim]"))
    say(f"  [bold]{right}/{len(ROUTING)} routed correctly[/bold]\n")


if __name__ == "__main__":
    cli = client()
    if wants_web():
        web(cli, port_from(default=7862))
        sys.exit(0)
    banner("Level 3 · AI Builder · Day 1", "Lab 1c · Tools — what it can tell apart")
    say("[dim]Tip: --web lets you edit the descriptions live.[/dim]\n")
    stages(cli, [
        Stage("The description IS the interface",
              why="To the model, a tool is its name, its description and its parameter "
                  "schema. That is all it gets. Here are the same four functions twice: "
                  "once described the way tools get written when nobody owns them, once "
                  "written as an interface that says what each is FOR.",
              fn=stage_routing,
              logic="The code never changed. The routing did. Most 'the agent picked the "
                    "wrong tool' bugs are not reasoning failures — they are interface "
                    "failures, fixed in the description, not in the prompt and not by "
                    "swapping the model."),
        Stage("Overlap is the same bug",
              why="Two tools that could both plausibly answer the same question is the "
                  "most common tool bug in production, and it never looks like a bug — "
                  "it looks like the model being unreliable.",
              fn=stage_overlap,
              logic="Give two tools the same description and the model has no basis to "
                    "choose; it picks one, and it will not always pick the same one. "
                    "Before you conclude the model is unreliable, read your tool list as "
                    "if you were the one being asked to choose from it."),
    ])
    meter.show()
