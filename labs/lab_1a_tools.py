# -*- coding: utf-8 -*-
"""Lab 1a — TOOLS: what your agent can actually answer

Modern AI Pro · Level 3 · AI Builder · Day 1

One question, and one knob: WHICH TOOLS the agent is allowed to use.

    Priya is asking for a refund on order A-4417. She says it arrived damaged.
    Can we refund her?

Take away `search_policy` and the agent cannot see the rule that decides the
case: damaged goods are covered for 90 days, which overrides the standard
30-day window. It still has a refund-window checker, and that checker says 41
days — outside. Accurate, and not the answer to the question asked.

Here is what actually happens then. Measured 2026-09-12, three runs per cell:

                        WITHOUT search_policy        WITH it
    refunds reviewer    denies her refund 2 of 3     never denies · 3-4 of 4 facts
                        runs · 1-2 of 4 facts
    support agent       never denies, but cannot     never denies · 2-4 of 4
                        close · 1-2 of 4 facts
    retention           never denies, always 3 of    never denies · 4 of 4
                        4 — and none of them read
                        the rule it is relying on

Read the ceiling first. WITHOUT the policy tool, no profile gets above 3 of 4,
because the fact that decides the case is not reachable from any of them. WITH
it, every profile lands 3-4 and nobody denies her.

    The toolbox sets the ceiling.
    The profile decides how you fail underneath it.

And the failures look nothing alike. The strict profile denies a customer money
she is owed — the only one that looks like a bug in a transcript. The careful
one will not commit and hands her to a human, which reads as prudence and
quietly costs you your deflection rate. The eager one scores highest of the
three while citing a 90-day rule it never read, which is the most dangerous of
the three precisely because it looks like success.

Then tick `search_policy` and run again. Same model, same question, same three
profiles, and all three converge — the rule cited and the $148.50 flagged for
supervisor approval. Nothing was re-prompted.

    When your agent is wrong, look at what you GAVE it
    before you look at how you asked.

That is the lab. Four beats:

    1  the model never runs your code — it emits a request, your code executes it
    2  the trap        — one missing tool, three different failures
    3  the fix         — the fix is a tool, not a prompt
    4  what IS a tool  — to the model: a name, a description, some parameters

    python labs/lab_1a_tools.py           guided walkthrough in the terminal
    python labs/lab_1a_tools.py --web     tick the tools yourself  ← start here
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _kit import Stage, banner, client, meter, say, stages           # noqa: E402
from _lab1 import (ANON_NAMES, MISLEADING, PROFILES, ROUTING_6,      # noqa: E402
                   SCHEMA, TOOLS, build_schema, call_tool,
                   first_tool, real_name, score)
from _web import (Knob, Panel, answer, note, port_from, presets,     # noqa: E402
                  request, section, serve, step, table, verdict,
                  wants_web)

QUESTION = ("Priya (priya@example.com) is asking for a refund on order A-4417. "
            "She says it arrived damaged. Can we refund her, and why?")

ALL_TOOLS = ["search_policy", "get_customer", "get_order", "check_refund_window"]

# The two configurations the whole lab turns on. get_order stays in the trap: its
# `customer_reported` note is what lets each profile react differently rather than
# all three stalling identically, and that divergence IS the finding.
TRAP = "check_refund_window,get_order"
FIXED = "check_refund_window,get_order,search_policy"

TOOL_BLURB = {
    "search_policy": "search_policy — the rules (refunds, damaged, returns, membership)",
    "get_customer": "get_customer — who the customer is, by email",
    "get_order": "get_order — one order: item, amount, delivery date, condition",
    "check_refund_window": "check_refund_window — is this order inside the STANDARD 30 days?",
}


def subset(names: list[str]) -> list[dict]:
    """The schema, narrowed to the ticked tools. This is the knob."""
    return [t for t in SCHEMA if t["function"]["name"] in names]


DENIALS = ("cannot approve", "can not approve", "cannot issue", "cannot be refunded",
           "not eligible", "unable to approve", "we must decline", "refund is denied",
           "do not approve", "cannot offer a refund", "not entitled")


def refuses(text: str) -> bool:
    """Did the agent tell the customer no?

    Reads the OPENING of the answer, because a support reply that opens with a
    refusal is a refusal whatever it qualifies later. The first version only
    caught a literal leading "no" and so scored "We cannot approve the requested
    refund under the standard policy" as an approval — labelling a denial as a
    correct answer on the student's screen, which is worse than not labelling it.
    """
    head = (text or "").strip().lower()[:220]
    return head.startswith("no") or any(d in head for d in DENIALS)


def run_agent(cli, question: str, names: list[str], profile: str, on_step, budget: int = 6) -> str:
    """ReAct, but reporting the RAW request as well as the result — beat 1 is a
    thing students have to see, not be told."""
    schema = subset(names)
    messages = [{"role": "system", "content": profile}, {"role": "user", "content": question}]
    for n in range(1, budget + 1):
        reply = cli.chat.completions.create(model="mai", messages=messages, tools=schema)
        msg = reply.choices[0].message
        meter.add(reply.usage, "agent")
        if not msg.tool_calls:
            on_step("answer", msg.content or "", "")
            return msg.content or ""
        messages.append(msg.model_dump(exclude_none=True))
        for c in msg.tool_calls:
            raw = c.function.arguments or "{}"
            out = call_tool(c.function.name, json.loads(raw))
            on_step("call", c.function.name, raw)
            on_step("result", out, "")
            messages.append({"role": "tool", "tool_call_id": c.id, "content": out})
    on_step("cap", f"hit the {budget}-step budget", "")
    return ""


def outcome(text: str, hits: int) -> tuple[str, str]:
    """Name the failure in the words a support manager would use."""
    if refuses(text):
        return "DENIED the refund", "bad"
    t = (text or "").lower()
    if any(p in t for p in ("can't confirm", "cannot confirm", "unable to confirm",
                            "need to", "escalat", "review", "further")) and hits < 3:
        return "could not close — escalates", "warn"
    if hits >= 3:
        return "approved, and can justify it", "good"
    return f"approved on only {hits}/4 facts", "warn"


def sweep_profiles(cli, names: list[str], question: str) -> list[list]:
    """The same toolbox through all three profiles. The divergence IS the finding."""
    rows = []
    for key in ("policy", "support", "retention"):
        out = run_agent(cli, question, names, PROFILES[key], lambda *a: None)
        hits, _ = score(out)
        label, _kind = outcome(out, hits)
        rows.append([key, label, f"{hits}/4", (out or "")[:150]])
    return rows


# ── web ──────────────────────────────────────────────────────────────────────

def run_web(cli, v: dict) -> str:
    names = [n for n in (v.get("tools") or "").split(",") if n in TOOLS]
    if not names:
        return section("give it a tool", note(
            "Tick at least one tool on the left. Start with the two the preset calls "
            "“the trap” and read what it tells the customer."))
    question = (v.get("question") or "").strip() or QUESTION
    profile = PROFILES.get(v.get("profile") or "support", PROFILES["support"])

    trace, first_req = [], []

    def on_step(kind, a, b):
        if kind == "call":
            if not first_req:
                first_req.append(request(a, b))
            trace.append(step(f"{a}({b[:60]})", "", ""))
        elif kind == "result":
            trace.append(step("→", a[:140], "warn"))
        elif kind == "cap":
            trace.append(step(a, b, "bad"))

    out = run_agent(cli, question, names, profile, on_step)
    said_no = refuses(out)
    hits, missed = score(out)
    has_policy = "search_policy" in names

    # The banner. Plain language, because the point is that anyone can judge this.
    if said_no:
        head = verdict("This answer is WRONG — and it just denied a real customer.",
                       "The agent was told the order is 41 days old, outside the standard "
                       "30-day window, and stopped there. Priya's item arrived damaged, and "
                       "damaged goods are covered for 90 days. It never had a tool that "
                       "could tell it that.", ok=False)
    elif hits >= 3:
        head = verdict("Correct — and it explains itself.",
                       f"It found {hits} of 4 facts, including the 90-day damaged-goods "
                       "rule that overrides the standard window. Same model, same question, "
                       "same profile as the wrong answer above. Only the toolbox changed.",
                       ok=True)
    else:
        head = verdict("It said yes, but it cannot fully justify it.",
                       f"Only {hits} of the 4 facts. Read the trace and ask which tool it "
                       "was missing.", ok=False)

    body = head
    if first_req:
        body += section("what the model actually did", first_req[0] + note(
            "The model never ran anything. It emitted a name and some JSON; your Python "
            "executed the function and handed the result back. Everything an agent does "
            "is that, in a loop."))
    body += section(f"the run · {len(names)} tool(s)", "".join(trace))
    body += section("what it told the customer", answer(out or "(no answer — hit the cap)"))

    rows = [[k, "✓" if not m else "—"] for k, m in
            ((k, k in missed) for k in
             ["the $148.50 amount", "41 days — outside the standard 30-day window",
              "damaged goods are covered to 90 days",
              "over $100, so a supervisor must approve"])]
    body += section(f"the four facts a good answer needs · {hits}/4",
                    table(["fact", "found"], rows))

    if v.get("sweep") in (True, "true", "on"):
        rows = sweep_profiles(cli, names, question)
        body += section(
            ("all three profiles, WITHOUT search_policy" if not has_policy
             else "all three profiles, WITH search_policy"),
            table(["profile", "what it did", "facts", "what it said"],
                  [[r[0], r[1], r[2], r[3]] for r in rows]))
        body += note(
            "One missing tool, three different failures — the strict profile denies a "
            "customer her money, the careful one gives up and costs you a human, the "
            "eager one is right for a reason it could not have known. Only the first "
            "looks like a bug in a transcript. Tick search_policy and run this again: "
            "all three converge."
            if not has_policy else
            "With the rule reachable, all three profiles agree. The profile decided the "
            "TONE; the toolbox decided whether an answer was possible at all.",
            "warn" if not has_policy else "good")

    body += section("read this", note(
        "check_refund_window did not malfunction. It answered the STANDARD window "
        "exactly as designed, and that answer is true. The failure is that its name "
        "sounds like it settles the refund question when it only settles part of it — "
        "so an agent trusting it stops one tool too early. "
        + ("You gave it search_policy, so it could find the exception. "
           if has_policy else
           "Tick search_policy and run it again: the answer flips, and you will not have "
           "touched the prompt. ")
        + "When your agent is wrong, look at what you GAVE it before you look at how "
          "you asked."))
    return body


def web(cli, port: int) -> None:
    serve(Panel(
        title="Tools — what your agent can actually answer",
        subtitle="One customer, one question, one knob: which tools the agent is allowed "
                 "to use. Watch a correct-looking agent deny a refund it should have "
                 "approved — then fix it without touching the prompt.",
        intro="Press <b>Run</b> as it stands. The agent has the order and the refund-window "
              "checker but NOT the rules, so it cannot see that damaged goods are covered "
              "for 90 days. Read the three-profile table: the strict profile <b>denies "
              "Priya her money</b>, the careful one gives up and escalates, the eager one "
              "says yes for a reason it cannot support. Same missing tool, three different "
              "failures. Then tick <code>search_policy</code> and run again — all three "
              "converge on the right answer, and you will not have touched the prompt.",
        knobs=[
            Knob("tools", "Tools the agent may use", "checks", default=TRAP,
                 options=[(n, TOOL_BLURB[n]) for n in ALL_TOOLS],
                 help="This is the knob. Everything else stays fixed."),
            Knob("question", "The customer's case", "combo", default=QUESTION,
                 options=[QUESTION,
                          "Tom (tom@example.com) wants to return order A-5120. Can he?",
                          "Can Priya get free return postage?"]),
            Knob("profile", "Profile", "select", default="policy",
                 options=[("policy", "refunds reviewer — strict"),
                          ("support", "support agent — careful"),
                          ("retention", "retention specialist — eager")]),
            Knob("sweep", "Also run all three profiles side by side", "select",
                 default="true",
                 options=[("true", "yes — this is the lesson"), ("false", "no — just one")],
                 help="Same toolbox, three profiles. Watch one missing tool produce "
                      "three different failures."),
        ],
        run=run_web, button="Run the agent",
    ), cli, port=port, presets_html=presets("tools", [
        ("the trap — 2 tools", TRAP),
        ("the fix — add search_policy", FIXED),
        ("everything", ",".join(ALL_TOOLS)),
    ]))


# ── cli ──────────────────────────────────────────────────────────────────────

def _run(cli, names, label):
    say(f"[bold yellow]── {label} — tools: {', '.join(names)} ──[/bold yellow]")

    def on_step(kind, a, b):
        if kind == "call":
            say(f'  [dim]the model emitted:[/dim] {{"name": "{a}", "arguments": {b[:60]}}}')
        elif kind == "result":
            say(f"  [dim]  → your code returned:[/dim] {a[:110]}")
        elif kind == "cap":
            say(f"  [red]{a}[/red]")

    out = run_agent(cli, QUESTION, names, PROFILES["support"], on_step)
    hits, _ = score(out)
    colour = "red" if refuses(out) else "green"
    say(f"\n  [{colour}]{out}[/{colour}]")
    say(f"  [dim]{hits}/4 of the facts a good answer needs[/dim]\n")
    return out


def stage_trap(cli):
    say("The agent can read the order and check the standard refund window — but it "
        "does NOT have the rules.\nWatch the raw requests go past: the model never runs "
        "anything itself.\n")
    _run(cli, TRAP.split(","), "the trap · support agent")
    say("Now the SAME toolbox through all three profiles:\n")
    for key, what, hits, said in sweep_profiles(cli, TRAP.split(","), QUESTION):
        colour = {"DENIED the refund": "red"}.get(what, "yellow")
        say(f"  [bold]{key:<10}[/bold] [{colour}]{what:<30}[/{colour}] {hits}")
        say(f"             [dim]{said[:120]}[/dim]")


def stage_fix(cli):
    say("Exactly the same model, question and profiles. One more tool.\n")
    _run(cli, FIXED.split(","), "the fix · support agent")
    say("And all three profiles again, with search_policy in the box:\n")
    for key, what, hits, said in sweep_profiles(cli, FIXED.split(","), QUESTION):
        say(f"  [bold]{key:<10}[/bold] [green]{what:<30}[/green] {hits}")


def stage_what_is_a_tool(cli):
    say("To the model, a tool is three strings: a name, a description, parameters.\n"
        "Strip each and see which was carrying the routing.\n")
    for label, kw, anon in (("names + descriptions", {}, False),
                            ("names only", {"describe": False}, False),
                            ("descriptions only (tool_a…)", {"anonymise": True}, True),
                            ("neither", {"anonymise": True, "describe": False}, True),
                            ("names + MISLEADING descriptions", {"overrides": MISLEADING}, False)):
        sch = build_schema(**kw)
        r = sum(real_name(first_tool(cli, q, sch)) == want for q, want in ROUTING_6)
        say(f"  {label:<34} {r}/{len(ROUTING_6)}")


if __name__ == "__main__":
    cli = client()
    if wants_web():
        web(cli, port_from(default=7860))
        sys.exit(0)
    banner("Level 3 · AI Builder · Day 1", "Lab 1a · Tools — what your agent can answer")
    say("[dim]Tip: --web lets you tick the tools yourself and watch the answer flip.[/dim]\n")
    stages(cli, [
        Stage("The trap — one missing tool, three different failures",
              why="Priya wants a refund on a damaged espresso machine. The agent has the "
                  "order and a refund-window checker, which sounds like everything it "
                  "needs — but not the rules, so the 90-day damaged-goods cover is "
                  "invisible to it. Watch the raw tool requests first: the model never "
                  "runs your code, it emits a name and some JSON and your Python does "
                  "the rest. Then read what each profile does with the same gap.",
              fn=stage_trap,
              logic="Nothing malfunctioned. check_refund_window reported the standard "
                    "30-day window exactly as designed, and 41 days really is outside "
                    "it — it simply is not the question that decides this case. What is "
                    "worth your attention is that the SAME gap produced three different "
                    "failures: the strict profile denied a customer money she was owed, "
                    "the careful one could not close and escalated to a human, and the "
                    "eager one said yes for a reason it had no way to check. Only the "
                    "first looks like a bug when you read the transcript. The second "
                    "looks like caution and quietly costs you your deflection rate. The "
                    "third looks like success."),
        Stage("The fix is a tool, not a prompt",
              why="Same model. Same question. Same three profiles. Same wording, down "
                  "to the character. The only change is that search_policy is now in "
                  "the toolbox, so the 90-day damaged-goods rule is reachable.",
              fn=stage_fix,
              logic="All three converged on a correct yes, cited the rule that overrides "
                    "the window, and flagged the $148.50 for supervisor approval — with "
                    "no prompt engineering whatsoever. Note what that means about the two "
                    "surfaces: the PROFILE decided the tone and the risk appetite, but "
                    "the TOOLBOX decided whether a correct answer was reachable at all. "
                    "No profile can talk its way to a rule it cannot read. This is the "
                    "habit to build: when "
                    "your agent is wrong, look at what you GAVE it before you look at "
                    "how you asked. Most 'the model is not smart enough' bugs are a "
                    "missing tool, or a tool that answers a narrower question than its "
                    "name implies."),
        Stage("So what IS a tool, to the model?",
              why="Three strings: a name, a description, and a parameter schema. That is "
                  "the entire interface — not your docstring, not your implementation. "
                  "Which of them is actually doing the routing? Remove each and score "
                  "what is left.",
              fn=stage_what_is_a_tool,
              logic="The name and the description are largely REDUNDANT — either alone "
                    "routes nearly everything, and only losing both really costs you. "
                    "But the misleading row keeps every perfect name and still drops, "
                    "which is the one to remember: absence is survivable, misdirection "
                    "is not. You may be terse; you may not be wrong. And none of this "
                    "would have saved the agent in stage 1 — no wording of "
                    "check_refund_window makes it know about the 90-day rule."),
    ])
    meter.show()
