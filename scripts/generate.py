#!/usr/bin/env python3
"""Generate the neon stats dashboard SVG for the profile README.

Uses only the standard library. Needs a token in GH_TOKEN / GITHUB_TOKEN
(a PAT with read:user lets private contributions count too).
"""
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request
from collections import defaultdict
from html import escape
from pathlib import Path

USER = os.environ.get("GH_USER", "nik12mcf")
OUT = Path(__file__).resolve().parent.parent / "assets" / "dashboard.svg"

PINK = "#ff2bd6"
CYAN = "#00f0ff"
YELLOW = "#ffe45e"
TEXT = "#e6e6ff"
MUTED = "#9a8cc2"
SANS = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"


def token():
    t = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if t:
        return t
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def gql(query, **variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token()}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if body.get("errors"):
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]


def fetch():
    meta = gql(
        """query($login:String!){user(login:$login){
          createdAt
          contributionsCollection{contributionYears}
          repositories(ownerAffiliations:OWNER,isFork:false,first:100){
            totalCount
            nodes{stargazerCount languages(first:10,orderBy:{field:SIZE,direction:DESC}){
              edges{size node{name color}}}}}}}""",
        login=USER,
    )["user"]

    days = {}
    for year in meta["contributionsCollection"]["contributionYears"]:
        cal = gql(
            """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
              contributionsCollection(from:$from,to:$to){contributionCalendar{
                weeks{contributionDays{date contributionCount}}}}}}""",
            login=USER,
            **{"from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"},
        )["user"]["contributionsCollection"]["contributionCalendar"]
        for w in cal["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]

    langs = defaultdict(lambda: [0, "#888"])
    stars = 0
    for repo in meta["repositories"]["nodes"]:
        stars += repo["stargazerCount"]
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]][0] += e["size"]
            langs[e["node"]["name"]][1] = e["node"]["color"] or "#888"

    return meta, days, langs, stars


def streaks(days):
    today = dt.date.today()
    dates = sorted(dt.date.fromisoformat(d) for d in days if dt.date.fromisoformat(d) <= today)
    longest, run, run_start, best = 0, 0, None, (None, None)
    prev = None
    for d in dates:
        if days[d.isoformat()] > 0:
            if prev and (d - prev).days == 1 and run:
                run += 1
            else:
                run, run_start = 1, d
            if run > longest:
                longest, best = run, (run_start, d)
        else:
            run = 0
        prev = d

    # current streak: today may still be empty without breaking it
    cur, d = 0, today
    if days.get(d.isoformat(), 0) == 0:
        d -= dt.timedelta(days=1)
    start = d
    while days.get(d.isoformat(), 0) > 0:
        cur += 1
        start = d
        d -= dt.timedelta(days=1)
    return cur, start, longest, best


def fmt_date(d, year=False):
    return d.strftime("%b %-d, %Y" if year else "%b %-d") if d else "—"


def tile(x, y, w, value, label, sub, color, delay):
    return f"""
  <g class="rise" style="animation-delay:{delay}s">
    <rect x="{x}" y="{y}" width="{w}" height="104" rx="10" fill="#140a2a" stroke="{color}" stroke-opacity=".45"/>
    <text x="{x + w / 2}" y="{y + 46}" text-anchor="middle" font-family="{SANS}" font-weight="800" font-size="32" fill="{color}" filter="url(#g)">{escape(value)}</text>
    <text x="{x + w / 2}" y="{y + 72}" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{TEXT}" letter-spacing="1.5">{escape(label)}</text>
    <text x="{x + w / 2}" y="{y + 91}" text-anchor="middle" font-family="{MONO}" font-size="11" fill="{MUTED}">{escape(sub)}</text>
  </g>"""


def render(meta, days, langs, stars):
    today = dt.date.today()
    total = sum(days.values())
    cur, cur_start, longest, (ls, le) = streaks(days)
    first_day = dt.date.fromisoformat(meta["createdAt"][:10])

    year_ago = today - dt.timedelta(days=364)
    year_total = sum(v for k, v in days.items() if year_ago <= dt.date.fromisoformat(k) <= today)

    W = 840
    parts = []
    tw, gap, x0 = 189, 14, 24
    tiles = [
        (f"{total:,}", "CONTRIBUTIONS", f"since {fmt_date(first_day, True)}", PINK),
        (f"{year_total:,}", "LAST 365 DAYS", f"{year_total / 52:.0f} / week avg", CYAN),
        (f"{cur}", "CURRENT STREAK", f"{fmt_date(cur_start)} – now" if cur else "start one today", YELLOW),
        (f"{longest}", "LONGEST STREAK", f"{fmt_date(ls)} – {fmt_date(le)}", PINK),
    ]
    for i, (v, l, s, c) in enumerate(tiles):
        parts.append(tile(x0 + i * (tw + gap), 64, tw, v, l, s, c, 0.1 * i))

    # weekly contributions over the last year
    start = year_ago - dt.timedelta(days=(year_ago.weekday() + 1) % 7)  # align to Sunday
    weeks = []
    d = start
    while d <= today:
        weeks.append(sum(days.get((d + dt.timedelta(days=i)).isoformat(), 0) for i in range(7)))
        d += dt.timedelta(days=7)
    peak = max(weeks) or 1
    cx, cy, cw, ch = 24, 214, 792, 120
    bw = cw / len(weeks)
    bars = []
    for i, n in enumerate(weeks):
        h = max(2, n / peak * ch)
        bars.append(
            f'<rect class="bar" x="{cx + i * bw + 1.5:.1f}" y="{cy + ch - h:.1f}" width="{bw - 3:.1f}" '
            f'height="{h:.1f}" rx="2" fill="url(#barG)" style="animation-delay:{0.3 + i * 0.018:.2f}s">'
            f"<title>{n} contributions</title></rect>"
        )
    month_labels = []
    seen = set()
    for i in range(len(weeks)):
        wd = start + dt.timedelta(days=7 * i)
        if wd.day <= 7 and (wd.year, wd.month) not in seen:
            seen.add((wd.year, wd.month))
            month_labels.append(
                f'<text x="{cx + i * bw:.1f}" y="{cy + ch + 18}" font-family="{MONO}" font-size="10" fill="{MUTED}">{wd.strftime("%b")}</text>'
            )

    # languages
    ranked = sorted(langs.items(), key=lambda kv: -kv[1][0])[:6]
    lang_total = sum(v[0] for _, v in ranked) or 1
    ly = 392
    seg_x = 24.0
    segs, legend = [], []
    for i, (name, (size, color)) in enumerate(ranked):
        pct = size / lang_total
        w = pct * 792
        segs.append(f'<rect x="{seg_x:.1f}" y="{ly}" width="{w:.1f}" height="12" fill="{color}"/>')
        seg_x += w
        lx = 24 + (i % 3) * 264
        lyy = ly + 38 + (i // 3) * 22
        legend.append(
            f'<circle cx="{lx + 6}" cy="{lyy - 4}" r="5" fill="{color}"/>'
            f'<text x="{lx + 18}" y="{lyy}" font-family="{MONO}" font-size="12" fill="{TEXT}">{escape(name)} '
            f'<tspan fill="{MUTED}">{pct * 100:.1f}%</tspan></text>'
        )

    H = 470
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0b0418"/><stop offset="1" stop-color="#170830"/>
    </linearGradient>
    <linearGradient id="barG" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0" stop-color="{PINK}"/><stop offset="1" stop-color="{CYAN}"/>
    </linearGradient>
    <filter id="g" x="-30%" y="-60%" width="160%" height="220%">
      <feGaussianBlur stdDeviation="4" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <clipPath id="langClip"><rect x="24" y="{ly}" width="792" height="12" rx="6"/></clipPath>
  </defs>
  <style>
    .rise {{ animation: rise .7s ease-out both; }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(12px) }} to {{ opacity: 1; transform: none }} }}
    .bar {{ transform-box: fill-box; transform-origin: bottom; animation: grow .8s cubic-bezier(.2,.8,.2,1) both; }}
    @keyframes grow {{ from {{ transform: scaleY(0) }} to {{ transform: scaleY(1) }} }}
    .h {{ font: 700 13px {MONO}; fill: {CYAN}; letter-spacing: 3px; }}
    @media (prefers-reduced-motion: reduce) {{ .rise, .bar {{ animation: none; }} }}
  </style>

  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="url(#bg)" stroke="{PINK}" stroke-opacity=".35" stroke-width="2"/>
  <text class="h" x="24" y="40">// STATS</text>
  <text x="{W - 24}" y="40" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">{meta["repositories"]["totalCount"]} repos · {stars} ★ · updated {today.strftime("%b %-d, %Y")}</text>
  {"".join(parts)}

  <text class="h" x="24" y="200">// LAST 12 MONTHS</text>
  <text x="{W - 24}" y="200" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">peak week: {peak}</text>
  <line x1="24" x2="816" y1="{cy + ch + 0.5}" y2="{cy + ch + 0.5}" stroke="{MUTED}" stroke-opacity=".3"/>
  {"".join(bars)}
  {"".join(month_labels)}

  <text class="h" x="24" y="{ly - 14}">// LANGUAGES</text>
  <g clip-path="url(#langClip)" class="rise" style="animation-delay:.6s">{"".join(segs)}</g>
  {"".join(legend)}
</svg>
"""


def main():
    meta, days, langs, stars = fetch()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(meta, days, langs, stars))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
