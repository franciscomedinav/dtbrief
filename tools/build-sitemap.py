#!/usr/bin/env python3
"""Regenerate sitemap.xml from the site's pages (Pepe, Nov 12, 2026).
Run after adding a post or lesson; include sitemap.xml in the push."""
import glob, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://dtbrief.com"

def date_of(path):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
    return m.group(1) if m else None

posts = sorted(glob.glob(os.path.join(ROOT, "posts", "*.html")), reverse=True)
lessons = sorted([p for p in glob.glob(os.path.join(ROOT, "learn", "*.html"))
                  if os.path.basename(p) != "index.html"], reverse=True)
newest = max([date_of(p) for p in posts + lessons if date_of(p)] or ["2026-11-12"])

entries = [("/", newest, "daily", "1.0")]
for p in posts:
    entries.append(("/posts/" + os.path.basename(p), date_of(p), "monthly", "0.8"))
entries.append(("/learn/", newest, "weekly", "0.7"))
for p in lessons:
    entries.append(("/learn/" + os.path.basename(p), date_of(p), "monthly", "0.7"))
entries.append(("/archive.html", newest, "daily", "0.5"))
entries.append(("/breaking/", newest, "weekly", "0.6"))
# Professional pack (Nov 14, 2026): sections + trust pages.
entries.append(("/sections/", newest, "weekly", "0.6"))
for slug in ["ai", "chips", "big-tech", "business", "security"]:
    entries.append(("/sections/%s.html" % slug, newest, "weekly", "0.6"))
for page in ["privacy", "terms", "contact", "advertise", "standards"]:
    entries.append(("/%s.html" % page, "2026-11-14", "monthly", "0.4"))

out = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for path, lastmod, freq, prio in entries:
    out.append("  <url><loc>%s%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq><priority>%s</priority></url>"
               % (BASE, path, lastmod, freq, prio))
out.append("</urlset>")
open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("sitemap.xml:", len(entries), "URLs, newest", newest)
