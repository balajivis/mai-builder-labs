# -*- coding: utf-8 -*-
"""Lab 1 — Designing the Agent

Modern AI Pro · Level 3 · AI Builder · Day 1

An agent is not one thing you prompt. It is four design surfaces you choose,
and every one of them changes behaviour without touching the model:

    1a  PROFILE    who it is          — the standing instruction, its judgement
    1b  MEMORY     what it carries    — what survives a turn, and at what cost
    1c  TOOLS      what it tells apart— the description IS the interface
    1d  PLANNING   how it decides     — ReAct · Plan-and-Execute · ReWOO

Each surface is its own file so you can run just the one being taught, and so a
stage that breaks never blocks the other three. Start with 1a: the profile is
the only surface you can change with no code at all.

    python labs/lab_1a_profile.py  --web     ← start here
    python labs/lab_1b_memory.py   --web
    python labs/lab_1c_tools.py    --web
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
    ("1a", "Profile — who it is", "lab_1a_profile.py"),
    ("1b", "Memory — what it carries", "lab_1b_memory.py"),
    ("1c", "Tools — what it tells apart", "lab_1c_tools.py"),
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
        "one:\n  python labs/lab_1a_profile.py --web[/dim]\n")
    for key, title, f in PARTS:
        say(f"\n[bold yellow]═══ Lab {key} · {title} ═══[/bold yellow]\n")
        sys.argv = [str(HERE / f)]
        try:
            runpy.run_path(str(HERE / f), run_name="__main__")
        except SystemExit:
            pass
        except KeyboardInterrupt:
            say("\n[dim]skipped.[/dim]")
