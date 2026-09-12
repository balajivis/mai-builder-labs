# -*- coding: utf-8 -*-
"""The world Lab 1 is played in — shared by all four files.

Aurex Financial, four READ-ONLY tools. Read-only is the whole point of Lab 1:
this lab is about the four design surfaces, and nothing in it should be able to
fire a trade. The risk gate, the budget cap and the autonomy ladder live in
Lab 4 on Sunday, where human-in-the-loop is the subject rather than a sidebar.

    lab_1a_profile   PROFILE   who it is
    lab_1b_memory    MEMORY    what it carries between turns
    lab_1c_tools     TOOLS     what it can tell apart
    lab_1d_planning  PLANNING  how it decides

Each runs on its own:  python labs/lab_1a_profile.py [--web]
"""

from __future__ import annotations

import json
import re
import time

from _kit import meter

# ── the world ────────────────────────────────────────────────────────────────

POLICIES = {
    "trading": "Trades above $50,000 notional require desk-head approval. "
               "Same-day settlement is not offered on any instrument.",
    "access": "Access is granted per tool, never per project. Revocation is "
              "immediate and does not wait for the next review cycle.",
    "disbursement": "Funds release requires two approvers when the amount exceeds "
                    "$25,000, or any amount to a first-time beneficiary.",
}

CLIENTS = {
    "C-1041": {"name": "Halvorsen Trust", "tier": "institutional", "limit": 250_000},
    "C-2288": {"name": "R. Okonjo", "tier": "retail", "limit": 10_000},
}

INSTRUMENTS = {
    "AXR-7": {"name": "Aurex Rates 7yr", "price": 98.42, "settles": "T+2"},
    "HLV-2": {"name": "Halvorsen Green 2yr", "price": 101.15, "settles": "T+1"},
}


def search_policy(topic: str) -> str:
    hit = POLICIES.get(str(topic).strip().lower())
    return hit or f"No policy found for {topic!r}. Known topics: {', '.join(POLICIES)}"


def lookup_client(client_id: str) -> str:
    c = CLIENTS.get(str(client_id).strip().upper())
    return json.dumps(c) if c else f"No client {client_id!r}"


def price_instrument(symbol: str) -> str:
    i = INSTRUMENTS.get(str(symbol).strip().upper())
    return json.dumps(i) if i else f"No instrument {symbol!r}. Known: {', '.join(INSTRUMENTS)}"


def check_limits(client_id: str, notional: float) -> str:
    c = CLIENTS.get(str(client_id).strip().upper())
    if not c:
        return f"No client {client_id!r}"
    try:
        n = float(notional)
    except (TypeError, ValueError):
        return f"notional must be a number, got {notional!r}"
    return json.dumps({"within_limit": n <= c["limit"], "limit": c["limit"], "requested": n})


TOOLS = {"search_policy": search_policy, "lookup_client": lookup_client,
         "price_instrument": price_instrument, "check_limits": check_limits}


def call_tool(name: str, args: dict) -> str:
    """A tool that raises must come back as an OBSERVATION, never as a crash —
    the agent can re-plan around a bad argument only if it gets to see one."""
    fn = TOOLS.get(name)
    if not fn:
        return f"No such tool {name!r}. Available: {', '.join(TOOLS)}"
    try:
        return fn(**(args or {}))
    except TypeError as e:
        return f"Tool error: wrong arguments — {e}"
    except Exception as e:  # noqa: BLE001
        return f"Tool error: {e}"


def _fn(name: str, description: str, props: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": props, "required": required}}}


# Written as an INTERFACE: each description says what the tool is for and when to
# reach for it — not merely what it returns.
SCHEMA = [
    _fn("search_policy",
        "Look up an Aurex internal policy that governs what is allowed. Use this "
        "before asserting any rule. Topics: trading, access, disbursement.",
        {"topic": {"type": "string", "description": "One of: trading, access, disbursement"}},
        ["topic"]),
    _fn("lookup_client",
        "Fetch a client's name, tier and standing trading limit by id (e.g. C-1041). "
        "Use when you need who the client is or what they are permitted.",
        {"client_id": {"type": "string", "description": "Client id, e.g. C-1041"}},
        ["client_id"]),
    _fn("price_instrument",
        "Fetch an instrument's current price and settlement cycle by symbol (e.g. "
        "AXR-7). Use to turn a quantity into a notional, or to check settlement.",
        {"symbol": {"type": "string", "description": "Instrument symbol, e.g. AXR-7"}},
        ["symbol"]),
    _fn("check_limits",
        "Test one specific notional amount against one client's limit. Use only "
        "AFTER you know both the client and the amount; it answers yes/no, not why.",
        {"client_id": {"type": "string"}, "notional": {"type": "number"}},
        ["client_id", "notional"]),
]

# Same four functions, described the way tools get written when nobody owns them.
VAGUE_SCHEMA = [
    _fn("search_policy", "Search policies.", {"topic": {"type": "string"}}, ["topic"]),
    _fn("lookup_client", "Get client info.", {"client_id": {"type": "string"}}, ["client_id"]),
    _fn("price_instrument", "Get price.", {"symbol": {"type": "string"}}, ["symbol"]),
    _fn("check_limits", "Check limits.",
        {"client_id": {"type": "string"}, "notional": {"type": "number"}},
        ["client_id", "notional"]),
]

SCHEMAS = {"good": SCHEMA, "vague": VAGUE_SCHEMA}

# ── profiles ─────────────────────────────────────────────────────────────────

PROFILES = {
    "blank": "You are a helpful assistant.",
    "operations": (
        "You are an operations agent at Aurex Financial, a regulated broker-dealer. "
        "Establish facts with tools before you assert anything. Never state a limit "
        "or a policy you have not looked up. Answer in at most three sentences."),
    "compliance": (
        "You are a compliance officer at Aurex Financial. Your job is to find the "
        "reason something CANNOT proceed. Check policy first, always. Cite the "
        "specific policy language you relied on. If anything is unverified, say so "
        "plainly rather than estimating."),
    "sales": (
        "You are a relationship manager at Aurex Financial. You want to find a way "
        "to say yes. Look up what you need, then propose the closest thing that "
        "would work if the exact request cannot."),
}

# ── the task every planner in 1d must answer ─────────────────────────────────
# Four facts, three tools, and one of them contradicts the premise of the
# question — which is what makes an adaptive planner worth its cost.

TASK = ("Client C-1041 wants to buy 1,800 units of AXR-7 and settle today. "
        "Can we do it? Answer yes or no and give every reason.")

# Frozen BEFORE any planner ran — the only order in which a measure means
# anything (house rule 2: the measure is frozen before the system is good).
MUST_MENTION = {
    "notional ≈ $177k": lambda t: bool(re.search(r"17[67][,.]?\d{3}|177\s?k", t, re.I)),
    "over the $50k desk-head threshold": lambda t: "desk" in t.lower() or "50,000" in t or "50k" in t.lower(),
    "within the $250k client limit": lambda t: "250" in t,
    "same-day settlement refused (T+2)": lambda t: any(
        s in t.lower() for s in ("t+2", "same-day", "same day", "two business days")),
}


def score(text: str) -> tuple[int, list[str]]:
    missed = [k for k, test in MUST_MENTION.items() if not test(text or "")]
    return len(MUST_MENTION) - len(missed), missed


class Probe:
    """Snapshot the meter around one run so two designs can be compared honestly."""

    def __init__(self) -> None:
        self.c0, self.t0, self.s0 = meter.calls, meter.total_tokens, time.perf_counter()

    def done(self, text: str) -> dict:
        hits, missed = score(text)
        return {"calls": meter.calls - self.c0, "tokens": meter.total_tokens - self.t0,
                "secs": round(time.perf_counter() - self.s0, 1),
                "hits": hits, "of": len(MUST_MENTION), "missed": missed, "answer": text or ""}


# ── the loop ─────────────────────────────────────────────────────────────────


def react(cli, question: str, *, profile: str, schema=None, budget: int = 6,
          on_step=None, history: list[dict] | None = None) -> str:
    """ReAct: think → act → observe, interleaved, until the model stops asking.

    on_step(kind, label, detail) reports each move, so the CLI can print it and
    the web panel can render it without either owning the loop.
    """
    schema = SCHEMA if schema is None else schema
    messages = ([{"role": "system", "content": profile}] +
                (list(history) if history else []) +
                [{"role": "user", "content": question}])
    for n in range(1, budget + 1):
        reply = cli.chat.completions.create(model="mai", messages=messages, tools=schema)
        msg = reply.choices[0].message
        meter.add(reply.usage, "react")
        if not msg.tool_calls:
            if on_step:
                on_step("good", f"stopped after {n} step(s)", "")
            return msg.content or ""
        messages.append(msg.model_dump(exclude_none=True))
        for c in msg.tool_calls:
            args = json.loads(c.function.arguments or "{}")
            out = call_tool(c.function.name, args)
            if on_step:
                on_step("", f"{c.function.name}({json.dumps(args)[:56]})", out[:88])
            messages.append({"role": "tool", "tool_call_id": c.id, "content": out})
    if on_step:
        on_step("bad", f"hit the {budget}-step budget cap", "stopped without finishing")
    return ""


def first_tool(cli, question: str, schema) -> str:
    """What does it reach for FIRST? One call, no loop — routing is the whole test."""
    reply = cli.chat.completions.create(
        model="mai", tools=schema,
        messages=[{"role": "system", "content": PROFILES["operations"]},
                  {"role": "user", "content": question}])
    meter.add(reply.usage, "routing")
    tc = reply.choices[0].message.tool_calls
    return tc[0].function.name if tc else "(answered with no tool)"


ROUTING = [
    ("Is $180,000 inside C-1041's limit?", "check_limits"),
    ("What does our policy say about big trades?", "search_policy"),
    ("When does AXR-7 settle?", "price_instrument"),
    ("Who is C-2288?", "lookup_client"),
]

__all__ = [
    "POLICIES", "CLIENTS", "INSTRUMENTS", "TOOLS", "call_tool",
    "SCHEMA", "VAGUE_SCHEMA", "SCHEMAS", "PROFILES", "TASK", "MUST_MENTION",
    "score", "Probe", "react", "first_tool", "ROUTING",
]
