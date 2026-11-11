#!/usr/bin/env python3
"""Rewrite the homepage headlines ticker from a post's digest section.

Usage: python3 tools/update-ticker.py posts/YYYY-MM-DD-<slug>.html

Reads the post's "The rest of today's briefing" digest (s4): each item is a
bold linked headline + outlet credit. Rewrites the ticker track in index.html
with those items, each listed TWICE — the CSS animation scrolls the track by
-50%, so the duplicated list is what makes the loop seamless.

Idempotent: running it twice on the same post produces no change.
"""
import re
import sys

BASE = "/home/hatch/workspace/dtbrief-blog"
INDEX = BASE + "/index.html"

ITEM_RE = re.compile(
    r'<p><a href="([^"]+)"[^>]*><strong>(.*?)</strong></a> &mdash; '
    r'([^<]*) &mdash; ([^<]+)</p>',
    re.S,
)


def extract_digest_items(post_path):
    html = open(post_path, encoding="utf-8").read()
    start = html.find('<h2 id="s4">')
    assert start != -1, "%s: no s4 digest section" % post_path
    end = html.find("<h2", start + 1)
    section = html[start:end if end != -1 else len(html)]
    items = [(m.group(2), m.group(4).strip(), m.group(1))
             for m in ITEM_RE.finditer(section)]
    assert items, "%s: no digest items found" % post_path
    return items  # [(headline, outlet, url), ...]


def ticker_items_html(items):
    """One copy of the items as track HTML (links + separators)."""
    out = []
    for headline, outlet, url in items:
        out.append(
            '              <a href="%s" target="_blank" rel="noopener">%s '
            '<span class="ticker-outlet">&mdash; %s</span></a>'
            % (url, headline, outlet))
        out.append('              <span class="ticker-sep" aria-hidden="true">'
                   '&bull;</span>')
    return "\n".join(out)


def update_index(items):
    html = open(INDEX, encoding="utf-8").read()
    open_tag = '<div class="ticker-track" id="ticker-track">'
    assert html.count(open_tag) == 1, "ticker track not found exactly once"
    start = html.find(open_tag) + len(open_tag)
    end = html.find("\n            </div>", start)
    assert end != -1, "ticker track close not found"
    # Two copies of the list: the -50% scroll animation loops seamlessly.
    new_track = "\n" + ticker_items_html(items) + "\n" + ticker_items_html(items)
    html = html[:start] + new_track + html[end:]
    open(INDEX, "w", encoding="utf-8").write(html)
    return len(items)


def main():
    if len(sys.argv) != 2:
        print("usage: update-ticker.py posts/YYYY-MM-DD-<slug>.html")
        return 2
    items = extract_digest_items(sys.argv[1])
    n = update_index(items)
    print("ticker updated: %d stories (x2 in track)" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
