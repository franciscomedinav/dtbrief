#!/usr/bin/env python3
"""Regenerate feed.xml (RSS 2.0) from search-index.json (Pepe, Nov 12, 2026).
Run after adding a post; include feed.xml in the push."""
import json, os
from email.utils import format_datetime
from datetime import datetime, timezone
from xml.sax.saxutils import escape
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://dtbrief.com"
idx = json.load(open(os.path.join(ROOT, "search-index.json"), encoding="utf-8"))

def rfc822(iso):
    dt = datetime.fromisoformat(iso).replace(hour=12, tzinfo=timezone.utc)
    return format_datetime(dt)

items = []
for e in idx:
    url = BASE + "/" + e["url"].lstrip("/")
    items.append(
        "    <item><title>%s</title><link>%s</link><guid isPermaLink=\"true\">%s</guid>"
        "<pubDate>%s</pubDate><description>%s</description></item>"
        % (escape(e["title"]), url, url, rfc822(e["date_iso"]), escape(e["excerpt"])))
newest = idx[0]["date_iso"] if idx else "2026-11-12"
feed = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Daily Tech Briefing</title>
    <link>%s/</link>
    <atom:link href="%s/feed.xml" rel="self" type="application/rss+xml"/>
    <description>The day's top tech story in plain English — what happened, why it matters, and what to watch next. From dtbrief.com.</description>
    <language>en-us</language>
    <lastBuildDate>%s</lastBuildDate>
%s
  </channel>
</rss>
""" % (BASE, BASE, rfc822(newest), "\n".join(items))
open(os.path.join(ROOT, "feed.xml"), "w", encoding="utf-8").write(feed)
print("feed.xml:", len(items), "items")
