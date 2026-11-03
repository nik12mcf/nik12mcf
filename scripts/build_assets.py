#!/usr/bin/env python3
"""Build the static Vice City assets: section titles and the tech stack card.

Run after editing STACK/TITLES or re-running scan_usage.py; the output is
committed. Percentages come from assets/usage.json. Icons come from
skillicons.dev / simpleicons.org and are embedded as data URIs (GitHub won't
load external images from inside an SVG).
"""
import base64
import json
import urllib.request
from html import escape
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

PINK = "#ff2bd6"
CYAN = "#00f0ff"
ORANGE = "#ff9a3d"
TEXT = "#e6e6ff"
MUTED = "#9a8cc2"
SCRIPT = "'Brush Script MT', 'Segoe Script', 'Snell Roundhand', cursive"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"
SANS = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"

TITLES = {"stack": "Tech Stack", "stats": "Stats", "building": "Building"}

GCP_BLUE = "#4285F4"

# (label, color, usage.json section, [(icon, name, usage key)]); items sort by usage
STACK = [
    ("LANGUAGES", PINK, "languages", [
        ("skill:python", "Python", "Python"), ("skill:go", "Go", "Go"),
        ("skill:ts", "TypeScript", "TypeScript"), ("skill:js", "JavaScript", "JavaScript"),
        ("skill:html", "HTML", "HTML"), ("skill:css", "CSS", "CSS"), ("skill:cpp", "C++", "C++")]),
    ("FRAMEWORKS", CYAN, "repo_share", [
        ("skill:react", "React", "react"), ("skill:nextjs", "Next.js", "nextjs"),
        ("skill:threejs", "Three.js", "threejs"), ("skill:tailwind", "Tailwind", "tailwind")]),
    ("GOOGLE CLOUD", "#7fb2ff", "repo_share", [
        ("si:googlebigquery", "BigQuery", "bigquery"), ("si:googlecloudstorage", "Cloud Storage", "gcs"),
        ("si:googlecloud", "Cloud Run", "cloudrun"), ("si:googlecloudcomposer", "Cloud Composer", "composer"),
        ("si:googlecloud", "Cloud Functions", "functions"), ("si:googlecloud", "Dataflow", "dataflow"),
        ("si:googlecloud", "API Gateway", "apigateway"), ("si:googlecloud", "Artifact Registry", "artifactregistry"),
        ("si:googlecloud", "Secret Manager", "secretmanager")]),
    ("TOOLS", ORANGE, "repo_share", [
        ("skill:docker", "Docker", "docker"), ("skill:vercel", "Vercel", "vercel"), ("skill:git", "Git", "git")]),
]
HINTS = {"languages": "share of code", "repo_share": "share of repos"}

GLOW = """<filter id="glow" x="-20%" y="-60%" width="140%" height="220%">
      <feGaussianBlur stdDeviation="4" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>"""


def title(text):
    W, H = 840, 84
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="l" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset="1" stop-color="{CYAN}"/>
    </linearGradient>
    <linearGradient id="r" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{ORANGE}"/><stop offset="1" stop-color="{ORANGE}" stop-opacity="0"/>
    </linearGradient>
    {GLOW}
  </defs>
  <style>
    .flicker {{ animation: fl 7s linear infinite; }}
    @keyframes fl {{ 0%,40%,44%,100% {{ opacity: 1 }} 42% {{ opacity: .55 }} }}
    @media (prefers-reduced-motion: reduce) {{ .flicker {{ animation: none; }} }}
  </style>
  <rect x="120" y="{H / 2}" width="190" height="2" rx="1" fill="url(#l)" filter="url(#glow)"/>
  <rect x="530" y="{H / 2}" width="190" height="2" rx="1" fill="url(#r)" filter="url(#glow)"/>
  <g class="flicker" text-anchor="middle" font-family="{SCRIPT}" font-style="italic" font-size="52">
    <text x="420" y="{H / 2 + 16}" fill="{PINK}" filter="url(#glow)" opacity=".75">{escape(text)}</text>
    <text x="420" y="{H / 2 + 16}" fill="#ff6be3" stroke="#3a0645" stroke-width="1.5" paint-order="stroke">{escape(text)}</text>
  </g>
</svg>
"""


def icon(spec):
    kind, slug = spec.split(":")
    url = (f"https://skillicons.dev/icons?i={slug}" if kind == "skill"
           else f"https://cdn.simpleicons.org/{slug}/{GCP_BLUE[1:]}")
    req = urllib.request.Request(url, headers={"User-Agent": "profile-builder"})
    with urllib.request.urlopen(req) as r:
        return "data:image/svg+xml;base64," + base64.b64encode(r.read()).decode()


def icon_tile(spec, x, y, s):
    """skillicons come as tiles already; simple icons get a matching dark tile."""
    if spec.startswith("skill:"):
        return f'<image x="{x}" y="{y}" width="{s}" height="{s}" href="{icon(spec)}"/>'
    inset = s * .2
    return (f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="{s * .23:.1f}" fill="#242938"/>'
            f'<image x="{x + inset}" y="{y + inset}" width="{s - 2 * inset}" height="{s - 2 * inset}" href="{icon(spec)}"/>')


def pct_label(v):
    return f"{v:.0f}%" if v >= 1 else "<1%"


def stack(usage):
    W, pad, chip_h, gap, icon_s = 840, 24, 42, 10, 26
    rows, y = [], 34
    for label, color, section, items in STACK:
        rows.append(f'<text x="{pad}" y="{y}" font-family="{MONO}" font-weight="700" font-size="12" '
                    f'letter-spacing="3" fill="{color}">// {label} <tspan fill="{MUTED}" font-weight="400" '
                    f'letter-spacing="1">· {HINTS[section]}</tspan></text>')
        y += 14
        x = pad
        for spec, name, key in sorted(items, key=lambda i: -usage[section].get(i[2], 0)):
            v = usage[section].get(key, 0)
            pct = pct_label(v)
            name_w = len(name) * 7.4
            w = 8 + icon_s + 9 + name_w + 7 + len(pct) * 7.6 + 12
            if x + w > W - pad:
                x, y = pad, y + chip_h + gap
            bar = max(4, (w - 20) * min(v, 100) / 100)
            rows.append(f"""<g>
    <rect x="{x}" y="{y}" width="{w:.0f}" height="{chip_h}" rx="10" fill="#1d0838" fill-opacity=".9" stroke="{color}" stroke-opacity=".55"/>
    {icon_tile(spec, x + 8, y + (chip_h - icon_s) / 2, icon_s)}
    <text x="{x + 8 + icon_s + 9}" y="{y + chip_h / 2 + 5}" font-family="{SANS}" font-weight="600" font-size="13" fill="{TEXT}">{escape(name)}<tspan dx="7" font-family="{MONO}" font-weight="700" fill="{color}">{escape(pct)}</tspan></text>
    <rect x="{x + 10}" y="{y + chip_h - 5}" width="{bar:.1f}" height="2" rx="1" fill="{color}" opacity=".7"/>
  </g>""")
            x += w + gap
        y += chip_h + 30
    H = y - 6
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#140630"/><stop offset=".7" stop-color="#2a0b47"/><stop offset="1" stop-color="#5a1660"/>
    </linearGradient>
    <linearGradient id="dusk" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{CYAN}"/><stop offset=".5" stop-color="{PINK}"/><stop offset="1" stop-color="{ORANGE}"/>
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="url(#bg)" stroke="{PINK}" stroke-opacity=".35" stroke-width="2"/>
  <rect x="24" y="{H - 6}" width="{W - 48}" height="3" rx="1.5" fill="url(#dusk)" opacity=".8"/>
  {"".join(rows)}
</svg>
"""


def main():
    for key, text in TITLES.items():
        (ASSETS / f"title-{key}.svg").write_text(title(text))
    usage = json.loads((ASSETS / "usage.json").read_text())
    (ASSETS / "stack.svg").write_text(stack(usage))
    print(f"wrote titles + stack to {ASSETS}")


if __name__ == "__main__":
    main()
