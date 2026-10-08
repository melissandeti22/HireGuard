"""
Local labelling tool for the HireGuard annotation batch.

Shows one posting at a time with the AI suggestion (if any), the seven
indicators from annotation_guide.md as tick boxes, and keyboard shortcuts.
Every click writes the `fraudulent` and `notes` columns straight back into
the CSV, so you can stop and resume at any time. Nothing leaves your
computer: the server only listens on 127.0.0.1.

A timestamped backup of the CSV is made each time the tool starts. Close the
file in Excel while labelling -- Excel locks it and saves would fail (the
page tells you if that happens; nothing is lost).

Usage (from data-collection/):
    python labeling/label_tool.py
    python labeling/label_tool.py --file data/processed/annotation_batch.csv --port 8766

Keys: 0 / L = legitimate, 1 / F = fraudulent, X = exclude (not a job ad /
unusable), arrows = previous / next, 1-7 with Shift = toggle indicator.
"""

import argparse
import json
import os
import shutil
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd

DEFAULT_FILE = Path(__file__).resolve().parent.parent / "data" / "processed" / "annotation_batch_prelabelled.csv"
SHOWN_COLUMNS = [
    "source", "title", "company_profile", "location", "salary_range", "employment_type",
    "contact_email_domain", "is_free_email_provider", "posted_date", "url", "description",
    "requirements", "benefits", "duplicate_count", "short_text", "urgency_terms",
    "suggested_label", "suggested_notes", "confidence", "reason", "fraudulent", "notes",
]


class Store:
    """Holds the CSV in memory and writes it back atomically after each change."""

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)
        for col in ("fraudulent", "notes"):
            if col not in self.df.columns:
                self.df[col] = ""
        for col in SHOWN_COLUMNS:
            if col not in self.df.columns:
                self.df[col] = ""

    def rows(self) -> list[dict]:
        return [{"row": i, **r} for i, r in enumerate(self.df[SHOWN_COLUMNS].to_dict("records"))]

    def save(self, row: int, fraudulent: str, notes: str) -> None:
        if fraudulent not in ("0", "1", ""):
            raise ValueError("fraudulent must be 0, 1 or empty")
        with self.lock:
            self.df.loc[row, ["fraudulent", "notes"]] = [fraudulent, notes]
            tmp = self.path.with_suffix(".tmp")
            self.df.to_csv(tmp, index=False, encoding="utf-8-sig")
            os.replace(tmp, self.path)  # PermissionError if Excel has the file open


def make_handler(store: Store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the terminal quiet
            pass

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, payload) -> None:
            self._send(status, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            if self.path == "/":
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif self.path == "/api/rows":
                self._json(200, {"file": str(store.path), "rows": store.rows()})
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if self.path != "/api/label":
                return self._send(404, b"not found", "text/plain")
            try:
                data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                store.save(int(data["row"]), str(data["fraudulent"]), str(data.get("notes", "")))
                self._json(200, {"ok": True})
            except PermissionError:
                self._json(409, {"ok": False, "error": "The CSV is locked -- close it in Excel, then click the label again."})
            except (ValueError, KeyError, IndexError) as e:
                self._json(400, {"ok": False, "error": str(e)})

    return Handler


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>HireGuard Labelling</title>
<style>
:root{--bg:#f5f7fa;--card:#fff;--text:#16212e;--muted:#5b6b7f;--border:#e2e8f0;--navy:#1f4e79;
--red:#c2362f;--red-bg:#fdecea;--green:#17824a;--green-bg:#e6f6ec;--amber:#a86a00;--amber-bg:#fff5e0;--hl:#fff1a8}
@media (prefers-color-scheme:dark){:root{--bg:#0f1720;--card:#16212e;--text:#e6edf3;--muted:#93a4b8;--border:#263445;
--navy:#7fb2e5;--red:#f08a83;--red-bg:#3a1d1b;--green:#6fd39b;--green-bg:#15301f;--amber:#f2c063;--amber-bg:#352a12;--hl:#5c4d00}}
*{box-sizing:border-box}body{margin:0;font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--text)}
header{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--border);padding:10px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header h1{font-size:17px;margin:0}.bar{flex:1;min-width:160px;height:8px;background:var(--border);border-radius:9px;overflow:hidden}
.bar span{display:block;height:100%;background:var(--navy)}.muted{color:var(--muted);font-size:13px}
select,button,input[type=text]{font:inherit;border:1px solid var(--border);border-radius:8px;padding:6px 10px;background:var(--card);color:var(--text)}
main{max-width:1200px;margin:0 auto;padding:18px 20px 120px;display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:18px}
@media (max-width:900px){main{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px}
.meta{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 14px}.chip{font-size:12px;padding:3px 9px;border-radius:999px;background:var(--bg);border:1px solid var(--border)}
.chip.warn{background:var(--amber-bg);color:var(--amber);border-color:transparent}
.body{white-space:pre-wrap;word-wrap:break-word}.body h3{margin:16px 0 4px;font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
mark{background:var(--hl);color:inherit;border-radius:3px;padding:0 2px}
.sugg{border-radius:10px;padding:12px;margin-bottom:14px}.sugg.f{background:var(--red-bg)}.sugg.l{background:var(--green-bg)}
.sugg b.f{color:var(--red)}.sugg b.l{color:var(--green)}
.ind label{display:flex;gap:8px;align-items:flex-start;padding:5px 0;font-size:14px;cursor:pointer}.ind .k{color:var(--muted);font-size:12px;min-width:18px}
.ind label.sug::after{content:"suggested";font-size:11px;color:var(--amber);margin-left:auto}
footer{position:fixed;bottom:0;left:0;right:0;background:var(--card);border-top:1px solid var(--border);padding:12px 20px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap;align-items:center}
footer button{padding:10px 18px;font-weight:600;cursor:pointer}.b0{background:var(--green-bg);color:var(--green);border-color:var(--green)}
.b1{background:var(--red-bg);color:var(--red);border-color:var(--red)}.cur{outline:3px solid var(--navy);outline-offset:2px}
.status{min-width:220px;font-size:13px}.err{color:var(--red);font-weight:600}h2{margin:0;font-size:21px}
a{color:var(--navy)}
</style></head><body>
<header><h1>HireGuard labelling</h1><div class="bar"><span id="prog"></span></div><span id="counts" class="muted"></span>
<select id="filter"><option value="todo">To do (unlabelled)</option><option value="all">All postings</option>
<option value="low">Low confidence</option><option value="fraud">Suggested fraudulent</option><option value="medium">Medium confidence</option>
<option value="labelled">Already labelled</option><option value="disagree">Where I disagree with the suggestion</option></select>
<span id="pos" class="muted"></span></header>
<main><section class="card" id="post"></section><aside><div class="card" id="side"></div></aside></main>
<footer><button id="prev" title="Left arrow">&larr; Prev</button><button class="b0" id="l0" title="Key 0 or L">0 &middot; Legitimate</button>
<button class="b1" id="l1" title="Key 1 or F">1 &middot; Fraudulent</button><button id="lx" title="Key X">Exclude</button>
<button id="next" title="Right arrow">Next &rarr;</button><span class="status" id="status"></span></footer>
<script>
const IND = ["Requests for financial/personal info (fees, M-Pesa, ID, bank details)","No verifiable company details",
"Unrealistic compensation","Free email provider instead of company domain","Urgency / over-promising language",
"Vague job description","Cyrillic / look-alike characters"];
const HL = /(registration fee|processing fee|application fee|training fee|fees?\b|m-?pesa|paybill|till number|send money|deposit|passport|id (?:card|number|no)|national id|bank details|kra pin|whats ?app|telegram|@(?:gmail|yahoo|hotmail|outlook)\.com|urgent(?:ly)?|guarantee[d]?|no experience|limited slots|act now|earn (?:daily|weekly)|easy money|work from home|(?:ksh?s?\.?|kes|usd|\$)\s?\d[\d,.]*k?)/gi;
let rows = [], view = [], i = 0;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const hl = s => esc(s).replace(HL, "<mark>$1</mark>");
const rank = r => ({low:0}[r.confidence] ?? (r.suggested_label==="1"?1:({medium:2}[r.confidence] ?? 3)));
const indsOf = notes => new Set(String(notes||"").replace(/^excluded\s*\|?\s*/,"").split(";")[0].split(",").map(s=>s.trim()).filter(s=>/^[1-7]$/.test(s)));
const comment = notes => String(notes||"").includes(";") ? String(notes).split(";").slice(1).join(";").trim() : "";

async function load(){ const d = await (await fetch("/api/rows")).json(); rows = d.rows;
  document.title = "HireGuard labelling"; build(); }
function build(keepRow){ const f = $("filter").value;
  view = rows.filter(r => f==="all" || (f==="todo" && r.fraudulent==="" && !/excluded/.test(r.notes)) ||
    (f==="low" && r.confidence==="low") || (f==="fraud" && r.suggested_label==="1") || (f==="medium" && r.confidence==="medium") ||
    (f==="labelled" && r.fraudulent!=="") || (f==="disagree" && r.fraudulent!=="" && r.suggested_label!=="" && r.fraudulent!==r.suggested_label))
    .sort((a,b)=>rank(a)-rank(b) || a.row-b.row);
  i = keepRow==null ? 0 : Math.max(0, view.findIndex(r=>r.row===keepRow)); render(); }
function stats(){ const done = rows.filter(r=>r.fraudulent!=="").length, ex = rows.filter(r=>r.fraudulent==="" && /excluded/.test(r.notes)).length;
  const f = rows.filter(r=>r.fraudulent==="1").length, agree = rows.filter(r=>r.fraudulent!=="" && r.fraudulent===r.suggested_label).length;
  $("prog").style.width = (100*(done+ex)/rows.length)+"%";
  $("counts").textContent = `${done+ex} / ${rows.length} done · ${f} fraudulent · ${ex} excluded` + (done?` · ${Math.round(100*agree/done)}% agree with suggestions`:""); }
function render(){ stats(); const r = view[i];
  $("pos").textContent = view.length ? `${i+1} of ${view.length} in this view` : "";
  if(!r){ $("post").innerHTML = "<h2>Nothing left in this view 🎉</h2><p class='muted'>Pick another filter above.</p>"; $("side").innerHTML=""; return; }
  const chips = [r.source, r.company_profile||"no company named", r.location, r.salary_range, r.employment_type, r.posted_date && "posted "+r.posted_date,
    r.contact_email_domain && "email: "+r.contact_email_domain].filter(Boolean).map(c=>`<span class="chip">${esc(c)}</span>`);
  if(r.is_free_email_provider==="1") chips.push('<span class="chip warn">free email provider</span>');
  if(r.short_text==="1") chips.push('<span class="chip warn">very short text</span>');
  if(+r.duplicate_count>1) chips.push(`<span class="chip">${r.duplicate_count} identical copies merged</span>`);
  const sec = (t,s)=> s ? `<h3>${t}</h3>${hl(s)}` : "";
  $("post").innerHTML = `<div class="muted">Row ${r.row}${r.url?` · <a href="${esc(r.url)}" target="_blank" rel="noopener">open original</a>`:""}</div>
    <h2>${esc(r.title)}</h2><div class="meta">${chips.join("")}</div>
    <div class="body">${sec("Description", r.description)}${sec("Requirements", r.requirements)}${sec("Benefits", r.benefits)}</div>`;
  const sugg = r.suggested_label==="" ? "" : `<div class="sugg ${r.suggested_label==="1"?"f":"l"}"><div class="muted">AI suggestion (${esc(r.confidence)} confidence)</div>
    <b class="${r.suggested_label==="1"?"f":"l"}">${r.suggested_label==="1"?"Fraudulent":"Legitimate"}</b>
    ${r.suggested_notes?` · indicators ${esc(r.suggested_notes)}`:""}<div style="margin-top:6px">${esc(r.reason)}</div></div>`;
  const mine = indsOf(r.notes), sug = indsOf(r.suggested_notes), pre = r.notes ? mine : sug;
  const current = r.fraudulent==="1" ? "Fraudulent" : r.fraudulent==="0" ? "Legitimate" : /excluded/.test(r.notes) ? "Excluded" : "not labelled yet";
  $("side").innerHTML = `${sugg}<div class="muted">Your label: <b>${current}</b></div><h3 style="margin:14px 0 4px;font-size:14px">Indicators that apply</h3>
    <div class="ind">${IND.map((t,k)=>`<label class="${!r.notes && sug.has(String(k+1))?"sug":""}"><input type="checkbox" data-k="${k+1}" ${pre.has(String(k+1))?"checked":""}>
    <span class="k">${k+1}</span><span>${t}</span></label>`).join("")}</div>
    <input type="text" id="comment" placeholder="Optional comment" style="width:100%;margin-top:10px" value="${esc(comment(r.notes))}">
    <p class="muted">Keys: 0/L legit · 1/F fraud · X exclude · ←/→ move · Shift+1–7 toggle indicator</p>`;
  $("l0").classList.toggle("cur", r.fraudulent==="0"); $("l1").classList.toggle("cur", r.fraudulent==="1"); }
function notesNow(excluded){ const ks=[...document.querySelectorAll(".ind input:checked")].map(x=>x.dataset.k).join(",");
  const c = ($("comment")?.value||"").replace(/;/g,",").trim(); let n = ks + (c?`; ${c}`:"");
  return excluded ? ("excluded" + (n?` | ${n}`:"")) : n; }
async function label(v){ const r = view[i]; if(!r) return; const excluded = v==="x";
  const body = {row:r.row, fraudulent: excluded ? "" : v, notes: notesNow(excluded)};
  $("status").textContent = "Saving…"; $("status").className="status";
  try { const res = await fetch("/api/label",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    const d = await res.json(); if(!d.ok) throw new Error(d.error);
    r.fraudulent = body.fraudulent; r.notes = body.notes; $("status").textContent = `Saved row ${r.row}`;
    const f = $("filter").value; if(f==="todo"){ view.splice(i,1); if(i>=view.length) i=view.length-1; i=Math.max(i,0); render(); } else { next(); }
  } catch(e){ $("status").textContent = e.message; $("status").className = "status err"; } }
function next(){ if(i<view.length-1){i++; render(); window.scrollTo(0,0);} }
function prev(){ if(i>0){i--; render(); window.scrollTo(0,0);} }
$("l0").onclick=()=>label("0"); $("l1").onclick=()=>label("1"); $("lx").onclick=()=>label("x");
$("next").onclick=next; $("prev").onclick=prev; $("filter").onchange=()=>build();
document.addEventListener("keydown", e => { if(e.target.tagName==="INPUT" && e.target.type==="text") return;
  if(e.shiftKey && /^Digit[1-7]$/.test(e.code)){ const cb=document.querySelector(`.ind input[data-k="${e.code.slice(5)}"]`); if(cb){cb.checked=!cb.checked;} e.preventDefault(); return; }
  const k = e.key.toLowerCase();
  if(k==="0"||k==="l") label("0"); else if(k==="1"||k==="f") label("1"); else if(k==="x") label("x");
  else if(e.key==="ArrowRight") next(); else if(e.key==="ArrowLeft") prev(); });
load();
</script></body></html>"""


def main():
    parser = argparse.ArgumentParser(description="Label HireGuard postings in your browser.")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if not args.file.exists():
        sys.exit(f"File not found: {args.file}")
    backup = args.file.with_name(f"{args.file.stem}.backup-{datetime.now():%Y%m%d-%H%M%S}.csv")
    shutil.copy2(args.file, backup)

    store = Store(args.file)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(store))
    url = f"http://127.0.0.1:{args.port}/"
    labelled = (store.df["fraudulent"] != "").sum()
    print(f"Labelling {args.file.name}: {labelled}/{len(store.df)} already labelled")
    print(f"Backup saved: {backup.name}")
    print(f"Open {url}  (Ctrl+C to stop -- every label is already saved)")
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
