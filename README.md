# Modern AI Pro — Level 3 · AI Builder Labs

The lab kit for the **AI Builder** weekend (Level 3 of the Modern AI Pro ladder). Every hands-on session runs from this repo. Labs land here move-by-move over the weekend — clone once, `git pull` each morning.

Level 2 taught you to build **one reliable component**. Level 3 is the first level whose unit of work is a **system**: several agents, several tools, a person in the loop, and failure modes that only appear when the parts interact.

## Setup (~10 minutes, before Friday)

```bash
git clone https://github.com/balajivis/mai-builder-labs.git
cd mai-builder-labs
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Then **mint your personal MAI key** at [study.modernaipro.com/practice](https://study.modernaipro.com/practice) and paste it into `OPENAI_API_KEY` in your `.env`.

**Two traps that cost people a morning.** The key and the base URL travel together — a `mai_` key needs `OPENAI_BASE_URL` pointed at the class proxy, a personal `sk-` key needs that line absent, and both mixed combinations return a 401 that looks exactly like a bad key. And **minting a second key revokes the first instantly**: it is shown exactly once, so paste it straight in and do not press the button twice.

**Smoke-test** — proves Python, the install and your key in one shot:

```bash
python labs/lab_1a_tools.py --web
```

That opens a page at `localhost:7860` with the lab's knobs on it. No extra install: the panel is served by Python's own standard library, so there is nothing to `pip install` and nothing to sign in to. Drop `--web` for the same lab as a guided walkthrough in the terminal — both run the same code.

## The labs

Run in order; each builds on the last.

| Day | Lab | Name |
|---|---|---|
| 1 (Fri) | 1 | **Designing the Agent** — profile · memory · tools · planning (four files, below) |
| 2 (Sat) | 2 | **Tools, Budgets and Self-Aimed Retrieval** — descriptions that route, caps that stop, agentic RAG |
| 2 (Sat) | 3 | **Wire a Topology, Then Earn It** — supervisor · collaboration · pipeline, and the ablation against one agent |
| 3 (Sun) | 4 | **Human-in-the-Loop Controls** — risk tags, approval queues, escalation, fail closed |
| 3 (Sun) | 5 | **Prove It, Guard It, Ship It** — the capstone: golden set, red-team, one system on your own use case |

### Lab 1 is four files, one per design surface

An agent is not one thing you prompt. It is four surfaces you choose, and each one changes behaviour without touching the model. Run the one being taught; each takes about three minutes.

Tools come first because they are the thing you **build** — the profile is a knob, and a knob only teaches once there is a machine under it.

| | Surface | Run it | The question it answers |
|---|---|---|---|
| **1a** | **Tools** | `python labs/lab_1a_tools.py --web` | What can it tell apart? Ask it anything and watch five different interfaces route it. **Start here.** |
| **1b** | **Profile** | `python labs/lab_1b_profile.py --web` | Who is it? The knob on the machine you just built — closing on whether a profile can repair a broken tool layer. It can. |
| **1c** | **Memory** | `python labs/lab_1c_memory.py --web` | What survives a turn? Turn 3 says "they" and names nobody. Five policies, five different bills. |
| **1d** | **Planning** | `python labs/lab_1d_planning.py --web` | How does it decide? ReAct vs Plan-and-Execute vs ReWOO, on one frozen scorecard. |

`python labs/lab_1.py` runs all four back to back.

Every claim in these labs was measured against the class model on 2026-09-12 rather than asserted, and three of the four first drafts turned out to teach something the model does not do. The numbers in each file's header are reproducible — you should land on the same table.

Every tool in Lab 1 is **read-only on purpose**. The risk gate, the budget cap and the autonomy ladder are Lab 4 on Sunday, where human-in-the-loop is the subject rather than a sidebar — nothing in Lab 1 should compete with the design lesson.

## What is different from Level 2

**Two fixtures, one for each half of the weekend.**

**[`labs/_lab1.py`](./labs/_lab1.py) — Orbit, an online marketplace and its support desk.** Four read-only tools over customers, orders and refund policy. The domain is chosen so nobody spends the lab decoding the scenario: everyone has chased a refund from a big retailer, and everyone can tell instantly whether the agent's answer to Priya is a good one. Lab 1 is about *design*, so nothing in it can issue a refund — there is no gate to distract from the four surfaces.

**[`labs/_aurex.py`](./labs/_aurex.py) — Aurex Financial, from Lab 2 on.** A regulated firm with nine tools, three destructive and two irreversible. L2's Meridian corpus existed so *retrieval* mistakes were visible; Aurex exists so *control* mistakes are visible, and it is where the gate, the budget cap and the autonomy ladder live.

Three things live there and nowhere else:

- **The risk register** — every tool tagged `read` / `write` / `destructive`. The tag lives on the **tool**, not in the prompt. No wording talks its way past a structural check.
- **Fail closed by default** — an unknown tool is treated as destructive, because a tool nobody classified is exactly the one nobody thought about.
- **The autonomy ladder** — `suggest → approve → notify → act`, applied per action class rather than to the whole system at once. You start at `approve` and widen only with evidence.

`labs/_kit.py` is carried over from Level 2 unchanged — same `client()`, `chat()`, `stages()`, the cost meter and the JSONL tracer. If you did L2, it will all be familiar.

## Getting updates

```bash
git pull
```

Run it at the start of every session. New labs and fixes land during the weekend.

## Stuck?

Read `FAQ.md` first — it covers the common errors verbatim. Then ask in the cohort room at [study.modernaipro.com](https://study.modernaipro.com). If Python itself is fighting you, the browser **Lab Bench** at [study.modernaipro.com/learn/lab](https://study.modernaipro.com/learn/lab) runs the same files with nothing to install.
