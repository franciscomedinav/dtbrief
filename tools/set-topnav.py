#!/usr/bin/env python3
"""Install the professional two-part site header on every dtbrief.com page
(Nov 14, 2026, Pepe's approved design).

The block (marked <!-- site-topnav --> ... <!-- /site-topnav -->) carries its
own <style> and <script>, in the same self-contained style as the site
footer: a sticky bar with the DTBRIEF mark + wordmark, section links
(Latest / AI / Chips / Big Tech / Business / Security / Learn / Breaking
with a Pulse-red dot), a Listen dropdown (Spotify + Apple Podcasts), a
search button that expands a search row driving search-index.json from any
page (depth-correct relative fetch + result links), and a Subscribe pill.
At <=760px the links collapse behind a hamburger (logo + Subscribe +
hamburger stay visible).

Replaces the old add-sticky-nav.py .topnav bar everywhere and, on the
homepage, removes the sections pill strip and the mid-page search block
(their jobs now live in the header). Idempotent: a page already carrying
the marker gets its block regenerated in place; a re-run changes 0 files.

Active state per page: posts -> their topic from tools/topics.json;
lessons + learn/index -> Learn; archive.html -> Latest; breaking/ ->
Breaking; section pages -> their section; everything else -> none.

Generators (build-lesson.py, build-sections.py, build-breaking-archive.py)
import apply_to_html() from this file so rebuilt pages keep the header.
Run from anywhere:  python3 tools/set-topnav.py

Note: the search-result card's kicker class is "pkicker", not "kicker" —
build-lesson.py swaps the first <span class="kicker"> in the template,
and the header script must never be that first match.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
START = "<!-- site-topnav -->"
END = "<!-- /site-topnav -->"

SPOTIFY = "https://open.spotify.com/show/2ssu27PcFaDaeQkVqPz9ls"
APPLE = "https://podcasts.apple.com/us/podcast/daily-tech-briefing/id6822945922"
SUBSCRIBE = "https://franciscos-newsletter-df7908.beehiiv.com/subscribe"

NAV_ITEMS = [
    ("latest", "Latest", "archive.html"),
    ("ai", "AI", "sections/ai.html"),
    ("chips", "Chips", "sections/chips.html"),
    ("big-tech", "Big Tech", "sections/big-tech.html"),
    ("business", "Business", "sections/business.html"),
    ("security", "Security", "sections/security.html"),
    ("learn", "Learn", "learn/"),
    ("breaking", "Breaking", "breaking/"),
]

CSS = """<style>
  .sitehdr { position: sticky; top: 0; z-index: 50; background: var(--paper, #F4F6F8); border-bottom: 1px solid var(--rule, #D8DEE7); box-shadow: 0 1px 10px rgba(10, 15, 30, 0.07); }
  .sitehdr-inner { max-width: 1080px; margin: 0 auto; padding: 0 24px; min-height: 56px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
  .sitehdr-brand { display: flex; align-items: center; gap: 9px; text-decoration: none; color: var(--ink, #0A0F1E); flex: none; padding: 10px 0; }
  .sitehdr-brand img { width: 28px; height: 28px; display: block; }
  .sitehdr-word { font-family: "Sora", sans-serif; font-weight: 800; font-size: 17px; letter-spacing: 0.03em; line-height: 1; }
  .sitehdr-nav { display: flex; align-items: center; gap: 2px; flex-wrap: wrap; }
  .sitehdr-nav > a, .sitehdr-listen-label { font-family: "IBM Plex Mono", monospace; font-size: 13px; font-weight: 600; color: var(--ink-soft, #2E3A52); text-decoration: none; padding: 8px 9px; border-bottom: 2px solid transparent; white-space: nowrap; }
  .sitehdr-nav > a:hover, .sitehdr-listen-label:hover { color: var(--ink, #0A0F1E); }
  .sitehdr-nav > a.active { color: var(--accent, #0090C8); border-bottom-color: var(--accent, #0090C8); }
  .sitehdr-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #FF5A3C; margin-right: 6px; vertical-align: 2px; animation: sitehdr-pulse 1.6s ease-in-out infinite; }
  @keyframes sitehdr-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .25; } }
  @media (prefers-reduced-motion: reduce) { .sitehdr-dot { animation: none; } }
  .sitehdr-listen { position: relative; display: inline-block; }
  .sitehdr-listen-label { cursor: pointer; display: inline-block; }
  .sitehdr-drop { display: none; position: absolute; top: 100%; left: 0; min-width: 190px; background: var(--card, #ffffff); border: 1px solid var(--rule, #D8DEE7); border-radius: 12px; box-shadow: 0 10px 30px rgba(10, 15, 30, 0.14); padding: 8px; z-index: 60; }
  .sitehdr-listen:hover .sitehdr-drop, .sitehdr-listen:focus-within .sitehdr-drop { display: block; }
  .sitehdr-drop a { display: block; font-family: "IBM Plex Sans", system-ui, sans-serif; font-size: 14.5px; font-weight: 600; color: var(--ink, #0A0F1E); text-decoration: none; padding: 9px 11px; border-radius: 8px; white-space: nowrap; }
  .sitehdr-drop a:hover { background: var(--accent-soft, rgba(0, 144, 200, 0.08)); color: var(--accent, #0090C8); }
  .sitehdr-actions { margin-left: auto; display: flex; align-items: center; gap: 10px; flex: none; }
  .sitehdr-iconbtn { display: inline-flex; align-items: center; justify-content: center; width: 38px; height: 38px; border-radius: 50%; border: 1px solid var(--rule, #D8DEE7); background: var(--card, #ffffff); color: var(--ink-soft, #2E3A52); cursor: pointer; padding: 0; }
  .sitehdr-iconbtn:hover { color: var(--accent, #0090C8); border-color: var(--accent, #0090C8); }
  .sitehdr-iconbtn svg { width: 18px; height: 18px; display: block; }
  .sitehdr-sub { font-family: "IBM Plex Mono", monospace; font-size: 13.5px; font-weight: 600; color: #ffffff; background: var(--accent, #0090C8); border-radius: 999px; padding: 10px 18px; text-decoration: none; white-space: nowrap; }
  .sitehdr-sub:hover { filter: brightness(1.1); color: #ffffff; }
  .sitehdr-burger { display: none; }
  .sitehdr-searchrow { border-top: 1px solid var(--rule, #D8DEE7); }
  .sitehdr-searchinner { max-width: 1080px; margin: 0 auto; padding: 14px 24px 18px; }
  .sitehdr-searchbox { width: 100%; font-family: "IBM Plex Sans", system-ui, sans-serif; font-size: 17px; padding: 13px 16px; border: 1px solid var(--rule, #D8DEE7); border-radius: 12px; background: var(--card, #ffffff); color: var(--ink, #0A0F1E); margin: 0; }
  .sitehdr-searchbox:focus { outline: 2px solid var(--accent, #0090C8); outline-offset: 1px; }
  .sitehdr-searchmeta { font-family: "IBM Plex Mono", monospace; font-size: 12.5px; color: var(--ink-faint, #5A6478); margin: 10px 0 0; }
  .sitehdr-results { display: grid; gap: 12px; margin-top: 12px; max-height: 55vh; overflow-y: auto; }
  .sitehdr-results:empty { margin-top: 0; }
  .sitehdr .pcard { display: block; background: var(--card, #ffffff); border: 1px solid var(--rule, #D8DEE7); border-radius: 14px; padding: 18px 20px; text-decoration: none; color: var(--ink, #0A0F1E); }
  .sitehdr .pcard:hover { border-color: var(--accent, #0090C8); }
  .sitehdr .pcard .pkicker { font-family: "IBM Plex Mono", monospace; font-size: 11.5px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--accent, #0090C8); }
  .sitehdr .pcard h3 { font-family: "Sora", sans-serif; font-size: 19px; line-height: 1.25; font-weight: 800; letter-spacing: -0.01em; margin: 8px 0 6px; }
  .sitehdr .pcard p { font-size: 14.5px; line-height: 1.5; color: var(--ink-soft, #2E3A52); margin: 0 0 8px; }
  .sitehdr .pcard .meta { font-family: "IBM Plex Mono", monospace; font-size: 11.5px; color: var(--ink-faint, #5A6478); }
  @media (max-width: 760px) {
    .sitehdr-inner { gap: 10px; padding: 0 16px; }
    .sitehdr-burger { display: inline-flex; }
    .sitehdr-nav { display: none; order: 5; flex-basis: 100%; flex-direction: column; align-items: stretch; gap: 0; padding: 4px 0 12px; }
    .sitehdr.open .sitehdr-nav { display: flex; }
    .sitehdr-nav > a, .sitehdr-listen-label { padding: 11px 6px; border-bottom: 1px solid var(--rule, #D8DEE7); font-size: 14px; }
    .sitehdr-nav > a.active { border-bottom-color: var(--rule, #D8DEE7); box-shadow: inset 3px 0 0 var(--accent, #0090C8); }
    .sitehdr-listen { display: block; }
    .sitehdr-drop { display: block; position: static; border: none; box-shadow: none; background: none; padding: 0 0 4px 16px; min-width: 0; }
    .sitehdr-drop a { padding: 9px 6px; font-family: "IBM Plex Mono", monospace; font-size: 13.5px; color: var(--ink-soft, #2E3A52); }
    .sitehdr-searchinner { padding: 12px 16px 16px; }
  }
</style>"""

SEARCH_SVG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2.2" stroke-linecap="round" aria-hidden="true">'
              '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.8-3.8"/></svg>')
BURGER_SVG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2.2" stroke-linecap="round" aria-hidden="true">'
              '<path d="M4 7h16M4 12h16M4 17h16"/></svg>')

SCRIPT = """<script>
    (function () {
      var hdr = document.currentScript.previousElementSibling;
      if (!hdr) return;
      var PREFIX = "__PREFIX__";
      var burger = hdr.querySelector('.sitehdr-burger');
      burger.addEventListener('click', function () {
        var open = hdr.classList.toggle('open');
        burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
      var row = hdr.querySelector('.sitehdr-searchrow');
      var toggle = hdr.querySelector('.sitehdr-searchbtn');
      var input = hdr.querySelector('#hdr-search');
      var meta = hdr.querySelector('#hdr-search-meta');
      var resultsBox = hdr.querySelector('#hdr-search-results');
      var index = null, loaded = false, loading = false;
      function esc(s) {
        return String(s == null ? '' : s).replace(/&/g, '&amp;')
          .replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
      }
      function words(q) {
        return q.toLowerCase().split(/\\s+/).filter(function (w) { return w.length > 0; });
      }
      function matches(item, ws) {
        var hay = (item.title + ' ' + item.excerpt + ' ' + item.date).toLowerCase();
        return ws.every(function (w) { return hay.indexOf(w) !== -1; });
      }
      function render() {
        var query = (input.value || '').trim();
        if (!query) { resultsBox.innerHTML = ''; meta.textContent = ''; return; }
        if (!loaded) { meta.textContent = 'Search is still loading\\u2026'; return; }
        var list = index.filter(function (item) { return matches(item, words(query)); });
        meta.textContent = list.length + (list.length === 1 ? ' result' : ' results') +
          ' for \\u201c' + query + '\\u201d';
        var html = '';
        list.forEach(function (item) {
          html += '<a class="pcard" href="' + esc(PREFIX + item.url) + '">' +
            '<span class="pkicker">Top Story</span>' +
            '<h3>' + esc(item.title) + '</h3>' +
            '<p>' + esc(item.excerpt) + '</p>' +
            '<span class="meta">' + esc(item.date) + ' &middot; Episode ' + esc(item.episode) + '</span></a>';
        });
        resultsBox.innerHTML = html;
      }
      function loadIndex() {
        if (loaded || loading) return;
        loading = true;
        fetch(PREFIX + 'search-index.json')
          .then(function (r) { if (!r.ok) throw new Error('index HTTP ' + r.status); return r.json(); })
          .then(function (data) { index = data; loaded = true; loading = false; render(); })
          .catch(function () { loading = false; meta.textContent = 'Search is unavailable right now.'; });
      }
      toggle.addEventListener('click', function () {
        var show = row.hidden;
        row.hidden = !show;
        toggle.setAttribute('aria-expanded', show ? 'true' : 'false');
        if (show) { loadIndex(); input.focus(); }
      });
      input.addEventListener('input', function () { loadIndex(); render(); });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && !row.hidden) {
          row.hidden = true;
          toggle.setAttribute('aria-expanded', 'false');
        }
      });
    })();
    </script>"""


def header_block(prefix, active):
    """The full marked header block. prefix: '' or '../' (per page depth);
    active: a NAV_ITEMS key or None."""
    p = prefix
    links = []
    for key, label, href in NAV_ITEMS:
        cls = ' class="active"' if key == active else ""
        cur = ' aria-current="page"' if key == active else ""
        dot = ('<span class="sitehdr-dot" aria-hidden="true"></span>'
               if key == "breaking" else "")
        links.append('        <a href="%s%s" data-nav="%s"%s%s>%s%s</a>'
                     % (p, href, key, cls, cur, dot, label))
    nav = "\n".join(links)
    script = SCRIPT.replace("__PREFIX__", p)
    return f"""{START}
{CSS}
    <header class="sitehdr">
      <div class="sitehdr-inner">
        <a class="sitehdr-brand" href="{p}index.html" aria-label="Daily Tech Briefing home">
          <img src="{p}favicon.svg" alt="" width="28" height="28" />
          <span class="sitehdr-word">DTBRIEF</span>
        </a>
        <nav class="sitehdr-nav" id="sitehdr-menu" aria-label="Site">
{nav}
          <span class="sitehdr-listen">
            <span class="sitehdr-listen-label" tabindex="0">Listen &#9662;</span>
            <span class="sitehdr-drop">
              <a href="{SPOTIFY}" target="_blank" rel="noopener">Spotify</a>
              <a href="{APPLE}" target="_blank" rel="noopener">Apple Podcasts</a>
            </span>
          </span>
        </nav>
        <div class="sitehdr-actions">
          <button class="sitehdr-iconbtn sitehdr-searchbtn" type="button" aria-expanded="false" aria-controls="sitehdr-searchrow" aria-label="Search the site">{SEARCH_SVG}</button>
          <a class="sitehdr-sub" href="{SUBSCRIBE}" target="_blank" rel="noopener">Subscribe</a>
          <button class="sitehdr-iconbtn sitehdr-burger" type="button" aria-expanded="false" aria-controls="sitehdr-menu" aria-label="Menu">{BURGER_SVG}</button>
        </div>
      </div>
      <div class="sitehdr-searchrow" id="sitehdr-searchrow" hidden>
        <div class="sitehdr-searchinner">
          <input id="hdr-search" class="sitehdr-searchbox" type="search" placeholder="Search stories &mdash; try &ldquo;Anthropic&rdquo; or &ldquo;Apple&rdquo;" autocomplete="off" aria-label="Search the briefing" />
          <p id="hdr-search-meta" class="sitehdr-searchmeta" aria-live="polite"></p>
          <div id="hdr-search-results" class="sitehdr-results"></div>
        </div>
      </div>
    </header>
{script}
{END}"""


OLD_NAV_CSS = re.compile(
    r"\n      /\* ---------- Sticky section nav ---------- \*/.*?\n      \}\n",
    re.S)
OLD_NAV_HTML = re.compile(
    r'    <nav class="topnav" aria-label="Sections">.*?</nav>\n', re.S)
BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)


def apply_to_html(html, prefix, active):
    """Return html carrying the new header block for (prefix, active).

    Handles all three starting states: block already present (regenerate
    in place), old .topnav present (remove its CSS + markup, insert the
    block after the masthead </header>), or neither (insert fresh)."""
    block = header_block(prefix, active)
    if START in html:
        new, n = BLOCK_RE.subn(lambda _: block, html, count=1)
        assert n == 1, "topnav block replace failed"
        return new
    new = html
    if 'class="topnav"' in new:
        new, n = OLD_NAV_CSS.subn("", new, count=1)
        assert n == 1, "old topnav CSS not found exactly once"
        new, n = OLD_NAV_HTML.subn("", new, count=1)
        assert n == 1, "old topnav markup not found exactly once"
    assert new.count("    </header>\n") >= 1, "masthead </header> not found"
    new = new.replace("    </header>\n",
                      "    </header>\n" + block + "\n", 1)
    return new


def homepage_cleanup(html):
    """Homepage only: drop the sections pill strip and the mid-page search
    block (both jobs moved into the header) plus the now-dead search.js
    include. Asserts each anchor exists exactly once."""
    new, n = re.subn(
        r'        <h2 class="section-label">Sections</h2>\n'
        r'        <div class="sections-strip">.*?</div>\n', "", html,
        count=1, flags=re.S)
    assert n == 1, "homepage sections strip not found"
    html = new
    new, n = re.subn(
        r'        <h2 class="section-label">Search</h2>\n'
        r'        <input id="site-search".*?'
        r'<div id="search-results" class="search-results"></div>\n', "",
        html, count=1, flags=re.S)
    assert n == 1, "homepage search block not found"
    html = new
    assert html.count('  <script src="search.js" defer></script>\n') == 1, \
        "homepage search.js include not found"
    html = html.replace('  <script src="search.js" defer></script>\n', "", 1)
    return html


DEAD_HOMEPAGE_CSS = re.compile(
    r"\n      \.search-box \{.*?\n      \}\n"
    r"      \.search-box:focus \{[^}]*\}\n"
    r"      \.search-meta \{.*?\n      \}\n"
    r"      \.search-results \{[^}]*\}\n"
    r"      \.search-results \.post-card:last-child \{[^}]*\}\n", re.S)
DEAD_PILL_CSS = re.compile(
    r"\n      \.sections-strip \{[^}]*\}\n"
    r"      \.section-pill \{.*?\n      \}\n"
    r"      \.section-pill:hover \{[^}]*\}\n", re.S)


def homepage_dead_css(html):
    """Homepage only, safe on every run: strip the CSS rules that belonged
    to the removed pill strip and mid-page search block (the masthead
    dateline rules in the same chunk stay — the dateline is still live)."""
    html = DEAD_HOMEPAGE_CSS.sub("", html, count=1)
    html = DEAD_PILL_CSS.sub("", html, count=1)
    return html


def load_topics():
    with open(os.path.join(HERE, "topics.json"), encoding="utf-8") as f:
        return json.load(f)


def active_for(rel, topics):
    parts = rel.split(os.sep)
    if rel == "index.html":
        return None
    if rel == "archive.html":
        return "latest"
    if parts[0] == "posts":
        return topics.get(parts[1])
    if parts[0] == "learn":
        return "learn"
    if parts[0] == "breaking":
        return "breaking"
    if parts[0] == "sections":
        key = parts[1][:-len(".html")]
        return key if key in dict((k, None) for k, _, _ in NAV_ITEMS) else None
    return None


def targets():
    out = []
    for pat in ["*.html", "breaking/index.html", "posts/*.html",
                "learn/*.html", "sections/*.html"]:
        out.extend(glob.glob(os.path.join(ROOT, pat)))
    # 404.html is a standalone page (no masthead/nav) — same exclusion as
    # tools/add-footer.py.
    return sorted(set(p for p in out
                      if os.path.basename(p) != "404.html"))


def main():
    topics = load_topics()
    changed, unchanged = [], []
    for path in targets():
        rel = os.path.relpath(path, ROOT)
        depth = len(rel.split(os.sep)) - 1
        prefix = "../" * depth
        html = open(path, encoding="utf-8").read()
        # Homepage cleanup only on first install (its anchors are gone
        # afterwards, and the run must stay idempotent).
        new = (homepage_cleanup(html)
               if rel == "index.html" and START not in html else html)
        if rel == "index.html":
            new = homepage_dead_css(new)
        new = apply_to_html(new, prefix, active_for(rel, topics))
        if new != html:
            open(path, "w", encoding="utf-8").write(new)
            changed.append(rel)
        else:
            unchanged.append(rel)
    print("changed:", len(changed))
    for c in changed:
        print("  ", c)
    print("unchanged:", len(unchanged))
    return 0


if __name__ == "__main__":
    sys.exit(main())
