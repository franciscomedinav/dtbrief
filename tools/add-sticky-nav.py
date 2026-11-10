#!/usr/bin/env python3
"""Add the sticky section nav (Top Stories / Latest / Learn / Listen) to every
dtbrief.com page. The nav sits directly after </header> as its own sticky bar
(only the slim nav sticks, not the whole masthead), with the active section
underlined in Signal blue. Mobile: the row scrolls horizontally, no hamburger.
Run once from ~/workspace/dtbrief-blog.
"""
import glob
import re
import sys

BASE = "/home/hatch/workspace/dtbrief-blog"
SHOW_URL = "https://open.spotify.com/show/2ssu27PcFaDaeQkVqPz9ls"

NAV_CSS = """
      /* ---------- Sticky section nav ---------- */
      .topnav { position: sticky; top: 0; z-index: 40; background: var(--paper); border-bottom: 1px solid var(--rule); }
      .topnav-inner { max-width: 1080px; margin: 0 auto; padding: 0 24px; display: flex; gap: 2px; }
      .topnav a { font-family: "IBM Plex Mono", monospace; font-size: 13px; font-weight: 600; color: var(--ink-soft); text-decoration: none; padding: 10px 12px 9px; border-bottom: 2px solid transparent; }
      .topnav a:hover { color: var(--ink); }
      .topnav a.active { color: var(--accent); border-bottom-color: var(--accent); }
      @media (max-width: 620px) {
        .topnav-inner { overflow-x: auto; scrollbar-width: none; }
        .topnav-inner::-webkit-scrollbar { display: none; }
        .topnav a { flex: none; }
      }
"""


def nav_html(prefix, active):
    """prefix: '' for root pages, '../' for posts/ and learn/ pages.
    active: 'top' | 'latest' | 'learn'."""
    learn_href = "index.html" if active == "learn" else prefix + "learn/"
    links = [
        (prefix + "index.html", "top", "Top Stories"),
        (prefix + "archive.html", "latest", "Latest"),
        (learn_href, "learn", "Learn"),
        (SHOW_URL, "listen", "Listen"),
    ]
    out = ['    <nav class="topnav" aria-label="Sections">',
           '      <div class="topnav-inner">']
    for href, key, label in links:
        cls = ' class="active"' if key == active else ""
        extra = (' target="_blank" rel="noopener"' if key == "listen" else "")
        out.append('        <a href="%s" data-nav="%s"%s%s>%s</a>'
                   % (href, key, cls, extra, label))
    out.append('      </div>')
    out.append('    </nav>')
    return "\n".join(out)


def sub_once(html, pattern, repl, name, path):
    new, n = re.subn(pattern, repl, html, count=1, flags=re.S)
    assert n == 1, "%s: anchor not found exactly once: %s" % (path, name)
    return new


def add_nav(path, prefix, active):
    html = open(path, encoding="utf-8").read()
    assert "topnav" not in html, "%s: nav already present" % path
    # 1. CSS before </style>
    html = sub_once(html, r'    </style>', NAV_CSS + '    </style>',
                    "style close", path)
    # 2. Nav right after </header>
    html = sub_once(html, r'    </header>\n',
                    '    </header>\n' + nav_html(prefix, active) + '\n',
                    "header close", path)
    open(path, "w", encoding="utf-8").write(html)
    print("nav added:", path)


def clean_meta(path, old, new):
    html = open(path, encoding="utf-8").read()
    assert html.count(old) == 1, "%s: meta anchor count %d" % (path, html.count(old))
    open(path, "w", encoding="utf-8").write(html.replace(old, new))
    print("meta cleaned:", path)


def main():
    # Homepage: root links, Top Stories active
    add_nav(f"{BASE}/index.html", "", "top")
    clean_meta(f"{BASE}/index.html",
               '          The blog companion to the podcast<br />\n'
               '          <a href="archive.html">Archive &rarr;</a> &middot; '
               '<a href="learn/">Learn &rarr;</a>',
               '          The blog companion to the podcast')
    # Archive: root links, Latest active
    add_nav(f"{BASE}/archive.html", "", "latest")
    clean_meta(f"{BASE}/archive.html",
               '          Every story, newest first<br />\n'
               '          <a href="learn/">Learn &rarr;</a>',
               '          Every story, newest first')
    # Posts: ../ links, Top Stories active
    for path in sorted(glob.glob(f"{BASE}/posts/????-??-??-*.html")):
        add_nav(path, "../", "top")
        clean_meta(path,
                   '          The blog companion to the podcast<br />\n'
                   '          <a href="../archive.html">Archive &rarr;</a> '
                   '&middot; <a href="../learn/">Learn &rarr;</a>',
                   '          The blog companion to the podcast')
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
