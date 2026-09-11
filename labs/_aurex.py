"""Aurex Financial — the fictional regulated firm every Level 3 lab acts inside.

L2's Meridian was a retailer and its corpus existed so RETRIEVAL mistakes would be
visible. Aurex is a financial services firm and its systems exist so CONTROL
mistakes are visible: every tool here is tagged with what it can do, and two of
them cannot be undone.

Keep this file open while you work. The whole of Level 3 is the argument that the
tag belongs on the tool, not in the prompt — no wording talks its way past a
structural check, and a model that has been asked nicely is not a control.
"""

from __future__ import annotations

# ── the risk register ────────────────────────────────────────────────────────
# read        safe to run unattended
# write       reversible, but someone should be able to see it happened
# destructive irreversible or externally visible — a human decides, every time
RISK: dict[str, str] = {
    "search_policy":     "read",
    "lookup_client":     "read",
    "check_limits":      "read",
    "price_instrument":  "read",
    "draft_memo":        "write",
    "open_case":         "write",
    "place_trade":       "destructive",
    "release_funds":     "destructive",
    "revoke_access":     "destructive",
}

# What a denial should say back to the agent. A refusal that reads as a crash
# teaches the agent nothing; a refusal that explains itself lets it re-plan.
DENIAL = ("A human declined this action. Do not retry it. Explain to the user what "
          "you were about to do, why it needs approval, and what you can do instead.")

IRREVERSIBLE = {"place_trade", "release_funds"}


def risk_of(tool: str) -> str:
    """Unknown tools are DESTRUCTIVE, not read. Fail closed on the default too —
    a tool nobody classified is exactly the one you have not thought about."""
    return RISK.get(tool, "destructive")


def needs_human(tool: str, *, autonomy: str = "approve") -> bool:
    """Whether this call stops for a person.

    `autonomy` is the ladder from Sunday's session, per action class:
      suggest  → nothing runs; the agent drafts and stops
      approve  → destructive actions wait for a human (the default, and where
                 every new system starts)
      notify   → destructive-but-reversible run and are reported after
      act      → only ever earned, per tool, with evidence behind it
    """
    r = risk_of(tool)
    if autonomy == "suggest":
        return r != "read"
    if autonomy == "approve":
        return r == "destructive"
    if autonomy == "notify":
        return tool in IRREVERSIBLE
    if autonomy == "act":
        return False
    raise ValueError(f"unknown autonomy level: {autonomy!r}")
