#!/usr/bin/env python3
"""One-off: insert the headlines ticker into index.html (CSS + shell + JS).
The ticker items themselves come from today's post via update-ticker.py's
extraction, so the shipped ticker is exactly what the daily tool regenerates.
Run once from ~/workspace/dtbrief-blog.
"""
import re
import sys

sys.path.insert(0, "/home/hatch/workspace/dtbrief-blog/tools")
from update_ticker import extract_digest_items, ticker_items_html  # noqa: E402

BASE = "/home/hatch/workspace/dtbrief-blog"
INDEX = BASE + "/index.html"
POST = BASE + "/posts/2026-11-10-anthropic-fable-mythos-5-2.html"

TICKER_CSS = """
      /* ---------- Headlines ticker ---------- */
      .ticker { display: flex; align-items: center; gap: 14px; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); padding: 11px 0; margin-bottom: 40px; }
      .ticker-label { font-family: "IBM Plex Mono", monospace; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; color: var(--accent); flex: none; white-space: nowrap; }
      .ticker-viewport { overflow: hidden; flex: 1; min-width: 0; mask-image: linear-gradient(90deg, transparent, #000 20px, #000 calc(100% - 20px), transparent); -webkit-mask-image: linear-gradient(90deg, transparent, #000 20px, #000 calc(100% - 20px), transparent); }
      .ticker-track { display: inline-flex; align-items: center; white-space: nowrap; animation: ticker-scroll 90s linear infinite; will-change: transform; }
      .ticker-track a { font-family: "IBM Plex Sans", system-ui, sans-serif; font-size: 15px; font-weight: 600; color: var(--ink); text-decoration: none; }
      .ticker-track a:hover { color: var(--accent); }
      .ticker-outlet { font-weight: 400; color: var(--ink-faint); }
      .ticker-sep { color: var(--accent); margin: 0 16px; flex: none; }
      .ticker-pause { font-family: "IBM Plex Mono", monospace; font-size: 11.5px; font-weight: 600; color: var(--ink-soft); background: none; border: 1px solid var(--rule); border-radius: 999px; padding: 5px 10px; cursor: pointer; flex: none; }
      .ticker-pause:hover { color: var(--ink); border-color: var(--ink-soft); }
      .ticker:hover .ticker-track, .ticker.paused .ticker-track { animation-play-state: paused; }
      @keyframes ticker-scroll { from { transform: translateX(0); } to { transform: translateX(-50%); } }
      @media (max-width: 620px) {
        .ticker { flex-wrap: wrap; gap: 8px 14px; }
        .ticker-viewport { flex: 1 1 100%; order: 3; }
        .ticker-pause { margin-left: auto; }
      }
      @media (prefers-reduced-motion: reduce) {
        .ticker-track { animation: none; }
        .ticker-viewport { overflow-x: auto; }
      }
"""

TICKER_JS = """  <script>
    (function () {
      var t = document.querySelector('.ticker');
      if (!t) return;
      var b = t.querySelector('.ticker-pause');
      b.addEventListener('click', function () {
        var paused = t.classList.toggle('paused');
        b.textContent = paused ? 'Play' : 'Pause';
        b.setAttribute('aria-pressed', paused ? 'true' : 'false');
      });
    })();
  </script>
"""


def sub_once(html, pattern, repl, name):
    new, n = re.subn(pattern, repl, html, count=1, flags=re.S)
    assert n == 1, "anchor not found exactly once: %s" % name
    return new


def main():
    html = open(INDEX, encoding="utf-8").read()
    assert 'class="ticker"' not in html, "ticker already present"
    items = extract_digest_items(POST)
    print("digest items:", len(items))
    for headline, outlet, url in items:
        print(" -", outlet, "|", headline[:60])

    # 1. CSS before </style>
    html = sub_once(html, r'    </style>', TICKER_CSS + '    </style>',
                    "style close")
    # 2. Ticker shell right after the Top Story hero's listen-row,
    #    before the latest-player block.
    track = ticker_items_html(items) + "\n" + ticker_items_html(items)
    shell = (
        '        <div class="ticker" aria-label="The rest of today\'s briefing">\n'
        '          <span class="ticker-label">The rest of today&rsquo;s briefing</span>\n'
        '          <div class="ticker-viewport">\n'
        '            <div class="ticker-track" id="ticker-track">\n'
        + track + '\n'
        '            </div>\n'
        '          </div>\n'
        '          <button class="ticker-pause" type="button" aria-pressed="false">Pause</button>\n'
        '        </div>\n\n'
    )
    html = sub_once(html, r'        <div class="latest-player">',
                    shell + '        <div class="latest-player">',
                    "latest-player open")
    # 3. Pause-toggle JS after the search script tag.
    html = sub_once(html,
                    r'  <script src="search.js" defer></script>\n',
                    '  <script src="search.js" defer></script>\n' + TICKER_JS,
                    "search script tag")
    open(INDEX, "w", encoding="utf-8").write(html)
    print("ticker inserted into index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
