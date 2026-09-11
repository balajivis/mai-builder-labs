# -*- coding: utf-8 -*-
"""Lab 1 — Build the Loop You Can Audit (interactive CLI tutor)

Modern AI Pro · Level 3 · AI Builder · Day 1

In Level 2 the agent loop was a mechanism inside one lab. Here it is the thing
you design. Four stages, each changing exactly one part of the picture:

    START → agent —tool_calls?→ tools → agent … → END
              ↑                    ↓
        the STOP decision    the risk gate

Run it as a guided walkthrough:   python labs/lab_1.py
Piped/non-interactive input auto-runs every stage (CI-safe).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _aurex import DENIAL, RISK, needs_human, risk_of          # noqa: E402
from _kit import Stage, banner, chat, client, meter, say, stages  # noqa: E402

# ── the tools ────────────────────────────────────────────────────────────────
# Deliberately small. Every tool widens what the system can do AND widens what
# it can do wrong, so the interesting question is never "what else could I add".

POLICIES = {
    "trading":    "Trades above $50,000 notional require desk-head approval. "
                  "Same-day settlement is not offered on any instrument.",
    "access":     "Access is granted per tool, never per project. Revocation is "
                  "immediate and does not wait for the next review cycle.",
    "disbursement": "Funds release requires two approvers when the amount exceeds "
                  "$25,000, or any amount to a first-time beneficiary.",
}

CLIENTS = {
    "C-1041": {"name": "Halvorsen Trust", "tier": "institutional", "limit": 250_000},
    "C-2288": {"name": "R. Okonjo",       "tier": "retail",        "limit": 10_000},
}


def search_policy(topic: str) -> str:
    hit = POLICIES.get(topic.strip().lower())
    return hit or f"No policy found for {topic!r}. Known topics: {', '.join(POLICIES)}"


def lookup_client(client_id: str) -> str:
    c = CLIENTS.get(client_id.strip().upper())
    return json.dumps(c) if c else f"No client {client_id!r}"


def place_trade(client_id: str, notional: float) -> str:
    return f"TRADE PLACED · {client_id} · ${notional:,.0f} · confirmation AX-88213"


TOOLS = {"search_policy": search_policy, "lookup_client": lookup_client, "place_trade": place_trade}

SCHEMA = [
    {"type": "function", "function": {"name": "search_policy",
        "description": "Look up an Aurex internal policy. Topics: trading, access, disbursement.",
        "parameters": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]}}},
    {"type": "function", "function": {"name": "lookup_client",
        "description": "Fetch a client's tier and trading limit by id, e.g. C-1041.",
        "parameters": {"type": "object", "properties": {"client_id": {"type": "string"}}, "required": ["client_id"]}}},
    {"type": "function", "function": {"name": "place_trade",
        "description": "Place a trade for a client. IRREVERSIBLE — executes against the market.",
        "parameters": {"type": "object", "properties": {
            "client_id": {"type": "string"}, "notional": {"type": "number"}}, "required": ["client_id", "notional"]}}},
]

SYSTEM = ("You are an operations agent at Aurex Financial, a regulated firm. "
          "Use the tools to establish facts before acting. Never assume a limit "
          "or a policy you have not looked up.")


def approve(name: str, args: dict) -> bool:
    """The checkpoint. Piped runs DENY — fail closed is the whole point."""
    if not sys.stdin.isatty():
        say("    [yellow]✋ non-interactive run → denied (fail closed)[/yellow]")
        return False
    ans = input(f"    ✋ allow {name}({json.dumps(args)[:70]})? [y/N] > ").strip().lower()
    return ans.startswith("y")


def run(cli, question: str, *, budget: int = 6, autonomy: str = "approve") -> None:
    """One agent loop, printed move by move so you can audit every step."""
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    for step in range(1, budget + 1):
        reply = cli.chat.completions.create(model="mai", messages=messages, tools=SCHEMA)
        msg = reply.choices[0].message
        meter.add(reply.usage, "agent")
        if not msg.tool_calls:                       # ← the STOP decision
            say(f"\n  [green]✓ stopped after {step} step(s)[/green]\n  {msg.content}")
            return
        messages.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:                  # ← EVERY call gets a reply
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            gate = risk_of(name)
            say(f"  [dim]step {step}[/dim] → [bold]{name}[/bold]({json.dumps(args)[:60]})  [dim]risk={gate}[/dim]")
            if needs_human(name, autonomy=autonomy) and not approve(name, args):
                out = DENIAL
            else:
                out = TOOLS[name](**args)
                if gate != "read":
                    say(f"    [red]● {gate} action executed[/red]")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": out})
    say(f"\n  [red]⛔ budget cap: {budget} steps — stopping honestly. A human should take over.[/red]")


# ── the stages ───────────────────────────────────────────────────────────────

def stage_read_only(cli):
    say("A question that needs two lookups and no action at all:\n")
    run(cli, "What is our trading policy, and what is client C-1041's limit?")


def stage_the_gate(cli):
    say("Now the same agent, asked to ACT. place_trade is tagged destructive:\n")
    run(cli, "Place a $40,000 trade for client C-1041.")


def stage_budget(cli):
    say("Same agent, deliberately given a budget of ONE step:\n")
    run(cli, "Compare the trading, access and disbursement policies and summarise each.", budget=1)


def stage_autonomy(cli):
    say("The same call at two rungs of the autonomy ladder.\n")
    say("[bold]suggest[/bold] — reads still inform the draft; every write stops:")
    run(cli, "Place a $40,000 trade for client C-1041.", autonomy="suggest", budget=3)
    say("\n[bold]approve[/bold] — reads run freely, the trade stops:")
    run(cli, "Place a $40,000 trade for client C-1041.", autonomy="approve", budget=3)


if __name__ == "__main__":
    banner("Level 3 · AI Builder · Day 1", "Lab 1 · Build the Loop You Can Audit")
    cli = client()
    stages(cli, [
        Stage("The loop, read-only",
              why="Three things make this an agent and not a chatbot: TOOLS it may "
                  "call, a LOOP that feeds results back, and a STOP decision. Watch "
                  "all three. The model never runs code — it emits a structured "
                  "REQUEST; your code runs it and feeds the result back. Every "
                  "tool_call id must get a reply, even a failure.",
              fn=stage_read_only,
              logic="You can draw that loop: START → agent → tools → agent → END. "
                    "Keep the picture in view — every stage from here changes "
                    "exactly one thing about it."),
        Stage("The risk gate",
              why="place_trade is tagged DESTRUCTIVE in _aurex.py — on the TOOL, "
                  "not in the prompt. That is the whole argument of Level 3: a "
                  "structural check cannot be talked out of it, and a model that "
                  "has been asked nicely is not a control.",
              fn=stage_the_gate,
              logic="Reads ran unattended; the irreversible action stopped for you. "
                    "Note what a denial returns — honest feedback the agent can "
                    "re-plan around, not a crash."),
        Stage("The budget cap",
              why="An agent that loops until it times out is worse than one that "
                  "stops early and says why. A cap is not a safety net; it is a "
                  "product decision about how much you are willing to spend before "
                  "a human looks.",
              fn=stage_budget,
              logic="It hit the cap and said so, instead of pretending it had "
                    "finished. Stopping honestly is a feature."),
        Stage("The autonomy ladder",
              why="Autonomy is not one dial for the whole system — it is per action "
                  "class, and it widens with EVIDENCE rather than at launch. "
                  "suggest → approve → notify → act.",
              fn=stage_autonomy,
              logic="Same agent, same question, two different products. Which rung "
                    "your organisation will accept on day one is the real design "
                    "constraint — and 'approve' is where every new system starts."),
    ])
