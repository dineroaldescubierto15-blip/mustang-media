#!/usr/bin/env python3
"""Genera la pàgina d'enllaços de la bio (bio/index.html) a partir de bio/links.json.

El workflow .github/workflows/bio.yml l'executa i la publica a GitHub Pages cada cop que canvia bio/.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIO = ROOT / "bio"
e = html.escape

CSS = """
:root{--bg:#0b0b0c;--card:#151517;--line:#2a2a2e;--text:#f4f1ea;--muted:#9a978f;--gold:#c9a54a;--gold2:#e2c26e}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;
  -webkit-font-smoothing:antialiased;min-height:100vh}
.wrap{max-width:520px;margin:0 auto;padding:36px 16px 48px}
header{text-align:center;margin-bottom:26px}
.logo{width:92px;height:92px;border-radius:50%;margin:0 auto 14px;display:grid;place-items:center;
  background:radial-gradient(circle at 50% 40%,#232326,#0d0d0e);border:1px dashed rgba(201,165,74,.55)}
.logo span{font-family:Anton,Impact,sans-serif;color:var(--gold);letter-spacing:.14em;font-size:13px;line-height:1.15}
h1{font-family:Anton,Impact,sans-serif;font-weight:400;letter-spacing:.08em;text-transform:uppercase;font-size:30px}
.handle{color:var(--muted);font-size:14px;margin-top:4px}
.handle a{color:inherit;text-decoration:none;border-bottom:1px solid var(--line)}
.banner{border:1px solid rgba(201,165,74,.45);background:linear-gradient(135deg,rgba(201,165,74,.16),rgba(201,165,74,.03));
  border-radius:16px;padding:18px 18px 16px;margin-bottom:28px;text-align:center}
.kicker{font-family:Anton,Impact,sans-serif;color:var(--gold2);text-transform:uppercase;letter-spacing:.12em;font-size:26px}
.banner p{color:#d9d5cb;font-size:14px;line-height:1.45;margin-top:6px}
section{margin-bottom:26px}
h2{font-size:12px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--gold);margin:0 4px 4px}
.note{color:var(--muted);font-size:13px;margin:0 4px 10px}
a.store{display:flex;align-items:center;gap:12px;text-decoration:none;color:var(--text);background:var(--card);
  border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:8px;transition:border-color .15s,transform .15s}
a.store:hover,a.store:focus-visible{border-color:var(--gold);transform:translateY(-1px);outline:none}
.store .t{flex:1;min-width:0}
.store b{display:block;font-size:16px;font-weight:700}
.store small{display:block;color:var(--muted);font-size:13px;margin-top:2px}
.store i{font-style:normal;color:var(--gold);font-size:18px}
.ig{display:block;text-align:center;text-decoration:none;color:#0b0b0c;background:var(--gold);font-weight:700;
  border-radius:999px;padding:13px 16px;margin:6px 0 26px}
footer{color:var(--muted);font-size:12px;line-height:1.5;text-align:center;border-top:1px solid var(--line);padding-top:18px}
"""


def build() -> str:
    d = json.loads((BIO / "links.json").read_text())
    out = []
    b = d.get("banner") or {}
    if b.get("active"):
        out.append(f'<div class="banner"><div class="kicker">{e(b["kicker"])}</div><p>{e(b["text"])}</p></div>')
    for s in d["sections"]:
        rows = "".join(
            f'<a class="store" href="{e(x["url"])}" target="_blank" rel="noopener sponsored">'
            f'<span class="t"><b>{e(x["name"])}</b><small>{e(x["tag"])}</small></span><i>&rarr;</i></a>'
            for x in s["stores"])
        note = f'<p class="note">{e(s["note"])}</p>' if s.get("note") else ""
        out.append(f'<section><h2>{e(s["name"])}</h2>{note}{rows}</section>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(d["title"])} | Deals &amp; gear</title>
<meta name="description" content="Mustang parts, lights, detailing and gifts picked by {e(d['handle'])}.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@400;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body><main class="wrap">
<header><div class="logo"><span>MUSTANG<br>EMOTION</span></div><h1>{e(d["title"])}</h1>
<p class="handle"><a href="{e(d["instagram"])}">{e(d["handle"])}</a> &middot; Mustang deals &amp; gear</p></header>
{''.join(out)}
<a class="ig" href="{e(d["instagram"])}">Follow {e(d["handle"])} on Instagram</a>
<footer>Some links on this page are affiliate links: if you buy through them we may earn a commission, at no extra cost to you.
Mustang Emotion is a fan page and is not affiliated with Ford Motor Company.</footer>
</main></body></html>
"""


if __name__ == "__main__":
    (BIO / "index.html").write_text(build())
    print("bio/index.html generat")
