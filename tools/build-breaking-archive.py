#!/usr/bin/env python3
"""Regenerate breaking/index.html (the Breaking News archive) from
tools/breaking-news.json (Pepe, Nov 13, 2026).

The page shell (head, styles, masthead, sticky nav, footer, analytics
beacon) is inherited from archive.html — the same inherit-the-shell
pattern build-lesson.py uses with the newest post. Local links are
rewritten one level up (../) because the page lives in breaking/.

Registry format (tools/breaking-news.json), newest first:
{"items": [{"date": "2026-11-13", "date_label": "Friday, November 13, 2026",
            "headline": "...", "summary": "...", "live": true,
            "links": [{"label": "...", "href": "https://..."},
                      {"label": "Background: ...", "href": "posts/...",
                       "site": true}]}]}
"site": true links are dtbrief-internal and render relative (../) with
no target=_blank. At most one item should carry "live": true — the one
currently on the homepage card.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, "tools", "breaking-news.json")


def _load_topnav():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "set_topnav", os.path.join(ROOT, "tools", "set-topnav.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TOPNAV = _load_topnav()
SHELL_SRC = os.path.join(ROOT, "archive.html")
OUT_DIR = os.path.join(ROOT, "breaking")
OUT = os.path.join(OUT_DIR, "index.html")

EXTRA_CSS = """
      .bn-item {
        border: 1px solid var(--rule);
        border-left: 4px solid #FF5A3C;
        background: var(--card);
        border-radius: 14px;
        padding: 18px 20px;
        margin: 0 0 16px;
      }
      .bn-meta {
        display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center;
        font-family: "IBM Plex Mono", monospace;
        font-size: 11px; letter-spacing: .14em; text-transform: uppercase;
      }
      .bn-kicker { color: #FF5A3C; font-weight: 600; }
      .bn-date { color: var(--ink-faint); }
      .bn-live {
        background: #FF5A3C; color: #fff; padding: 2px 8px;
        border-radius: 999px; letter-spacing: .08em; font-weight: 600;
      }
      .bn-item h2 {
        font-family: "Sora", sans-serif; font-size: 24px;
        line-height: 1.25; margin: 10px 0 8px;
      }
      .bn-item p { color: var(--ink-soft); line-height: 1.6; margin: 0 0 12px; }
      .bn-links { display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 14px; }
      .bn-links a { color: var(--accent); font-weight: 600; text-decoration: none; }
"""

BAND = """
        <div style="margin:28px 0 8px;padding:22px 20px;background:#EDF1F8;border:1px solid #D8DEE7;border-radius:14px;">
          <div style="font-family:'Sora',sans-serif;font-weight:700;font-size:19px;color:#0A0F1E;">Get the Daily Tech Briefing in your inbox</div>
          <p style="margin:6px 0 14px;color:#2E3A52;font-size:15px;line-height:1.5;">The day's top tech stories in plain English &mdash; every weekday morning. Free.</p>
          <a href="https://franciscos-newsletter-df7908.beehiiv.com/subscribe" target="_blank" rel="noopener" style="display:block;text-align:center;background:#0A0F1E;color:#FFFFFF;font-family:'Sora',sans-serif;font-weight:700;font-size:16px;padding:13px 16px;border-radius:999px;text-decoration:none;">Subscribe</a>
        </div>
"""


def up(href):
    """Rewrite a root-relative local href for the breaking/ subfolder."""
    return "../" + href


def main():
    data = json.load(open(REGISTRY, encoding="utf-8"))
    items = data["items"]
    shell = open(SHELL_SRC, encoding="utf-8").read()

    # --- top shell: everything through <div class="wrap"> ---
    marker = '    <div class="wrap">'
    assert marker in shell, "wrap marker not found in archive.html shell"
    top = shell.split(marker, 1)[0] + marker + "\n"

    # Breaking-specific head metadata (exact-string swaps; fail loudly).
    swaps = [
        ("Archive — Daily Tech Briefing", "Breaking News — Daily Tech Briefing"),
        ('content="Every story from every Daily Tech Briefing, newest first — each linked to the original reporting."',
         'content="Every story that earned the Breaking News card on dtbrief.com — newest first, with the original sources."'),
        ('content="https://dtbrief.com/archive.html"', 'content="https://dtbrief.com/breaking/"'),
        ("<strong>Archive</strong>", "<strong>Breaking News</strong>"),
        ("Every story, newest first", "The stories that earned the red card"),
    ]
    for old, new in swaps:
        assert old in top, "shell anchor missing: %r" % old
        top = top.replace(old, new)

    # Local links outside the header block, one level up: the head favicon
    # and the masthead brand. (The old blanket nav-href rewrite is gone.)
    for old, new in (('href="favicon.svg"', 'href="../favicon.svg"'),
                     ('<a class="brand" href="index.html"',
                      '<a class="brand" href="../index.html"')):
        assert old in top, "shell anchor missing: %s" % old
        top = top.replace(old, new)

    # Header: regenerate the set-topnav.py block for this depth, with
    # Breaking as the active item (Pepe promoted Breaking into the menu
    # Nov 14, 2026).
    top = TOPNAV.apply_to_html(top, "../", "breaking")

    # Page-specific styles, appended to the shell's style block.
    assert "</style>" in top
    top = top.replace("</style>", EXTRA_CSS + "    </style>", 1)

    # --- entries ---
    parts = [top]
    parts.append('      <article>\n')
    parts.append('        <div class="dateline-row">\n'
                 '          <span class="kicker" style="color:#FF5A3C;">Breaking News</span>\n'
                 '        </div>\n')
    parts.append('        <h1>Breaking news, <span class="money">as it happened.</span></h1>\n')
    parts.append('        <p class="deck">Every story that earned the red Breaking News card on the '
                 'homepage &mdash; newest first, each with its original sources. A story stays on the '
                 'homepage only while it is still developing; this page is its permanent record.</p>\n')
    n = len(items)
    parts.append('        <div class="byline">\n'
                 '          <span class="who">Daily Tech Briefing</span>\n'
                 '          <span class="dot" aria-hidden="true"></span>\n'
                 '          <span>%d %s</span>\n'
                 '        </div>\n' % (n, "story" if n == 1 else "stories"))
    for it in items:
        live = ' <span class="bn-live">Live now</span>' if it.get("live") else ""
        links = []
        for ln in it["links"]:
            href = ln["href"]
            if ln.get("site"):
                links.append('<a href="%s">%s</a>' % (up(href), html.escape(ln["label"])))
            else:
                links.append('<a href="%s" target="_blank" rel="noopener">%s</a>'
                             % (html.escape(href, quote=True), html.escape(ln["label"])))
        parts.append(
            '        <section class="bn-item">\n'
            '          <div class="bn-meta"><span class="bn-kicker">Breaking News</span>'
            '<span class="bn-date">%s</span>%s</div>\n'
            '          <h2>%s</h2>\n'
            '          <p>%s</p>\n'
            '          <div class="bn-links">%s</div>\n'
            '        </section>\n'
            % (html.escape(it["date_label"]), live,
               html.escape(it["headline"]), html.escape(it["summary"]),
               "".join(links)))
    parts.append(BAND)
    parts.append('      </article>\n    </div>\n\n')

    # --- footer + scripts + beacon, from the shell's tail ---
    # The shared footer is the add-footer.py block (Nov 14, 2026); the old
    # bare "    <footer>" marker and the "All posts" span are gone.
    fmark = "    <!-- site-footer -->"
    assert fmark in shell, "site footer not found in archive.html shell"
    tail = shell.split(fmark, 1)[1]
    tail = fmark + tail
    # Every local href in the footer block goes one level up.
    tail = re.sub(r'href="(?!https?:|//|#|mailto:)([^"]+)"',
                  r'href="../\1"', tail)
    # The header carries search now; drop the archive page's search script.
    tail = tail.replace('  <script src="search.js" defer></script>\n', "")
    parts.append(tail)

    page = "".join(parts)
    assert "cloudflareinsights" in page, "analytics beacon missing"
    assert page.count('class="bn-item"') == n
    os.makedirs(OUT_DIR, exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(page)
    print("breaking/index.html written: %d items, %d bytes" % (n, len(page)))


if __name__ == "__main__":
    sys.exit(main())
