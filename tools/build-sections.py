#!/usr/bin/env python3
"""Generate the topic section pages for dtbrief.com (Nov 14, 2026).

Reads tools/topics.json (post filename -> one topic key), extracts each
post's headline (<h1>), summary (<p class="deck">) and read time from the
post's own HTML, and writes sections/<key>.html for the five topics plus
sections/index.html, using archive.html as the page shell (prefix "../").
Re-run after adding/classifying a post; include sections/ in the push."""
import glob, html, json, os, re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SECTIONS = [
    ("ai", "AI", "Models, agents and the labs building them, explained plainly."),
    ("chips", "Chips & Hardware", "The silicon the AI race runs on — Nvidia, AMD and the supply chain."),
    ("big-tech", "Big Tech", "Apple, Google, Meta, Microsoft and the platform giants."),
    ("business", "Business & Markets", "Deals, IPOs, earnings and the money moving tech."),
    ("security", "Security & Privacy", "Breaches, security models and staying safe online."),
]

topics = json.load(open(os.path.join(HERE, "topics.json"), encoding="utf-8"))
shell = open(os.path.join(ROOT, "archive.html"), encoding="utf-8").read()
home = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
NEWSLETTER = re.search(r'<div class="newsletter-band".*?</div>\s*\n', home, re.S).group(0).strip()


def plain(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def post_info(fname):
    text = open(os.path.join(ROOT, "posts", fname), encoding="utf-8").read()
    h1 = re.search(r"<h1>(.*?)</h1>", text, re.S).group(1)
    deck = re.search(r'<p class="deck">(.*?)</p>', text, re.S).group(1).strip()
    mins = re.search(r"(\d+) min read", text)
    date = datetime.strptime(fname[:10], "%Y-%m-%d").strftime("%B %-d, %Y")
    return {"file": fname, "headline": plain(h1), "deck": deck,
            "date": date, "mins": mins.group(1) if mins else None}


def shell_for(title, desc, url, meta_strong, meta_sub):
    p = shell
    p = p.replace("<title>Archive — Daily Tech Briefing</title>", f"<title>{title}</title>")
    p = p.replace('content="Every story from every Daily Tech Briefing, newest first — each linked to the original reporting."',
                  f'content="{desc}"')
    p = p.replace('<meta property="og:title" content="Archive — Daily Tech Briefing" />',
                  f'<meta property="og:title" content="{title}" />')
    p = p.replace('<meta property="og:url" content="https://dtbrief.com/archive.html" />',
                  f'<meta property="og:url" content="{url}" />')
    p = p.replace('<link rel="icon" type="image/svg+xml" href="favicon.svg" />',
                  '<link rel="icon" type="image/svg+xml" href="../favicon.svg" />')
    p = p.replace('<a class="brand" href="index.html"', '<a class="brand" href="../index.html"')
    p = re.sub(r"<strong>Archive</strong><br />\s*Every story, newest first",
               f"<strong>{meta_strong}</strong><br />\n          {meta_sub}", p)
    p = p.replace('<a href="index.html" data-nav="top">', '<a href="../index.html" data-nav="top">')
    p = p.replace('<a href="archive.html" data-nav="latest" class="active">', '<a href="../archive.html" data-nav="latest">')
    p = p.replace('<a href="learn/" data-nav="learn">', '<a href="../learn/" data-nav="learn">')
    p = p.replace('  <script src="search.js" defer></script>\n', '')
    return p


def article(kicker, h1, deck, byline_note, cards_html):
    body = ['      <article>',
            '        <div class="dateline-row">',
            f'          <span class="kicker">{kicker}</span>',
            '        </div>', '',
            f'        <h1>{h1}</h1>', '',
            f'        <p class="deck">{deck}</p>', '',
            '        <div class="byline">',
            '          <span class="who">Daily Tech Briefing</span>',
            '          <span class="dot" aria-hidden="true"></span>',
            f'          <span>{byline_note}</span>',
            '        </div>', '',
            cards_html, '',
            '        ' + NEWSLETTER,
            '      </article>']
    return "\n".join(body)


def card(href, kicker, headline, deck_html, meta):
    return (f'        <a class="post-card" href="{href}">\n'
            f'          <span class="kicker">{kicker}</span>\n'
            f'          <h3>{headline}</h3>\n'
            f'          <p>{deck_html}</p>\n'
            f'          <span class="meta">{meta}</span>\n'
            f'        </a>')


def write_page(fname, page_shell, article_html):
    p, n = re.subn(r"      <article>.*?</article>", lambda _: article_html,
                   page_shell, count=1, flags=re.S)
    assert n == 1, f"article replace failed: {fname}"
    out = os.path.join(ROOT, "sections", fname)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(p)
    print("wrote sections/" + fname, len(p))


by_topic = {key: [] for key, _, _ in SECTIONS}
for fname, key in topics.items():
    assert key in by_topic, f"unknown topic {key} for {fname}"
    by_topic[key].append(post_info(fname))
for key in by_topic:
    by_topic[key].sort(key=lambda x: x["file"], reverse=True)

all_posts = {os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "posts", "*.html"))}
missing = all_posts - set(topics)
if missing:
    print("WARNING unclassified posts:", sorted(missing))

for key, name, desc in SECTIONS:
    infos = by_topic[key]
    cards = "\n".join(
        card(f"../posts/{i['file']}", html.escape(name), html.escape(i["headline"]),
             i["deck"],
             i["date"] + (f" &middot; {i['mins']} min read" if i["mins"] else ""))
        for i in infos)
    write_page(f"{key}.html",
               shell_for(f"{name} — Daily Tech Briefing", desc,
                         f"https://dtbrief.com/sections/{key}.html", name, "Section"),
               article("Section", html.escape(name), html.escape(desc),
                       f"{len(infos)} {'story' if len(infos) == 1 else 'stories'}", cards))

overview = []
for key, name, desc in SECTIONS:
    infos = by_topic[key]
    latest = infos[0]["date"] if infos else "—"
    overview.append(card(f"{key}.html", "Section", html.escape(name), html.escape(desc),
                         f"{len(infos)} {'story' if len(infos) == 1 else 'stories'} &middot; Latest: {latest}"))
total = sum(len(v) for v in by_topic.values())
write_page("index.html",
           shell_for("Sections — Daily Tech Briefing",
                     "Browse the Daily Tech Briefing by topic: AI, chips and hardware, big tech, business and markets, security and privacy.",
                     "https://dtbrief.com/sections/", "Sections", "Browse by topic"),
           article("Sections", "Browse by topic",
                   "Every Daily Tech Briefing story, sorted into the five beats we cover.",
                   f"5 sections &middot; {total} stories",
                   "\n".join(overview)))
print("sections done:", {k: len(v) for k, v in by_topic.items()}, "total", total)
