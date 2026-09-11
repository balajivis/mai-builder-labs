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
python labs/lab_1.py
```

## The labs

Run in order; each builds on the last.

| Day | Lab | Name |
|---|---|---|
| 1 (Fri) | 1 | **Build the Loop You Can Audit** — the graph, tools, and the stop decision |
| 2 (Sat) | 2 | **Tools, Budgets and Self-Aimed Retrieval** — descriptions that route, caps that stop, agentic RAG |
| 2 (Sat) | 3 | **Wire a Topology, Then Earn It** — supervisor · collaboration · pipeline, and the ablation against one agent |
| 3 (Sun) | 4 | **Human-in-the-Loop Controls** — risk tags, approval queues, escalation, fail closed |
| 3 (Sun) | 5 | **Prove It, Guard It, Ship It** — the capstone: golden set, red-team, one system on your own use case |

## What is different from Level 2

**[`labs/_aurex.py`](./labs/_aurex.py) is the spine of the weekend.** Aurex Financial is a regulated firm with nine tools, three of them destructive and two irreversible. L2's Meridian corpus existed so *retrieval* mistakes were visible; Aurex exists so *control* mistakes are visible.

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
