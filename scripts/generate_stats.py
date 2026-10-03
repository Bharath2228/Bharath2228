#!/usr/bin/env python3
"""Generate an SVG card of language usage across a user's public, non-fork repos.

Env:
  GH_USERNAME   GitHub username (default: Bharath2228)
  GITHUB_TOKEN  token for API calls (provided automatically in GitHub Actions)
  MOCK=1        use fake data (for local testing without network)
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from html import escape

USERNAME = os.environ.get("GH_USERNAME", "Bharath2228")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("OUT", "assets/lang-stats.svg")
TOP_N = 8
EXCLUDE = {"Jupyter Notebook"}  # notebooks skew byte counts; remove to include

COLORS = {
    "Python": "#3776AB", "C": "#7A8CA5", "C++": "#F34B7D", "JavaScript": "#F1E05A",
    "TypeScript": "#3178C6", "MATLAB": "#E16737", "Shell": "#89E051", "HTML": "#E34C26",
    "CSS": "#8A63D2", "SCSS": "#C6538C", "Java": "#B07219", "Go": "#00ADD8",
    "Rust": "#DEA584", "PLpgSQL": "#336790", "TSQL": "#E38C00", "Dockerfile": "#384D54",
    "Kotlin": "#A97BFF", "Jupyter Notebook": "#DA5B0B",
}
DEFAULT_COLOR = "#8B949E"


def api(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "lang-stats-generator",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_totals():
    if os.environ.get("MOCK"):
        return {"Python": 420000, "C++": 90000, "JavaScript": 70000, "C": 50000,
                "MATLAB": 30000, "Shell": 12000, "HTML": 9000, "CSS": 6000, "SCSS": 2000}
    totals = {}
    page = 1
    while True:
        repos = api(f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}&type=owner")
        if not repos:
            break
        for repo in repos:
            if repo.get("fork"):
                continue
            for lang, n in api(repo["languages_url"]).items():
                totals[lang] = totals.get(lang, 0) + n
        if len(repos) < 100:
            break
        page += 1
    return totals


def build_svg(totals):
    items = {k: v for k, v in totals.items() if k not in EXCLUDE}
    total = sum(items.values()) or 1
    ranked = sorted(items.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[:TOP_N]
    rest = sum(v for _, v in ranked[TOP_N:])
    if rest:
        top.append(("Other", rest))

    w, pad = 495, 24
    bar_w = w - pad * 2
    row_h = 30
    h = 92 + row_h * len(top) + 16

    # Stacked overview bar
    segs, x = [], pad
    for i, (lang, v) in enumerate(top):
        seg = bar_w * v / total
        c = COLORS.get(lang, DEFAULT_COLOR)
        segs.append(f'<rect x="{x:.1f}" y="52" width="{max(seg,1):.1f}" height="10" fill="{c}"/>')
        x += seg

    rows = []
    for i, (lang, v) in enumerate(top):
        y = 92 + i * row_h
        pct = 100 * v / total
        c = COLORS.get(lang, DEFAULT_COLOR)
        delay = i * 0.08
        rows.append(f'''
  <g style="animation: fade .5s ease-out {delay:.2f}s both">
    <circle cx="{pad+5}" cy="{y}" r="5" fill="{c}"/>
    <text x="{pad+18}" y="{y+4}" class="lang">{escape(lang)}</text>
    <text x="{w-pad}" y="{y+4}" class="pct" text-anchor="end">{pct:.1f}%</text>
    <rect x="{pad+150}" y="{y-3}" width="{bar_w-150-60}" height="6" rx="3" fill="#21262d"/>
    <rect x="{pad+150}" y="{y-3}" width="{(bar_w-150-60)*pct/100:.1f}" height="6" rx="3" fill="{c}"/>
  </g>''')

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Most used languages">
  <style>
    .title {{ font: 600 16px 'Segoe UI', Ubuntu, sans-serif; fill: #58a6ff; }}
    .lang  {{ font: 400 13px 'Segoe UI', Ubuntu, sans-serif; fill: #c9d1d9; }}
    .pct   {{ font: 400 12px 'Segoe UI', Ubuntu, sans-serif; fill: #8b949e; }}
    .meta  {{ font: 400 10px 'Segoe UI', Ubuntu, sans-serif; fill: #6e7681; }}
    @keyframes fade {{ from {{ opacity: 0; transform: translateX(-6px); }} to {{ opacity: 1; transform: none; }} }}
  </style>
  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="10" fill="#0d1117" stroke="#30363d"/>
  <text x="{pad}" y="34" class="title">Most Used Languages</text>
  <clipPath id="bar"><rect x="{pad}" y="52" width="{bar_w}" height="10" rx="5"/></clipPath>
  <g clip-path="url(#bar)">{''.join(segs)}</g>{''.join(rows)}
  <text x="{w-pad}" y="{h-10}" class="meta" text-anchor="end">Auto-updated {stamp} · by repo bytes, forks excluded</text>
</svg>
'''


def main():
    try:
        totals = fetch_totals()
    except Exception as e:  # keep the previous card if the API is unavailable
        print(f"Fetch failed, leaving existing card untouched: {e}", file=sys.stderr)
        sys.exit(0)
    if not totals:
        print("No language data found; leaving existing card untouched.", file=sys.stderr)
        sys.exit(0)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build_svg(totals))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
