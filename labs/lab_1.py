# -*- coding: utf-8 -*-
"""Lab 1 — Designing the Agent

Modern AI Pro · Level 3 · AI Builder · Day 1

An agent is not one thing you prompt. It is four design surfaces you choose,
and every one of them changes behaviour without touching the model:

    1a  TOOLS      what it tells apart— the interface you hand the model
    1b  PROFILE    who it is          — the knob on the machine you just built
    1c  MEMORY     what it carries    — what survives a turn, and at what cost
    1d  PLANNING   how it decides     — ReAct · Plan-and-Execute · ReWOO

Each surface is its own file so you can run just the one being taught, and so a
stage that breaks never blocks the other three.

Tools come first because they are the thing you BUILD; the profile is a knob,
and a knob only teaches once there is a machine under it. 1b closes on the
measurement that ties the two together: a strict profile fully repairs a broken
tool layer (5.0/6 → 6.0/6), so the two surfaces are substitutable and choosing
between them is the design call.

    python labs/lab_1a_tools.py    --web     ← start here
    python labs/lab_1b_profile.py  --web
    python labs/lab_1c_memory.py   --web
    python labs/lab_1d_planning.py --web

Drop --web for a guided walkthrough in the terminal. This file just runs all
four back to back, in order.

The risk gate, the budget cap and the autonomy ladder are NOT in Lab 1 — they
are Lab 4 on Sunday, where human-in-the-loop is the subject rather than a
sidebar. Every tool in Lab 1 is read-only on purpose, so nothing in it can
distract from design.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from _kit import banner, say  # noqa: E402

PARTS = [
    ("1a", "Tools — what it tells apart", "lab_1a_tools.py"),
    ("1b", "Profile — who it is", "lab_1b_profile.py"),
    ("1c", "Memory — what it carries", "lab_1c_memory.py"),
    ("1d", "Planning — how it decides", "lab_1d_planning.py"),
]

if __name__ == "__main__":
    if "--web" in sys.argv:
        say("\n  The web panels are per-surface — each is its own page and its own port:\n")
        for key, title, f in PARTS:
            say(f"    python labs/{f} --web    [dim]{title}[/dim]")
        say("\n  [dim]Start with 1a.[/dim]\n")
        sys.exit(0)

    banner("Level 3 · AI Builder · Day 1", "Lab 1 · Designing the Agent")
    say("[dim]Four surfaces, four files. Running all of them in order — or run just "
        "one:\n  python labs/lab_1a_tools.py --web[/dim]\n")
    for key, title, f in PARTS:
        say(f"\n[bold yellow]═══ Lab {key} · {title} ═══[/bold yellow]\n")
        sys.argv = [str(HERE / f)]
        try:
            runpy.run_path(str(HERE / f), run_name="__main__")
        except SystemExit:
            pass
        except KeyboardInterrupt:
            say("\n[dim]skipped.[/dim]")
