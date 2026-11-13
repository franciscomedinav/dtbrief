#!/usr/bin/env python3
"""Build a Learning Center lesson page and regenerate the learn index.

Usage:
  python3 tools/build-lesson.py tools/lessons/YYYY-MM-DD-<slug>.json
  python3 tools/build-lesson.py --reindex

The lesson JSON holds all content (title, deck, key ideas, sections, terms,
images, briefing link, sources). The lesson HTML is rendered from the newest
daily-post v2 template (newest file in posts/), with the Learning Center CSS
extras injected. The registry tools/lessons.json lists lessons newest-first;
learn/index.html is regenerated from it on every build.

Section rendering rules (kept simple so the daily cron worker can write the
JSON by hand):
  - "paras": list of raw HTML <p>...</p> strings, in order.
  - "loop": {"steps": [{"t": ..., "d": ...}]} renders the 4-step diagram
    after the section's FIRST paragraph (or after paragraph N with
    "loop_after": N, 0-based).
  - "figure": {"src", "alt", "caption"} renders after the FIRST paragraph
    (or after paragraph N with "figure_after": N).
  - "vs": [{"label", "text", "agent": bool}] renders comparison cards after
    the LAST paragraph.
  - "pull": a pull-quote string, rendered last in the section.
  - "hero": page-level figure rendered right after the byline.
"""
import glob
import json
import os
import re
import sys

BASE = os.path.expanduser("~/workspace/dtbrief-blog")
LEARN_DIR = os.path.join(BASE, "learn")
LESSONS_DIR = os.path.join(BASE, "tools", "lessons")
REGISTRY = os.path.join(BASE, "tools", "lessons.json")

EXTRA_CSS = """
      /* Learning Center extras: figures, loop diagram, comparison cards */
      .figure { margin: 28px 0; }
      .figure img { display: block; width: 100%; height: auto; border-radius: 14px; border: 1px solid var(--rule); }
      .figure figcaption { font-size: 13.5px; color: var(--ink-faint); margin-top: 10px; line-height: 1.5; }
      .loop-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 22px 0; }
      .loop-step { background: var(--accent-soft); border: 1px solid var(--rule); border-radius: 12px; padding: 16px 18px; }
      .loop-step .loop-num { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; background: var(--chip-bg); color: var(--chip-ink); font-family: "IBM Plex Mono", monospace; font-size: 14px; font-weight: 600; margin-bottom: 8px; }
      .loop-step strong { display: block; font-family: "Sora", sans-serif; font-size: 17px; margin-bottom: 4px; }
      .loop-step span { display: block; font-size: 15px; line-height: 1.5; color: var(--ink-soft); }
      .vs-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 22px 0; }
      .vs-card { border: 1px solid var(--rule); border-radius: 12px; padding: 18px; background: var(--card); }
      .vs-card.agent { border-color: var(--accent); background: var(--accent-soft); }
      .vs-card strong { display: block; font-family: "Sora", sans-serif; font-size: 18px; margin-bottom: 6px; }
      .vs-card span { display: block; font-size: 15px; line-height: 1.55; color: var(--ink-soft); }
      @media (max-width: 560px) {
        .loop-grid, .vs-grid { grid-template-columns: 1fr; }
      }
"""


def sub_once(html, pattern, repl, name):
    new, n = re.subn(pattern, repl, html, count=1, flags=re.S)
    assert n == 1, "anchor not found exactly once: %s" % name
    return new


def newest_post_template():
    posts = sorted(glob.glob(os.path.join(BASE, "posts", "????-??-??-*.html")))
    assert posts, "no post template found"
    return posts[-1]


def figure_html(fig, lazy=False):
    lazy_attr = ' loading="lazy"' if lazy else ""
    return ('        <figure class="figure">\n'
            '          <img src="%s" alt="%s" width="2048" height="1152"%s />\n'
            '          <figcaption>%s</figcaption>\n'
            '        </figure>' % (fig["src"], fig["alt"], lazy_attr,
                                   fig["caption"]))


def render_section(sec):
    out = ['        <section aria-labelledby="s%d">' % sec["num"],
           '          <h2 id="s%d"><span class="num">%d</span> %s</h2>'
           % (sec["num"], sec["num"], sec["title"])]
    paras = sec.get("paras", [])
    loop_after = sec.get("loop_after", 0)
    figure_after = sec.get("figure_after", 0)
    for i, p in enumerate(paras):
        out.append("          " + p)
        if i == loop_after:
            if sec.get("loop"):
                steps = sec["loop"]["steps"]
                out.append('          <div class="loop-grid" role="img" '
                           'aria-label="The agent loop: ' +
                           ", ".join(s["t"].lower() for s in steps) +
                           ', then repeat">')
                for j, s in enumerate(steps, 1):
                    out.append('            <div class="loop-step"><span '
                               'class="loop-num">%d</span><strong>%s</strong>'
                               '<span>%s</span></div>'
                               % (j, s["t"], s["d"]))
                out.append('          </div>')
        if i == figure_after:
            if sec.get("figure"):
                out.append(figure_html(sec["figure"], lazy=True))
    if sec.get("vs"):
        out.append('          <div class="vs-grid">')
        for card in sec["vs"]:
            cls = "vs-card agent" if card.get("agent") else "vs-card"
            out.append('            <div class="%s"><strong>%s</strong>'
                       '<span>%s</span></div>'
                       % (cls, card["label"], card["text"]))
        out.append('          </div>')
    if sec.get("pull"):
        out.append('          <div class="pull">%s</div>' % sec["pull"])
    out.append('        </section>')
    return "\n".join(out)


def render_terms(terms):
    out = ['        <section aria-labelledby="terms">',
           '          <h2 id="terms">Key terms</h2>',
           '          <ul class="watch">']
    for t in terms:
        out.append('            <li>\n'
                   '              <span class="w-label">%s</span>\n'
                   '              <span>%s</span>\n'
                   '            </li>' % (t["term"], t["def"]))
    out.append('          </ul>')
    out.append('        </section>')
    return "\n".join(out)


def lesson_body(lesson):
    parts = []
    if lesson.get("hero"):
        parts.append(figure_html(lesson["hero"]))
    parts.append('        <div class="keynums" role="group" '
                 'aria-label="Key ideas">')
    for k in lesson["key_ideas"]:
        parts.append('          <div class="keynum">\n'
                     '            <div class="fig">%s</div>\n'
                     '            <div class="lbl">%s</div>\n'
                     '          </div>' % (k["fig"], k["lbl"]))
    parts.append('        </div>')
    parts.append("")
    for sec in lesson["sections"]:
        parts.append(render_section(sec))
        parts.append("")
    if lesson.get("terms"):
        parts.append(render_terms(lesson["terms"]))
        parts.append("")
    b = lesson["briefing"]
    parts.append('        <div class="source-card">\n'
                 '          <div class="sc-label">From today&rsquo;s briefing'
                 '</div>\n'
                 '          <p>This lesson comes from today&rsquo;s Daily Tech '
                 'Briefing (Episode %d, %s): %s. Read the full briefing: '
                 '<a href="%s">%s</a>.</p>\n'
                 '        </div>'
                 % (b["episode"], lesson["date_long"], b["summary"],
                    b["url"], b["label"]))
    parts.append("")
    parts.append('        <div class="source-card">\n'
                 '          <div class="sc-label">Sources</div>\n'
                 '          <p>%s</p>\n'
                 '        </div>' % lesson["sources"])
    return "\n".join(parts)


def fix_learn_nav(h):
    """Learn pages live in learn/: the Learn link points at index.html (not
    ../learn/), and Learn — not Top Stories — is the active nav item."""
    h = h.replace('<a href="../learn/" data-nav="learn">Learn</a>',
                  '<a href="index.html" data-nav="learn" class="active">Learn</a>',
                  1)
    h = h.replace('<a href="../index.html" data-nav="top" class="active">Top Stories</a>',
                  '<a href="../index.html" data-nav="top">Top Stories</a>', 1)
    assert 'data-nav="learn" class="active"' in h, "learn nav fix failed"
    return h


def share_row(url, title, label):
    """Self-contained share row (inline styles; no CSS dependency).
    Added Nov 12, 2026 (Pepe) to posts and lessons."""
    from urllib.parse import quote
    u = quote(url, safe="")
    t = quote(title, safe="")
    pill = ("display:inline-block;background:#0A0F1E;color:#F4F6F8;"
            "border-radius:999px;padding:8px 16px;font-family:'IBM Plex Mono',"
            "monospace;font-size:13px;font-weight:600;text-decoration:none;")
    return (
        '        <div class="share-row" style="margin:28px 0 8px;'
        'padding-top:18px;border-top:1px solid #D8DEE7;">\n'
        '          <span style="font-family:\'IBM Plex Mono\',monospace;'
        'font-size:12px;letter-spacing:.12em;text-transform:uppercase;'
        'color:#5A6478;">%s</span>\n'
        '          <div style="margin-top:10px;display:flex;flex-wrap:wrap;'
        'gap:8px;">\n'
        '            <a href="https://twitter.com/intent/tweet?url=%s&text=%s" '
        'target="_blank" rel="noopener" style="%s">Post to X</a>\n'
        '            <a href="https://wa.me/?text=%s%%20%s" target="_blank" '
        'rel="noopener" style="%s">WhatsApp</a>\n'
        '            <a href="https://www.facebook.com/sharer/sharer.php?u=%s" '
        'target="_blank" rel="noopener" style="%s">Facebook</a>\n'
        '            <a href="#" onclick="navigator.clipboard.writeText'
        '(\'%s\');this.textContent=\'Link copied\';return false;" '
        'style="%s">Copy link</a>\n'
        '          </div>\n'
        '        </div>'
        % (label, u, t, pill, t, u, pill, u, pill, url, pill))


def newsletter_block():
    """Site-built newsletter band (Nov 13, 2026 — replaced the beehiiv JS
    embed, whose live rendering ignored the builder's width settings on
    phones). Same copy as the beehiiv form; the button links to the
    publication's beehiiv subscribe page (which does not support email
    prefill — verified Nov 13, 2026)."""
    return (
        '        <div class="newsletter-band" style="margin:28px 0 8px;'
        'padding:24px 20px;border:1px solid #D8DEE7;border-radius:12px;'
        'background:#EDF1F8;">'
        '<div style="font-family:\'Sora\',sans-serif;font-weight:700;'
        'font-size:21px;line-height:1.25;color:#0A0F1E;margin:0 0 6px;">'
        'Get the Daily Tech Briefing in your inbox</div>'
        '<p style="font-size:15.5px;line-height:1.5;color:#2E3A52;'
        'margin:0 0 16px;">The day&rsquo;s top tech stories in plain '
        'English &mdash; every weekday morning. Free.</p>'
        '<a href="https://franciscos-newsletter-df7908.beehiiv.com/subscribe" '
        'target="_blank" rel="noopener" style="display:block;text-align:center;'
        'background:#0A0F1E;color:#F4F6F8;border-radius:999px;'
        'padding:13px 22px;font-family:\'IBM Plex Mono\',monospace;'
        'font-size:15px;font-weight:600;text-decoration:none;">Subscribe</a>'
        '</div>')


def build_lesson(lesson):
    with open(newest_post_template(), encoding="utf-8") as f:
        h = f.read()
    slug = lesson["slug"]
    h = fix_learn_nav(h)
    h = sub_once(h, r'    </style>', EXTRA_CSS + '    </style>', "extra css")
    h = sub_once(h, r'<meta name="description" content="[^"]*" />',
                 '<meta name="description" content="%s" />'
                 % lesson["meta_description"], "meta description")
    h = sub_once(h, r'<meta property="og:title" content="[^"]*" />',
                 '<meta property="og:title" content="%s" />'
                 % lesson["og_title"], "og title")
    h = sub_once(h, r'<meta property="og:description" content="[^"]*" />',
                 '<meta property="og:description" content="%s" />'
                 % lesson["og_description"], "og description")
    h = sub_once(h, r'<meta property="og:url" content="[^"]*" />',
                 '<meta property="og:url" content="https://dtbrief.com/learn/%s.html" />'
                 % slug, "og url")
    h = sub_once(h, r'\{"@context":"https://schema\.org".*?\}\n    </script>',
                 '{"@context":"https://schema.org","@type":"Article",'
                 '"headline":"%s","datePublished":"%s",'
                 '"author":{"@type":"Organization","name":"Daily Tech Briefing"},'
                 '"publisher":{"@type":"Organization","name":"Daily Tech Briefing",'
                 '"url":"https://dtbrief.com/"},'
                 '"mainEntityOfPage":"https://dtbrief.com/learn/%s.html"}\n    </script>'
                 % (lesson["title"].replace('"', '\\"'), lesson["date"], slug),
                 "json-ld")
    h = sub_once(h, r'<title>[^<]*</title>',
                 '<title>%s &mdash; Learning Center &mdash; Daily Tech Briefing</title>'
                 % lesson["title_short"], "title")
    h = sub_once(h, r'<div class="masthead-meta">.*?</div>',
                 '<div class="masthead-meta">\n'
                 '          <strong>Learning Center</strong><br />\n'
                 '          One technology, explained in plain English\n'
                 '        </div>', "masthead meta")
    h = sub_once(h, r'<span class="kicker">[^<]*</span>',
                 '<span class="kicker">Learning Center &middot; Lesson %d</span>'
                 % lesson["lesson_no"], "kicker")
    h = sub_once(h, r'<h1>.*?</h1>',
                 '<h1>%s</h1>' % lesson["title"], "h1")
    h = sub_once(h, r'<p class="deck">.*?</p>',
                 '<p class="deck">%s</p>' % lesson["deck"], "deck")
    h = sub_once(h, r'<span>\d+ min read</span>',
                 '<span>%s</span>' % lesson["read_time"], "read time")
    h = sub_once(h, r'<span>[A-Z][a-z]+ \d{1,2}, \d{4}</span>',
                 '<span>%s</span>' % lesson["date_long"], "byline date")
    # Replace everything from the key-numbers block to </article> with the
    # lesson body (this also drops the listen bar, digest, episode note).
    start = h.index('<div class="keynums"')
    end = h.index('      </article>')
    h = h[:start] + lesson_body(lesson) + "\n" + newsletter_block() + "\n" + share_row(
        "https://dtbrief.com/learn/%s.html" % slug,
        lesson["title"], "Share this lesson") + "\n" + h[end:]
    h = sub_once(h, r'<span><a href="\.\./index\.html">&larr; All posts</a> &middot; [^<]*</span>',
                 '<span><a href="index.html">&larr; Learning Center</a> &middot; %s</span>'
                 % lesson["date_long"], "footer")
    return h


def load_registry():
    if os.path.exists(REGISTRY):
        return json.load(open(REGISTRY, encoding="utf-8"))
    return []


def save_registry(lessons):
    tmp = REGISTRY + ".tmp"
    json.dump(lessons, open(tmp, "w", encoding="utf-8"), indent=2)
    os.replace(tmp, REGISTRY)


def build_index(registry):
    with open(newest_post_template(), encoding="utf-8") as f:
        h = f.read()
    h = fix_learn_nav(h)
    latest = registry[0]
    h = sub_once(h, r'    </style>', EXTRA_CSS + '    </style>', "idx extra css")
    h = sub_once(h, r'<meta name="description" content="[^"]*" />',
                 '<meta name="description" content="Learning Center &mdash; '
                 'one technology from the Daily Tech Briefing, explained in '
                 'plain English. A new lesson every day." />', "idx meta")
    h = sub_once(h, r'<meta property="og:title" content="[^"]*" />',
                 '<meta property="og:title" content="Learning Center '
                 '&mdash; Daily Tech Briefing" />', "idx og title")
    h = sub_once(h, r'<meta property="og:description" content="[^"]*" />',
                 '<meta property="og:description" content="One technology '
                 'from the daily briefing, explained in plain English. A '
                 'new lesson every day." />', "idx og desc")
    h = sub_once(h, r'<meta property="og:url" content="[^"]*" />',
                 '<meta property="og:url" content="https://dtbrief.com/learn/" />',
                 "idx og url")
    h = sub_once(h, r'\{"@context":"https://schema\.org".*?\}\n    </script>',
                 '{"@context":"https://schema.org","@type":"WebPage",'
                 '"name":"Learning Center","url":"https://dtbrief.com/learn/"}\n    </script>',
                 "idx json-ld")
    h = sub_once(h, r'<title>[^<]*</title>',
                 '<title>Learning Center &mdash; Daily Tech Briefing</title>',
                 "idx title")
    h = sub_once(h, r'<div class="masthead-meta">.*?</div>',
                 '<div class="masthead-meta">\n'
                 '          <strong>Learning Center</strong><br />\n'
                 '          One technology, explained in plain English\n'
                 '        </div>', "idx masthead meta")

    def watch_item(e):
        return ('            <li>\n'
                '              <span class="w-label">%s &middot; %s</span>\n'
                '              <span><a href="%s.html"><strong>%s</strong></a>'
                ' &mdash; %s</span>\n'
                '            </li>' % (e["date_long"], e["read_time"],
                                       e["slug"], e["title"], e["deck_short"]))

    article = ['      <article>',
               '        <div class="dateline-row">',
               '          <span class="kicker">Learning Center</span>',
               '        </div>',
               '',
               '        <h1>Learning Center</h1>',
               '',
               '        <p class="deck">One technology from the Daily Tech '
               'Briefing, explained in plain English. A new lesson every day '
               '&mdash; no jargon, no hype, just what it is, how it works, '
               'and why it matters.</p>',
               '']
    hero = latest.get("hero")
    if hero:
        hero = dict(hero)
        hero["alt"] = hero.get("index_alt", hero["alt"])
        hero["caption"] = hero.get("index_caption", hero["caption"])
        article.append(figure_html(hero))
        article.append('')
    article += ['        <div class="byline">',
                '          <span class="who">Daily Tech Briefing</span>',
                '          <span class="dot" aria-hidden="true"></span>',
                '          <span>Updated every weekday</span>',
                '        </div>',
                '',
                '        <section aria-labelledby="lessons">',
                '          <h2 id="lessons"><span class="num">1</span> Latest lesson</h2>',
                '          <ul class="watch">',
                watch_item(latest),
                '          </ul>',
                '        </section>',
                '']
    if len(registry) > 1:
        article += ['        <section aria-labelledby="all">',
                    '          <h2 id="all"><span class="num">2</span> All lessons</h2>',
                    '          <ul class="watch">']
        for e in registry[1:]:
            article.append(watch_item(e))
        article += ['          </ul>',
                    '        </section>',
                    '']
    how_num = 3 if len(registry) > 1 else 2
    article += ['        <section aria-labelledby="how">',
                '          <h2 id="how"><span class="num">%d</span> How it works</h2>'
                % how_num,
                '          <p>Every weekday, the briefing picks one technology '
                'from that day&rsquo;s news &mdash; a model, a chip, a protocol, '
                'a product &mdash; and explains it from zero: what it is, how '
                'it works, and why it matters. Lessons build on each other, '
                'and every one links back to the briefing it came from.</p>',
                '          <p>A new lesson lands here every weekday. Start with '
                'the latest above, or come back tomorrow for the next one.</p>',
                '        </section>',
                '',
                '        <div class="source-card">',
                '          <div class="sc-label">New here?</div>',
                '          <p>The Learning Center is the classroom next to the '
                'newsroom. The <a href="../index.html">Daily Tech Briefing</a> '
                'tells you what happened today; this is where you learn the '
                'technology behind it.</p>',
                '        </div>',
                '      </article>']
    h = sub_once(h, r'      <article>.*?</article>', "\n".join(article),
                 "idx article")
    h = sub_once(h, r'<span><a href="\.\./index\.html">&larr; All posts</a> &middot; [^<]*</span>',
                 '<span><a href="../index.html">&larr; Daily Tech Briefing</a> &middot; %s</span>'
                 % latest["date_long"], "idx footer")
    return h


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--reindex":
        registry = load_registry()
        assert registry, "registry is empty"
        html = build_index(registry)
        with open(os.path.join(LEARN_DIR, "index.html"), "w",
                  encoding="utf-8") as f:
            f.write(html)
        print("rebuilt learn/index.html from %d lessons" % len(registry))
        return 0
    if len(sys.argv) != 2:
        print("usage: build-lesson.py <lesson-json> | --reindex",
              file=sys.stderr)
        return 2
    lesson = json.load(open(sys.argv[1], encoding="utf-8"))
    os.makedirs(LEARN_DIR, exist_ok=True)
    html = build_lesson(lesson)
    out = os.path.join(LEARN_DIR, lesson["slug"] + ".html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    registry = load_registry()
    entry = {"date": lesson["date"], "date_long": lesson["date_long"],
             "slug": lesson["slug"], "title": lesson["title"],
             "deck_short": lesson["deck_short"],
             "read_time": lesson["read_time"], "hero": lesson.get("hero")}
    registry = [e for e in registry if e["slug"] != lesson["slug"]]
    registry.insert(0, entry)
    registry.sort(key=lambda e: e["date"], reverse=True)
    save_registry(registry)
    idx = build_index(registry)
    with open(os.path.join(LEARN_DIR, "index.html"), "w",
              encoding="utf-8") as f:
        f.write(idx)
    print("built learn/%s.html (%d chars); index rebuilt from %d lessons"
          % (lesson["slug"], len(html), len(registry)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
