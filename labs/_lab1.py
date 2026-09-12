# -*- coding: utf-8 -*-
"""The world Lab 1 is played in — shared by all four files.

**Orbit** — an online marketplace — and its customer support desk. Four
READ-ONLY tools.

The domain is deliberate. Everyone in the room has chased a refund from a big
retailer, so nobody spends the lab decoding the scenario instead of the lesson.
The agent decides whether Priya gets her money back, and every person reading
that answer knows instantly whether it is a good one. You do not need the domain
explained, which means every minute of the lab is spent on design.

Read-only is also deliberate. This lab is about the four design surfaces; the
risk gate, the budget cap and the autonomy ladder live in Lab 4, where
human-in-the-loop is the subject rather than a sidebar. Nothing here can issue a
refund, so nothing here competes with the design lesson.

    lab_1a_tools     TOOLS     what it can tell apart   ← build it first
    lab_1b_profile   PROFILE   who it is                — steer what you built
    lab_1c_memory    MEMORY    what it carries between turns
    lab_1d_planning  PLANNING  how it decides

Tools come first on purpose: the profile is a knob, and a knob is only teachable
once there is a machine under it.

Each runs on its own:  python labs/lab_1a_tools.py [--web]
"""

from __future__ import annotations

import json
import re
import time

from _kit import meter

# ── the world ────────────────────────────────────────────────────────────────

POLICIES = {
    "refunds": "Refunds are accepted within 30 days of delivery, for any reason. "
               "Refunds above $100 require supervisor approval before they are issued.",
    "damaged": "An item that arrived damaged or faulty is covered for 90 days from "
               "delivery, regardless of the standard 30-day refund window. Photo "
               "evidence is required, and counts as received once uploaded to the order.",
    "returns": "Standard delivery is 3-5 working days. Return postage is paid by Orbit "
               "for damaged items and by the customer otherwise. Opened items may be "
               "returned if faulty.",
    "membership": "Orbit Prime can be cancelled any time; the remaining month is not "
                  "refunded. Prime members get free return postage on everything.",
}

CUSTOMERS = {
    "priya@example.com": {"name": "Priya Raman", "member_since": "2023-04-11",
                          "plan": "Orbit Prime", "orders_last_year": 14},
    "tom@example.com": {"name": "Tom Whitfield", "member_since": "2026-08-30",
                        "plan": "no membership", "orders_last_year": 1},
}

ORDERS = {
    "A-4417": {"customer": "priya@example.com", "item": "Cortado espresso machine",
               "total": 148.50, "delivered": "2026-08-02", "days_since_delivery": 41,
               "customer_reported": "arrived damaged — photos uploaded"},
    "A-5120": {"customer": "tom@example.com", "item": "Walnut lamp shade",
               "total": 32.00, "delivered": "2026-09-05", "days_since_delivery": 7,
               "customer_reported": None},
}


def search_policy(topic: str) -> str:
    hit = POLICIES.get(str(topic).strip().lower())
    return hit or f"No policy found for {topic!r}. Known topics: {', '.join(POLICIES)}"


def get_customer(email: str) -> str:
    c = CUSTOMERS.get(str(email).strip().lower())
    return json.dumps(c) if c else f"No customer {email!r}"


def get_order(order_id: str) -> str:
    o = ORDERS.get(str(order_id).strip().upper())
    return json.dumps(o) if o else f"No order {order_id!r}. Known: {', '.join(ORDERS)}"


def check_refund_window(order_id: str) -> str:
    """Answers the STANDARD window only — deliberately.

    It knows nothing about the 90-day damaged-goods route, so on order A-4417 it
    returns a perfectly accurate NO to a question nobody asked. An agent that
    stops here is confidently wrong, and it is the tool's fault, not the model's.
    A tool that answers a narrower question than its name suggests is the single
    most common cause of a wrong agent — and Lab 1d is built on this one.
    """
    o = ORDERS.get(str(order_id).strip().upper())
    if not o:
        return f"No order {order_id!r}"
    d = o["days_since_delivery"]
    return json.dumps({"within_standard_30_day_window": d <= 30,
                       "days_since_delivery": d, "standard_window_days": 30})


TOOLS = {"search_policy": search_policy, "get_customer": get_customer,
         "get_order": get_order, "check_refund_window": check_refund_window}


def _fn(name: str, description: str, props: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": props, "required": required}}}


# Written as an INTERFACE: each description says what the tool is for and when to
# reach for it — not merely what it returns.
SCHEMA = [
    _fn("search_policy",
        "Look up an Orbit support policy — the rules that decide what a customer is "
        "entitled to. Use this before promising or refusing anything. Topics: refunds, "
        "damaged, returns, membership.",
        {"topic": {"type": "string",
                   "description": "One of: refunds, damaged, returns, membership"}},
        ["topic"]),
    _fn("get_customer",
        "Fetch a customer's name, membership plan and how long they have shopped with "
        "Orbit, by email address. Use when you need who you are talking to.",
        {"email": {"type": "string", "description": "Customer email, e.g. priya@example.com"}},
        ["email"]),
    _fn("get_order",
        "Fetch one order by its id (e.g. A-4417): the item, the amount paid, the "
        "delivery date, and anything the customer reported about its condition. Use to "
        "establish what was bought and what happened to it.",
        {"order_id": {"type": "string", "description": "Order id, e.g. A-4417"}},
        ["order_id"]),
    _fn("check_refund_window",
        "Answer directly whether an order is still inside the STANDARD 30-day refund "
        "window. Looks the dates up itself. Returns yes/no plus the day count — it does "
        "not consider damaged goods or any other exception.",
        {"order_id": {"type": "string"}},
        ["order_id"]),
]

# The SAME four functions, named and described the way tools get written when
# nobody owns them as an interface. The names go vague too — a good name carries
# much of the routing signal by itself, so a "vague" set that keeps search_policy
# is not vague at all. get_info, lookup and check are what actually ships.
VAGUE_NAMES = {"search_policy": "search", "get_customer": "get_info",
               "get_order": "lookup", "check_refund_window": "check"}
VAGUE_SCHEMA = [
    _fn("search", "Search for information.", {"topic": {"type": "string"}}, ["topic"]),
    _fn("get_info", "Get info about a record.", {"email": {"type": "string"}}, ["email"]),
    _fn("lookup", "Look up a value.", {"order_id": {"type": "string"}}, ["order_id"]),
    _fn("check", "Check a value against a rule.", {"order_id": {"type": "string"}}, ["order_id"]),
]

SCHEMAS = {"good": SCHEMA, "vague": VAGUE_SCHEMA}

# ── the 2×2 that Lab 1a actually measures ────────────────────────────────────
# Which carries the routing signal: the NAME or the DESCRIPTION? The only honest
# way to answer is to remove each and score what is left. They turn out to be
# REDUNDANT — either alone routes everything, and only removing BOTH costs a
# question. Routing is far more robust than tool-writing advice implies. But a
# description pointing the WRONG way costs as much as deleting both signals, and
# does it while every name is still perfect.
#
# The rule that survives the measurement: you may be terse, you may not be wrong.
ANON_NAMES = {"search_policy": "tool_a", "get_customer": "tool_b",
              "get_order": "tool_c", "check_refund_window": "tool_d"}


def build_schema(*, anonymise: bool = False, describe: bool = True,
                 overrides: dict | None = None) -> list[dict]:
    """A copy of SCHEMA with the name and/or description knobs turned."""
    out = json.loads(json.dumps(SCHEMA))   # deep copy — never mutate the shared one
    for t in out:
        f = t["function"]
        real = f["name"]
        if overrides and real in overrides:
            f["description"] = str(overrides[real])
        if not describe:
            f["description"] = ""
        if anonymise:
            f["name"] = ANON_NAMES[real]
    return out


def real_name(name: str) -> str:
    """Map tool_a → search_policy so one dispatch table serves every variant."""
    back = {v: k for k, v in ANON_NAMES.items()}
    back.update({v: k for k, v in VAGUE_NAMES.items()})
    return back.get(name, name)


def call_tool(name: str, args: dict) -> str:
    """A tool that raises must come back as an OBSERVATION, never as a crash —
    the agent can re-plan around a bad argument only if it gets to see one."""
    fn = TOOLS.get(name) or TOOLS.get(real_name(name))
    if not fn:
        return f"No such tool {name!r}. Available: {', '.join(TOOLS)}"
    try:
        return fn(**(args or {}))
    except TypeError as e:
        return f"Tool error: wrong arguments — {e}"
    except Exception as e:  # noqa: BLE001
        return f"Tool error: {e}"


# Six questions rather than four: with four tools and four obviously-separated
# questions everything scores 4/4 and the experiment cannot discriminate.
ROUTING_6 = [
    ("Is order A-4417 still inside the refund window?", "check_refund_window"),
    ("What does our policy say about refunds over $100?", "search_policy"),
    # Names the ORDER, not the customer: get_order takes an id, so "what did Priya
    # order?" is genuinely unanswerable in one hop and the model rightly declines
    # to guess. A routing question must be answerable by the tool it is scoring.
    ("What was in order A-4417, and what did it cost?", "get_order"),
    ("Who is tom@example.com?", "get_customer"),
    ("Which membership plan is priya@example.com on?", "get_customer"),
    ("Can someone return an item that arrived broken?", "search_policy"),
]

# A description that points the WRONG way, while every NAME stays perfect.
# Note what it does: "whether they are eligible for a refund" is a plausible
# thing for a customer record to hold, and it is exactly the phrase that pulls
# the model to get_customer when it should be checking the order's own window.
MISLEADING = {
    "check_refund_window": "Check a value against a rule for an order.",
    "get_customer": "Fetch a customer's full support record, including their order "
                    "history and whether they are eligible for a refund.",
}

# ── profiles ─────────────────────────────────────────────────────────────────

PROFILES = {
    "blank": "You are a helpful assistant.",
    "support": (
        "You are a support agent at Orbit, an online marketplace. Look things up before "
        "you promise or refuse anything — never state a policy or a date you have not "
        "checked. Answer the customer in at most three sentences."),
    "policy": (
        "You are a refunds reviewer at Orbit. Your job is to find the reason a refund "
        "cannot be issued as requested. Check policy first, always, and quote the "
        "specific rule you relied on. If anything is unverified, say so plainly rather "
        "than assuming in the customer's favour."),
    "retention": (
        "You are a retention specialist at Orbit. This customer is worth keeping and you "
        "want to find a way to yes. Look up what you need, then offer the closest thing "
        "you can actually authorise if the exact request is not possible."),
    # Used by 1b's closing experiment: does the PROFILE repair a broken TOOL layer?
    # With MISLEADING descriptions this lifts routing 5.0/6 → 6.0/6. It does, fully.
    "strict": (
        "You are a support agent at Orbit. Choose tools by what the question actually "
        "asks for. To test whether ONE order is still inside the refund window, use "
        "check_refund_window. To fetch who a customer is, use get_customer. Do not use "
        "a customer-record tool to answer a question about one order's eligibility."),
}

# ── the task every planner in 1d must answer ─────────────────────────────────
# Four facts, three tools, and a trap: check_refund_window returns a perfectly
# accurate NO — 41 days, outside the standard 30. An agent that stops there tells
# Priya no, confidently and wrongly. The damaged-goods policy overrides the
# standard window, and it lives in a DIFFERENT tool. This is what makes the task
# worth three planners: the cheap ones have to find it too.

TASK = ("Priya (priya@example.com) is asking for a refund on order A-4417. "
        "She says it arrived damaged. Can we refund her? Answer yes or no, "
        "and give every reason.")

# Frozen BEFORE any planner ran — the only order in which a measure means
# anything (house rule 2: the measure is frozen before the system is good).
MUST_MENTION = {
    "the $148.50 amount": lambda t: "148" in t,
    "41 days — outside the standard 30-day window":
        lambda t: "41" in t or "30-day" in t.lower() or "30 day" in t.lower(),
    "damaged goods are covered to 90 days":
        lambda t: "90" in t or "damag" in t.lower(),
    "over $100, so a supervisor must approve":
        lambda t: "supervisor" in t.lower() or "approval" in t.lower() or "approve" in t.lower(),
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


def first_tool(cli, question: str, schema, profile: str | None = None) -> str:
    """What does it reach for FIRST? One call, no loop — routing is the whole test.

    `profile` is a real parameter, not decoration: 1b's combine experiment holds the
    schema fixed and varies ONLY this. (It was hardcoded to the support profile at
    first, which silently made that whole experiment a no-op — every row came back
    identical because every row was in fact the same run.)
    """
    reply = cli.chat.completions.create(
        model="mai", tools=schema,
        messages=[{"role": "system", "content": profile or PROFILES["support"]},
                  {"role": "user", "content": question}])
    meter.add(reply.usage, "routing")
    tc = reply.choices[0].message.tool_calls
    return tc[0].function.name if tc else "(answered with no tool)"


ROUTING = ROUTING_6   # back-compat for anything importing the older short list

__all__ = [
    "POLICIES", "CUSTOMERS", "ORDERS", "TOOLS", "call_tool",
    "SCHEMA", "VAGUE_SCHEMA", "SCHEMAS", "PROFILES", "TASK", "MUST_MENTION",
    "score", "Probe", "react", "first_tool", "ROUTING", "ROUTING_6",
    "VAGUE_NAMES", "ANON_NAMES", "build_schema", "real_name", "MISLEADING",
]
