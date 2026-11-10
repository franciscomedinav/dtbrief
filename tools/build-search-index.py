#!/usr/bin/env python3
"""Regenerate search-index.json from the published posts.

Reads every posts/*.html in this blog directory and writes search-index.json
at the site root: title, excerpt, date, episode, spotify id, url — newest first.
Run after adding a new post (the techbriefing-daily cron does this every run).
"""
import glob
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def clean(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip()


def main():
    entries = []
    for path in sorted(glob.glob(os.path.join(ROOT, "posts", "*.html"))):
        name = os.path.basename(path)
        date_iso = name[:10]
        s = open(path, encoding="utf-8").read()
        m = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
        if not m:
            print(f"SKIP {name}: no h1", file=sys.stderr)
            continue
        title = clean(m.group(1))
        m = re.search(r'<p class="deck">(.*?)</p>', s, re.S)
        excerpt = clean(m.group(1)) if m else ""
        m = re.search(r'<div class="byline">(.*?)</div>', s, re.S)
        date = ""
        if m:
            spans = re.findall(r"<span>([^<]+)</span>", m.group(1))
            date = spans[0] if spans else ""
        m = re.search(r'<div class="episode-note">(.*?)</div>\s*</div>', s, re.S)
        ep = None
        spotify = None
        if m:
            em = re.search(r"Episode\s+(\d+)", m.group(1))
            ep = int(em.group(1)) if em else None
            sm = re.search(r"open\.spotify\.com/episode/([A-Za-z0-9]+)", m.group(1))
            spotify = sm.group(1) if sm else None
        entries.append(
            {
                "title": title,
                "excerpt": excerpt,
                "date": date,
                "date_iso": date_iso,
                "episode": ep,
                "spotify": spotify,
                "url": f"posts/{name}",
            }
        )
    entries.sort(key=lambda e: e["date_iso"], reverse=True)
    out = os.path.join(ROOT, "search-index.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Wrote {out}: {len(entries)} entries")


if __name__ == "__main__":
    main()
