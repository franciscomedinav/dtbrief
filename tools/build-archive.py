#!/usr/bin/env python3
"""Regenerate archive.html from the daily briefing files.

Reads every ~/workspace/techbriefing/YYYY-MM-DD-briefing.md that has a
published post in posts/, and rebuilds the day sections of archive.html:
newest day first, one section per day, each story a bold linked headline +
outlet credit + date. The page's title, intro, styles, masthead, search box
and footer are left untouched — only the byline (date range + story count),
the browse-list sections and the footer date are regenerated.

Rules (same as the existing hand-built archive):
- ORIGINAL SOURCES RULE: every link must be the ORIGINAL publisher's
  article URL, resolved to its final destination. Never invent a link.
  A story is included only if its Article URL's domain is a known original
  publisher (see archive-overrides.json "outlets"). Stories whose only URL
  is an aggregator/obscure domain are omitted, never guessed.
- Days Oct 23-30, 2026 use the old briefing format (no Article URLs):
  only story #1 is included, with the URL/outlet from that day's post
  source card ("Original reporting" — first link in the card).
- Headlines are rendered in the archive's style: straight quotes become
  curly, and spoken numbers become digits in money/percent/unit contexts
  ("eleven billion dollars" -> "$11 billion", "fifty-nine percent" ->
  "59%", "four thousand meters" -> "4,000 meters"). Bare numbers before
  plain nouns stay spelled out ("about eight months"), matching the
  existing archive. Exact final headlines for the exceptions live in
  archive-overrides.json "headline_overrides" — the exact final headline
  for the few stories where the briefing-derived headline does not match
  the archive (Nov 10 #5-7 use the outlet article's own headline; #2-3
  are briefing headlines with a trailing clause trimmed).

URL replacements for aggregator-sourced stories (a story whose Article URL
is an aggregator but whose original reporting was verified elsewhere) live
in archive-overrides.json "url_replacements". When a future day has an
Article URL from a domain not in "outlets", the script omits that story
and logs it — add a replacement URL (after verifying the original) or an
"outlet" entry, then re-run.

Run after adding a new post (the techbriefing-daily cron does this every
run). Usage:
  python3 tools/build-archive.py [--root DIR] [--briefing-dir DIR]
"""
import glob
import html
import json
import os
import re
import sys
from datetime import date
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_BRIEFING_DIR = os.path.join(os.path.dirname(ROOT), "techbriefing")
OVERRIDES_PATH = os.path.join(HERE, "archive-overrides.json")
ARCHIVE_PATH = os.path.join(ROOT, "archive.html")

# --- spoken-number handling -------------------------------------------------

ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19,
}
TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
SCALES = {"hundred": 100, "thousand": 1_000, "million": 1_000_000,
          "billion": 1_000_000_000, "trillion": 1_000_000_000_000}
NUMBER_WORDS = set(ONES) | set(TENS) | set(SCALES) | {"point"}

# Units after which a spoken number is rendered as digits ("4,000 meters").
UNITS = {
    "meter", "meters", "metre", "metres", "kilometer", "kilometers",
    "kilometre", "kilometres", "mile", "miles", "foot", "feet",
    "inch", "inches", "pound", "pounds", "kilogram", "kilograms",
    "watt", "watts", "kilowatt", "kilowatts", "megawatt", "megawatts",
    "gigawatt", "gigawatts", "terawatt", "terawatts",
}


def _fmt_num(value):
    """Format a parsed number the archive way: commas at >= 1000."""
    if isinstance(value, float) and not value.is_integer():
        s = f"{value:.10f}".rstrip("0").rstrip(".")
        int_part, _, frac = s.partition(".")
        return f"{int(int_part):,}" + (f".{frac}" if frac else "")
    return f"{int(value):,}"


def _parse_number_run(words):
    """Parse a run of number words -> (value, largest million+ scale or None).

    Handles "three hundred thirty million" (330, million), "one point two
    five trillion" (1.25, trillion), "four thousand" (4000, None).
    """
    total = 0.0
    current = 0.0
    largest_scale = None
    i = 0
    while i < len(words):
        w = words[i]
        if w == "point":
            digits = []
            j = i + 1
            while j < len(words) and words[j] in ONES:
                digits.append(str(ONES[words[j]]))
                j += 1
            if digits:
                current += float("0." + "".join(digits))
            i = j
            continue
        if w in ONES:
            current += ONES[w]
        elif w in TENS:
            current += TENS[w]
        elif w == "hundred":
            current *= 100
        elif w in SCALES:
            scale = SCALES[w]
            total += current * scale
            if scale >= 1_000_000:
                largest_scale = w
            current = 0
        i += 1
    value = total + current
    return value, largest_scale


def _display_number(value, scale):
    if scale:
        coeff = value / SCALES[scale]
        return f"{_fmt_num(coeff)} {scale}"
    return _fmt_num(value)


def _expand_token(token):
    """Split a hyphenated token into parts if every part is a number word
    or dollar(s)/percent; otherwise return the token unchanged."""
    if "-" not in token:
        return [token]
    parts = token.split("-")
    if all(p.lower() in NUMBER_WORDS or p.lower() in ("dollar", "dollars", "percent")
           for p in parts):
        return [p.lower() for p in parts]
    return [token]


def convert_spoken_numbers(headline):
    """Convert spoken numbers to digits only in money/percent/unit contexts.

    - number ... dollar(s)  -> "$<n> [scale]"  (dollar word consumed)
    - number percent        -> "<n>%"           (percent consumed)
    - number <unit>         -> "<n> <unit>"
    - number and up         -> "<n> and up"
    Bare numbers before plain nouns are left spelled out, as in the
    existing archive ("about eight months", "one of tech's biggest deals").
    A lone "one" before "of" is never converted.
    """
    tokens = []
    for tok in headline.split(" "):
        tokens.extend(_expand_token(tok))
    out = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.lower() in NUMBER_WORDS:
            run = []
            j = i
            while j < len(tokens) and tokens[j].lower() in NUMBER_WORDS:
                run.append(tokens[j].lower())
                j += 1
            # Lone "one" before "of" is a pronoun, not a number.
            if run == ["one"] and j < len(tokens) and tokens[j].lower() == "of":
                out.append(tok)
                i += 1
                continue
            nxt = tokens[j].lower() if j < len(tokens) else ""
            nxt2 = tokens[j + 1].lower() if j + 1 < len(tokens) else ""
            value, scale = _parse_number_run(run)
            disp = _display_number(value, scale)
            if nxt in ("dollar", "dollars"):
                out.append("$" + disp)
                i = j + 1
            elif nxt == "percent":
                out.append(disp + "%")
                i = j + 1
            elif nxt in UNITS:
                out.append(disp)
                i = j  # keep the unit token; it is copied next round
            elif nxt == "and" and nxt2 == "up":
                out.append(disp)
                i = j
            else:
                out.extend(tokens[i:j])
                i = j
        else:
            out.append(tok)
            i += 1
    return " ".join(out)


def style_headline(headline):
    """Curly quotes + spoken-number conversion, archive style."""
    s = headline.replace("'", "\u2019")
    # Straight double quotes -> curly pairs, in order.
    parts = s.split('"')
    s = parts[0]
    for k, p in enumerate(parts[1:]):
        s += ("\u201c" if k % 2 == 0 else "\u201d") + p
    return convert_spoken_numbers(s)


# --- briefing parsing --------------------------------------------------------

def parse_briefing(path):
    """Return a list of stories: {"num", "headline", "articles": [urls]}."""
    text = open(path, encoding="utf-8").read()
    stories = []
    # Headings are "### N. Headline" (Nov 2+) or "## N. Headline" (Oct 23-30).
    heading_re = re.compile(r"^#{2,3}\s+(\d+)\.\s+(.+)$", re.M)
    matches = list(heading_re.finditer(text))
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[start:end]
        articles = re.findall(r"^Article:\s*(\S+)\s*$", block, re.M)
        stories.append({
            "num": int(m.group(1)),
            "headline": m.group(2).strip(),
            "articles": articles,
        })
    return stories


def source_card_link(post_path):
    """First link in the post's "Original reporting" source card, or None."""
    s = open(post_path, encoding="utf-8").read()
    m = re.search(r'<div class="source-card">(.*?)</div>\s*</div>', s, re.S)
    if not m:
        return None
    link = re.search(r'<a href="([^"]+)"', m.group(1))
    return link.group(1) if link else None


def domain_of(url):
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


# --- rendering ---------------------------------------------------------------

def render_section(day, stories):
    iso = day.isoformat()
    long_date = day.strftime("%A, %B ") + str(day.day) + f", {day.year}"
    short_date = day.strftime("%b ") + str(day.day) + f", {day.year}"
    lines = [f'        <section aria-labelledby="d-{iso}">',
             f'          <h2 id="d-{iso}">{long_date}</h2>']
    for st in stories:
        headline = html.escape(st["headline"], quote=False)
        url = html.escape(st["url"], quote=True)
        lines.append(
            f'          <p><a href="{url}" target="_blank" rel="noopener">'
            f"<strong>{headline}</strong></a> &mdash; {st['outlet']} "
            f"&middot; {short_date}</p>")
    lines.append("        </section>")
    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--briefing-dir", default=DEFAULT_BRIEFING_DIR)
    args = ap.parse_args()

    overrides = json.load(open(OVERRIDES_PATH, encoding="utf-8"))
    outlets = overrides.get("outlets", {})
    url_repl = overrides.get("url_replacements", {})
    headline_over = overrides.get("headline_overrides", {})

    archive_path = os.path.join(args.root, "archive.html")
    current = open(archive_path, encoding="utf-8").read()

    days = {}  # date -> list of included stories
    omitted = []
    for path in sorted(glob.glob(os.path.join(args.briefing_dir,
                                              "????-??-??-briefing.md"))):
        iso = os.path.basename(path)[:10]
        try:
            day = date.fromisoformat(iso)
        except ValueError:
            continue
        posts = sorted(glob.glob(os.path.join(args.root, "posts", f"{iso}-*.html")))
        if not posts:
            continue  # no published post for this day: not in the archive
        stories = parse_briefing(path)
        old_format = not any(st["articles"] for st in stories)
        included = []
        for st in stories:
            if old_format:
                if st["num"] != 1:
                    continue  # no URLs recorded for stories 2+ before Nov 2
                url = source_card_link(posts[0])
                if not url:
                    omitted.append((iso, st["num"], "no source card in post"))
                    continue
            else:
                url = url_repl.get(iso, {}).get(str(st["num"]))
                if url is None:
                    if not st["articles"]:
                        omitted.append((iso, st["num"], "no Article URL"))
                        continue
                    url = st["articles"][0]
            dom = domain_of(url)
            outlet = outlets.get(dom)
            if not outlet:
                omitted.append((iso, st["num"], f"unknown domain {dom}"))
                continue
            headline = style_headline(st["headline"])
            over = headline_over.get(iso, {}).get(str(st["num"]))
            if over:
                headline = over
            included.append({"headline": headline, "url": url, "outlet": outlet})
        if included:
            days[day] = included

    ordered = sorted(days, reverse=True)
    total = sum(len(days[d]) for d in ordered)
    sections = "\n\n".join(render_section(d, days[d]) for d in ordered)

    if ordered:
        first, last = ordered[-1], ordered[0]
        if first == last:
            date_range = f"{first.strftime('%B')} {first.day}, {first.year}"
        elif first.year == last.year and first.month == last.month:
            date_range = (f"{first.strftime('%B')} {first.day} &ndash; "
                          f"{last.day}, {last.year}")
        else:
            date_range = (f"{first.strftime('%B')} {first.day} &ndash; "
                          f"{last.strftime('%B')} {last.day}, {last.year}")
        footer_date = f"{first.strftime('%B')} {first.day}, {first.year}"
    else:
        date_range = ""
        footer_date = ""

    new = current
    m = re.search(
        r'(<div class="byline">.*?<span class="dot"[^>]*></span>\s*<span>)'
        r'[^<]+(</span>.*?<span class="dot"[^>]*></span>\s*<span>)'
        r'\d+ stories?(</span>)', new, re.S)
    if not m:
        print("ERROR: byline block not found in archive.html", file=sys.stderr)
        return 1
    new = new[:m.start()] + m.group(1) + date_range + m.group(2) + \
        f"{total} {'story' if total == 1 else 'stories'}" + m.group(3) + new[m.end():]

    m = re.search(r'(<div id="browse-list">\n).*?(\n        </div>)',
                  new, re.S)
    if not m:
        print("ERROR: browse-list block not found in archive.html", file=sys.stderr)
        return 1
    new = new[:m.start()] + m.group(1) + sections + m.group(2) + new[m.end():]

    m = re.search(r'(<span><a href="index\.html">← All posts</a> · )[^<]+(</span>)', new)
    if not m:
        print("ERROR: footer date not found in archive.html", file=sys.stderr)
        return 1
    new = new[:m.start()] + m.group(1) + footer_date + m.group(2) + new[m.end():]

    if new == current:
        print(f"No changes: archive already current "
              f"({total} stories across {len(ordered)} days).")
    else:
        with open(archive_path, "w", encoding="utf-8") as f:
            f.write(new)
        print(f"Wrote {archive_path}: {total} stories across {len(ordered)} days "
              f"({ordered[-1].isoformat()} to {ordered[0].isoformat()}).")
    for iso, num, why in omitted:
        print(f"OMITTED {iso} #{num}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
