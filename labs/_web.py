# -*- coding: utf-8 -*-
"""A knob panel in the browser, in the standard library.

Every Lab 1 file can run two ways: as a guided CLI walkthrough, or as a page you
poke at. This module is the second one. It is deliberately dependency-free —
no Gradio, no Streamlit, no Flask — because the worst possible moment to ask a
room of thirty people to pip-install something is the middle of a lab.

    from _web import Knob, Panel, serve
    serve(Panel(title=..., knobs=[Knob(...)], run=my_run_fn))

`run(cli, values) -> str` returns an HTML fragment. Server-rendered on purpose:
the alternative is shipping a client-side renderer, and a lab is not the place
to debug one. Helpers below (h, step, note, table) cover everything the labs
need, and `esc` is applied at the edges so model output can never break the page.

Port 7860 by default (--port to move it). Binds 127.0.0.1 only — this holds a
live API key, so it must never be reachable from the network.
"""

from __future__ import annotations

import html as _html
import json
import socket
import sys
import threading
import traceback
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ── rendering helpers ────────────────────────────────────────────────────────


def esc(s) -> str:
    return _html.escape(str(s if s is not None else ""))


def h(tag: str, body: str = "", cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return f"<{tag}{c}>{body}</{tag}>"


def note(text: str, kind: str = "") -> str:
    """A short aside. kind: '' | 'good' | 'warn' | 'bad'."""
    return f'<p class="note {kind}">{esc(text)}</p>'


def step(label: str, detail: str = "", kind: str = "") -> str:
    """One line of an agent trace — a tool call, a stop, a denial."""
    d = f'<span class="d">{esc(detail)}</span>' if detail else ""
    return f'<div class="step {kind}"><span class="l">{esc(label)}</span>{d}</div>'


def answer(text: str) -> str:
    return f'<div class="answer">{esc(text)}</div>'


def table(headers: list[str], rows: list[list], highlight: int | None = None) -> str:
    th = "".join(f"<th>{esc(x)}</th>" for x in headers)
    trs = []
    for i, r in enumerate(rows):
        cls = ' class="hi"' if highlight is not None and i == highlight else ""
        trs.append(f"<tr{cls}>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>")
    return f'<table><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table>'


def section(title: str, body: str) -> str:
    return f'<section><h3>{esc(title)}</h3>{body}</section>'


# ── the panel spec ───────────────────────────────────────────────────────────


@dataclass
class Knob:
    key: str
    label: str
    kind: str = "text"           # text | textarea | select | slider | toggle
    default: object = ""
    options: list = field(default_factory=list)   # select: [(value, label)] or [value]
    min: int = 1
    max: int = 10
    help: str = ""


@dataclass
class Panel:
    title: str
    subtitle: str
    knobs: list          # list[Knob]
    run: object          # callable(cli, values: dict) -> HTML fragment
    intro: str = ""      # HTML shown before the first run
    button: str = "Run"


# ── the page ─────────────────────────────────────────────────────────────────

CSS = """
*{box-sizing:border-box} body{margin:0;background:#09090b;color:#e4e4e7;
  font:14px/1.6 ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif}
.wrap{max-width:1140px;margin:0 auto;padding:28px 22px 80px}
header{border-bottom:1px solid #27272a;padding-bottom:16px;margin-bottom:22px}
.eyebrow{color:#f59e0b;font-size:11px;letter-spacing:.16em;text-transform:uppercase;font-weight:600}
h1{margin:6px 0 4px;font-size:22px;color:#fafafa;font-weight:650}
.sub{color:#a1a1aa;margin:0;max-width:70ch}
.cols{display:grid;grid-template-columns:minmax(300px,360px) 1fr;gap:24px;align-items:start}
@media(max-width:880px){.cols{grid-template-columns:1fr}}
.panel{background:#18181b;border:1px solid #27272a;border-radius:12px;padding:18px;
  position:sticky;top:22px}
@media(max-width:880px){.panel{position:static}}
label{display:block;margin:0 0 5px;font-size:12px;color:#d4d4d8;font-weight:600}
.hint{color:#71717a;font-size:11px;margin:-2px 0 7px;line-height:1.45}
.k{margin-bottom:17px}
input[type=text],textarea,select{width:100%;background:#09090b;color:#e4e4e7;
  border:1px solid #3f3f46;border-radius:8px;padding:9px 11px;font:13px/1.55 inherit}
textarea{min-height:132px;resize:vertical;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
input:focus,textarea:focus,select:focus{outline:none;border-color:#f59e0b}
input[type=range]{width:100%;accent-color:#f59e0b}
.rangeval{float:right;color:#f59e0b;font-weight:600;font-variant-numeric:tabular-nums}
button{width:100%;background:#f59e0b;color:#18181b;border:0;border-radius:8px;
  padding:11px;font-size:14px;font-weight:700;cursor:pointer}
button:hover{background:#fbbf24} button:disabled{opacity:.5;cursor:wait}
.presets{display:flex;flex-wrap:wrap;gap:6px;margin:-6px 0 14px}
.presets button{width:auto;background:#27272a;color:#d4d4d8;font-size:11.5px;
  font-weight:600;padding:5px 10px;border:1px solid #3f3f46}
.presets button:hover{background:#3f3f46;color:#fafafa}
.out{min-height:220px}
section{background:#18181b;border:1px solid #27272a;border-radius:12px;
  padding:15px 18px;margin-bottom:14px}
section h3{margin:0 0 11px;font-size:12px;color:#f59e0b;letter-spacing:.1em;
  text-transform:uppercase;font-weight:700}
.step{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;
  padding:5px 9px;border-left:2px solid #3f3f46;margin:4px 0;background:#0f0f11}
.step .l{color:#fafafa;font-weight:600} .step .d{color:#71717a;margin-left:9px}
.step.good{border-left-color:#4ade80} .step.good .l{color:#4ade80}
.step.bad{border-left-color:#f87171} .step.bad .l{color:#f87171}
.step.warn{border-left-color:#fbbf24} .step.warn .l{color:#fbbf24}
.answer{background:#0f0f11;border:1px solid #27272a;border-radius:8px;
  padding:12px 14px;margin:9px 0;white-space:pre-wrap;color:#e4e4e7}
.note{color:#a1a1aa;font-size:12.5px;margin:8px 0 0}
.note.good{color:#4ade80} .note.warn{color:#fbbf24} .note.bad{color:#f87171}
table{width:100%;border-collapse:collapse;font-size:13px;margin-top:4px}
th{text-align:left;color:#71717a;font-size:11px;letter-spacing:.07em;
  text-transform:uppercase;padding:5px 9px;border-bottom:1px solid #27272a;font-weight:700}
td{padding:7px 9px;border-bottom:1px solid #1f1f23;font-variant-numeric:tabular-nums}
tr.hi td{background:#1c1917;color:#fbbf24}
.spin{color:#f59e0b;padding:22px 2px;font-size:13px}
.err{background:#1f1315;border:1px solid #7f1d1d;color:#fca5a5;border-radius:8px;
  padding:13px 15px;white-space:pre-wrap;font-family:ui-monospace,Menlo,monospace;font-size:12px}
.intro{color:#a1a1aa;font-size:13px}
.intro code{background:#27272a;padding:1.5px 5px;border-radius:4px;color:#fbbf24;font-size:12px}
"""

JS = """
const $=s=>document.querySelector(s);
function values(){const v={};document.querySelectorAll('[data-k]').forEach(e=>{
  v[e.dataset.k]=e.type==='checkbox'?e.checked:e.value});return v}
function preset(k,val){const e=document.querySelector(`[data-k="${k}"]`);
  if(e){e.value=val;e.dispatchEvent(new Event('input'))}}
document.querySelectorAll('input[type=range]').forEach(r=>{
  const out=document.querySelector(`#v_${r.dataset.k}`);
  const sync=()=>{if(out)out.textContent=r.value};r.addEventListener('input',sync);sync()});
async function run(){
  const b=$('#go');b.disabled=true;const t0=Date.now();
  $('#out').innerHTML='<div class="spin">running — a real model call takes a few seconds…</div>';
  try{
    const r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(values())});
    const j=await r.json();
    $('#out').innerHTML=j.ok?j.html:`<div class="err">${j.error}</div>`;
  }catch(e){$('#out').innerHTML=`<div class="err">${e}</div>`}
  finally{b.disabled=false;
    const s=((Date.now()-t0)/1000).toFixed(1);
    const f=document.createElement('p');f.className='note';f.textContent=`${s}s`;
    $('#out').appendChild(f)}
}
$('#go').addEventListener('click',run);
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key==='Enter')run()});
"""


def _knob_html(k: Knob) -> str:
    hint = f'<p class="hint">{esc(k.help)}</p>' if k.help else ""
    if k.kind == "textarea":
        field_html = f'<textarea data-k="{k.key}">{esc(k.default)}</textarea>'
    elif k.kind == "select":
        opts = []
        for o in k.options:
            val, lab = o if isinstance(o, (tuple, list)) else (o, o)
            sel = " selected" if val == k.default else ""
            opts.append(f'<option value="{esc(val)}"{sel}>{esc(lab)}</option>')
        field_html = f'<select data-k="{k.key}">{"".join(opts)}</select>'
    elif k.kind == "slider":
        field_html = (f'<input type="range" data-k="{k.key}" min="{k.min}" max="{k.max}" '
                      f'value="{esc(k.default)}">')
    else:
        field_html = f'<input type="text" data-k="{k.key}" value="{esc(k.default)}">'
    val = f'<span class="rangeval" id="v_{k.key}"></span>' if k.kind == "slider" else ""
    return f'<div class="k"><label>{esc(k.label)}{val}</label>{hint}{field_html}</div>'


def _page(panel: Panel, presets_html: str) -> str:
    knobs = "".join(_knob_html(k) for k in panel.knobs)
    intro = f'<section><h3>start here</h3><div class="intro">{panel.intro}</div></section>' if panel.intro else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(panel.title)} · Modern AI Pro L3</title><style>{CSS}</style></head><body>
<div class="wrap">
  <header>
    <div class="eyebrow">Modern AI Pro · Level 3 · AI Builder · Lab 1</div>
    <h1>{esc(panel.title)}</h1>
    <p class="sub">{esc(panel.subtitle)}</p>
  </header>
  <div class="cols">
    <div class="panel">{presets_html}{knobs}
      <button id="go">{esc(panel.button)}</button>
      <p class="hint" style="margin-top:9px">⌘/Ctrl + Enter also runs it.</p>
    </div>
    <div class="out" id="out">{intro}</div>
  </div>
</div><script>{JS}</script></body></html>"""


def presets(knob_key: str, items: list[tuple[str, str]]) -> str:
    """Quick-fill buttons above the knobs: [(button label, value to load)]."""
    btns = "".join(
        f"""<button onclick='preset({json.dumps(knob_key)},{json.dumps(v)})'>{esc(lab)}</button>"""
        for lab, v in items)
    return f'<div class="presets">{btns}</div>'


# ── the server ───────────────────────────────────────────────────────────────


def _free_port(start: int) -> int:
    for p in range(start, start + 20):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return start


def serve(panel: Panel, cli, port: int = 7860, presets_html: str = "", open_browser: bool = True) -> None:
    page = _page(panel, presets_html).encode()
    port = _free_port(port)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # noqa: D102 — the rich output is the log
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            if self.path in ("/", "/index.html"):
                self._send(200, page, "text/html; charset=utf-8")
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):  # noqa: N802
            if self.path != "/api/run":
                return self._send(404, b"not found", "text/plain")
            n = int(self.headers.get("Content-Length") or 0)
            try:
                vals = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                return self._send(400, b'{"ok":false,"error":"bad json"}', "application/json")
            try:
                out = {"ok": True, "html": panel.run(cli, vals)}
            except Exception as e:  # noqa: BLE001
                # Never 500 at a student mid-lab: show the failure in the page,
                # keep the server up, and print the full trace to the terminal.
                traceback.print_exc()
                out = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            self._send(200, json.dumps(out).encode(), "application/json")

    url = f"http://127.0.0.1:{port}"
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"\n  {panel.title}\n  → {url}   (Ctrl-C to stop)\n")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped.\n")
        srv.server_close()


def wants_web(argv: list[str] | None = None) -> bool:
    return "--web" in (argv if argv is not None else sys.argv)


def port_from(argv: list[str] | None = None, default: int = 7860) -> int:
    a = argv if argv is not None else sys.argv
    if "--port" in a:
        try:
            return int(a[a.index("--port") + 1])
        except (IndexError, ValueError):
            pass
    return default
