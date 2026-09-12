# -*- coding: utf-8 -*-
"""Lab 1c — MEMORY: what the agent carries between turns

Modern AI Pro · Level 3 · AI Builder · Day 1

Turn 3 asks what "she" paid. Nothing in that sentence names a customer or an
order. Whether the agent can answer it is not a model capability — it
is a policy you chose, and each policy pays a different bill:

    none     cheap, and turn 3 is unanswerable
    window   accurate, and grows without limit
    facts    cheap and durable, and lossy in exactly the way you wrote

There is no right answer on this slider. There is only which bill you meant to pay.

    python labs/lab_1c_memory.py           guided walkthrough in the terminal
    python labs/lab_1c_memory.py --web     knobs in the browser
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _kit import Stage, banner, chat, client, meter, say, stages     # noqa: E402
from _lab1 import PROFILES, Probe, react                             # noqa: E402
from _web import (Knob, Panel, answer, note, port_from, section,     # noqa: E402
                  serve, step, table, wants_web)

# Turn 3 must be UNANSWERABLE without turn 1 — otherwise a stateless agent
# answers it from the question alone and the whole comparison scores a pass.
# (A first draft named the order outright in turn 3 — the stateless agent then
#  answered it correctly from the question alone and the lesson evaporated.)
TURNS = [
    "I'm looking at Priya's complaint — priya@example.com.",
    "What did she order?",
    "Is she still inside the refund window for it?",
]

POLICIES_HELP = {
    "none": "Send only the current turn. Every turn is turn one.",
    "window": "Send the entire transcript, every time.",
    "last2": "Send only the last two exchanges — a sliding window.",
    "facts": "Send a small extracted state (ids seen so far), not the transcript.",
    "summary": "Ask the model to compress the transcript, then send the summary.",
}


def carry_for(policy: str, cli):
    """Return carry(history) -> messages. That function IS the memory policy."""
    state: dict = {}

    def facts(h):
        for m in h:
            for cid in re.findall(r"[A-Z]-\d{4}|[\w.+-]+@[\w-]+\.[\w.]+",
                                  m.get("content") or ""):
                state.setdefault("seen", [])
                if cid not in state["seen"]:
                    state["seen"].append(cid)
        note_ = f"Known so far: {json.dumps(state)}" if state else "Known so far: nothing."
        return [{"role": "system", "content": note_}, h[-1]]

    def summary(h):
        if len(h) <= 1:
            return h[-1:]
        prior = "\n".join(f"{m['role']}: {m['content']}" for m in h[:-1])
        s = chat(cli, [{"role": "user", "content":
                        "Compress this conversation to the facts a colleague would need "
                        "to answer the next question. Two sentences maximum.\n\n" + prior}],
                 label="summarise")
        return [{"role": "system", "content": f"Conversation so far: {s}"}, h[-1]]

    return {
        "none": lambda h: h[-1:],
        "window": lambda h: list(h),
        "last2": lambda h: h[-4:],
        "facts": facts,
        "summary": summary,
    }.get(policy, lambda h: list(h))


def converse(cli, policy: str, on_turn) -> dict:
    """Run the three turns under one memory policy. on_turn(user, reply, steps)."""
    carry = carry_for(policy, cli)
    history: list[dict] = []
    p = Probe()
    for t in TURNS:
        history.append({"role": "user", "content": t})
        prior = carry(history)
        steps: list = []
        out = react(cli, prior[-1]["content"], profile=PROFILES["support"],
                    history=prior[:-1], budget=4,
                    on_step=lambda k, lab, det: steps.append((k, lab, det)))
        history.append({"role": "assistant", "content": out})
        on_turn(t, out, steps)
    r = p.done("")
    return {"calls": r["calls"], "tokens": r["tokens"], "secs": r["secs"],
            "last": history[-1]["content"] if history else ""}


def resolved(last: str) -> bool:
    """Turn 3 is answered only if the agent still knows who 'they' are.

    Scored on the ORDER's own numbers, not on a yes/no — a stateless agent can emit
    a confident answer about nobody in particular, and that must not count as a
    pass. 41 days against the 30-day window is the answer, and reaching either
    number requires knowing from turn 1 that we are talking about order A-4417.
    """
    t = (last or "").lower()
    return ("41" in t) or ("a-4417" in t) or ("30" in t and "day" in t)


# ── web ──────────────────────────────────────────────────────────────────────

def run_web(cli, v: dict) -> str:
    policy = v.get("policy") or "window"
    body = ""
    rows: list = []

    def render(u, reply, steps):
        nonlocal body
        body += step("you", u, "warn")
        for k, lab, det in steps:
            body += step(lab, det, k)
        body += answer(reply or "(no answer)")

    r = converse(cli, policy, render)
    rows.append([policy, r["calls"], r["tokens"], f"{r['secs']}s",
                 "yes" if resolved(r["last"]) else "NO"])

    if v.get("compare") in (True, "true", "on"):
        for other in ("none", "window", "facts"):
            if other == policy:
                continue
            r2 = converse(cli, other, lambda *a: None)
            rows.append([other, r2["calls"], r2["tokens"], f"{r2['secs']}s",
                         "yes" if resolved(r2["last"]) else "NO"])

    out = section(f"the conversation · policy = {policy}", body)
    out += section("the bill", table(
        ["policy", "LLM calls", "tokens", "secs", "turn 3 answered"], rows, highlight=0))
    out += section("read this", note(
        "Cost and capability move together. 'none' is cheapest and cannot answer turn 3 "
        "at all. 'window' answers it and re-sends everything to do so. 'facts' answers it "
        "for almost nothing — but only carries what the extractor was written to notice. "
        "That last clause is every memory system you will ever build."))
    return out


def web(cli, port: int) -> None:
    serve(Panel(
        title="Memory — what it carries between turns",
        subtitle="Three turns. The third says 'she' and 'it' and names neither the "
                 "customer nor the order. Which memory policy you chose decides "
                 "whether that sentence means anything at all.",
        intro="Run it on <b>window</b> first and read turn 3. Then switch to <b>none</b> "
              "and watch the same question become unanswerable. Then <b>facts</b> — it "
              "answers again, for a fraction of the tokens. Tick <i>compare all</i> to "
              "get the bill side by side.",
        knobs=[
            Knob("policy", "Memory policy", "select", default="window",
                 options=[(k, f"{k} — {d}") for k, d in POLICIES_HELP.items()],
                 help="The carry() function. This is the knob."),
            Knob("compare", "Also run none / window / facts for the table", "select",
                 default="false", options=[("false", "no — just this one"),
                                           ("true", "yes — compare (slower)")]),
        ],
        run=run_web, button="Run the conversation",
    ), cli, port=port)


# ── cli ──────────────────────────────────────────────────────────────────────

def stage_policies(cli):
    rows = []
    for policy in ("none", "window", "facts"):
        say(f"[bold yellow]── {policy}: {POLICIES_HELP[policy]} ──[/bold yellow]")

        def show(u, reply, steps):
            say(f"  [bold]you[/bold]   {u}")
            say(f"  [cyan]agent[/cyan] {(reply or '(no answer)')[:210]}\n")

        r = converse(cli, policy, show)
        rows.append((policy, r))
        say(f"  [dim]{r['calls']} calls · {r['tokens']} tok · {r['secs']}s · "
            f"turn 3 {'answered' if resolved(r['last']) else 'NOT answered'}[/dim]\n")

    say("[bold]  policy      calls   tokens   turn 3[/bold]")
    for policy, r in rows:
        say(f"  {policy:<10} {r['calls']:>5}   {r['tokens']:>6}   "
            f"{'yes' if resolved(r['last']) else 'NO'}")


if __name__ == "__main__":
    cli = client()
    if wants_web():
        web(cli, port_from(default=7862))
        sys.exit(0)
    banner("Level 3 · AI Builder · Day 1", "Lab 1c · Memory — what it carries")
    say("[dim]Tip: --web gives you the same thing with a policy dropdown.[/dim]\n")
    stages(cli, [
        Stage("Three policies, one conversation",
              why="Memory is not a feature you switch on. It is a carry() function: "
                  "given everything that has happened, what do you actually send? "
                  "Turn 3 says 'she' and 'it' and names nobody and nothing — so it "
                  "is a direct test of what actually survived.",
              fn=stage_policies,
              logic="Stateless could not resolve 'they' and had to guess or ask. The "
                    "window resolved it and re-sent the whole transcript to do it — "
                    "fine at three turns, ruinous at three hundred. The facts policy "
                    "won on cost and only carried what its extractor was written to "
                    "notice. What you chose to keep is what the agent can still reason "
                    "about; everything else is gone and it will not tell you."),
    ])
    meter.show()
