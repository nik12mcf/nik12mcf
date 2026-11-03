#!/usr/bin/env python3
"""Build the static Vice City assets: section titles and the tech stack card.

Run once after editing STACK or TITLES; the output is committed. Icons come
from skillicons.dev and are embedded as data URIs (GitHub won't load external
images from inside an SVG).
"""
import base64
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

STACK = [
    ("LANGUAGES", PINK, [("ts", "TypeScript"), ("js", "JavaScript"), ("python", "Python"),
                         ("java", "Java"), ("cpp", "C++"), ("html", "HTML"), ("css", "CSS")]),
    ("FRAMEWORKS", CYAN, [("react", "React"), ("nextjs", "Next.js"), ("threejs", "Three.js"),
                          ("tailwind", "Tailwind")]),
    ("TOOLS", ORANGE, [("docker", "Docker"), ("vercel", "Vercel"), ("git", "Git")]),
]

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


def icon(slug):
    req = urllib.request.Request(f"https://skillicons.dev/icons?i={slug}", headers={"User-Agent": "profile-builder"})
    with urllib.request.urlopen(req) as r:
        return "data:image/svg+xml;base64," + base64.b64encode(r.read()).decode()


def stack():
    W, pad, chip_h, gap, icon_s = 840, 24, 42, 10, 26
    rows, y = [], 34
    for label, color, items in STACK:
        rows.append(f'<text x="{pad}" y="{y}" font-family="{MONO}" font-weight="700" font-size="12" '
                    f'letter-spacing="3" fill="{color}">// {label}</text>')
        y += 14
        x = pad
        for slug, name in items:
            w = 8 + icon_s + 9 + len(name) * 7.4 + 12
            if x + w > W - pad:
                x, y = pad, y + chip_h + gap
            rows.append(f"""<g>
    <rect x="{x}" y="{y}" width="{w:.0f}" height="{chip_h}" rx="10" fill="#1d0838" fill-opacity=".9" stroke="{color}" stroke-opacity=".55"/>
    <image x="{x + 8}" y="{y + (chip_h - icon_s) / 2}" width="{icon_s}" height="{icon_s}" href="{icon(slug)}"/>
    <text x="{x + 8 + icon_s + 9}" y="{y + chip_h / 2 + 5}" font-family="{SANS}" font-weight="600" font-size="13" fill="{TEXT}">{escape(name)}</text>
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
    (ASSETS / "stack.svg").write_text(stack())
    print(f"wrote titles + stack to {ASSETS}")


if __name__ == "__main__":
    main()
