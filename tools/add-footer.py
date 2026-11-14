#!/usr/bin/env python3
"""Inject the shared site footer into every dtbrief.com page (Nov 14, 2026).

Replaces the old minimal <footer> block where one exists, otherwise inserts
the footer immediately before </body>. Idempotent: files already carrying
the <!-- site-footer --> marker are skipped. Relative links get the correct
prefix for the file's depth (root: "", one level down: "../").

Run after adding a page; include changed files in the push."""
import glob, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MARKER = "<!-- site-footer -->"

MARK_SVG = """<svg width="38" height="38" viewBox="0 0 96 96" aria-hidden="true">
            <rect x="4" y="14" width="66" height="66" rx="17" fill="#00C2FF"/>
            <path d="M34 33.5v29c0 2.4 2.6 3.9 4.6 2.6l22.4-14.5c1.9-1.2 1.9-4 0-5.2L38.6 30.9c-2-1.3-4.6.2-4.6 2.6z" fill="#0A0F1E"/>
            <path d="M76 26a17 17 0 0 1 0 22" fill="none" stroke="#FFC800" stroke-width="6.5" stroke-linecap="round"/>
            <path d="M84.5 17.5a29 29 0 0 1 0 39" fill="none" stroke="#FFC800" stroke-width="6.5" stroke-linecap="round" opacity=".45"/>
          </svg>"""

STYLE = """<style>
  footer.site-footer { border-top: none; background: #0A0F1E; color: #EDF1F8; margin-top: 56px; }
  .site-footer-inner { max-width: 1080px; margin: 0 auto; padding: 42px 24px 26px; }
  .site-footer-cols { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr; gap: 30px; }
  @media (max-width: 860px) { .site-footer-cols { grid-template-columns: 1fr 1fr; } }
  .site-footer h4 { font-family: "IBM Plex Mono", monospace; font-size: 12px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: #93A0B8; margin: 0 0 13px; }
  .site-footer-cols a { display: block; color: #EDF1F8; text-decoration: none; font-size: 14.5px; line-height: 1.5; margin-bottom: 9px; }
  .site-footer-cols a:hover { color: #00C2FF; text-decoration: underline; }
  .site-footer-brand { display: flex; gap: 13px; align-items: flex-start; }
  .site-footer-name { font-family: "Sora", sans-serif; font-weight: 800; font-size: 19px; line-height: 1.15; }
  .site-footer-tag { color: #93A0B8; font-size: 13.5px; line-height: 1.55; margin-top: 5px; max-width: 300px; }
  .site-footer-bottom { border-top: 1px solid #22304F; margin-top: 34px; padding-top: 18px; display: flex; justify-content: space-between; gap: 10px 18px; flex-wrap: wrap; font-family: "IBM Plex Mono", monospace; font-size: 12.5px; color: #93A0B8; }
</style>"""


def footer_html(prefix):
    p = prefix
    return f"""{MARKER}
{STYLE}
    <footer class="site-footer">
      <div class="site-footer-inner">
        <div class="site-footer-cols">
          <div>
            <div class="site-footer-brand">
              <span aria-hidden="true">{MARK_SVG}</span>
              <div>
                <div class="site-footer-name">Daily Tech Briefing</div>
                <div class="site-footer-tag">Your daily dose of tech news &mdash; signal, not noise.</div>
              </div>
            </div>
          </div>
          <div>
            <h4>Sections</h4>
            <a href="{p}sections/ai.html">AI</a>
            <a href="{p}sections/chips.html">Chips &amp; Hardware</a>
            <a href="{p}sections/big-tech.html">Big Tech</a>
            <a href="{p}sections/business.html">Business &amp; Markets</a>
            <a href="{p}sections/security.html">Security &amp; Privacy</a>
          </div>
          <div>
            <h4>Site</h4>
            <a href="{p}archive.html">Archive</a>
            <a href="{p}breaking/">Breaking News archive</a>
            <a href="{p}learn/">Learning Center</a>
            <a href="{p}standards.html">How we pick stories</a>
          </div>
          <div>
            <h4>Listen</h4>
            <a href="https://open.spotify.com/show/2ssu27PcFaDaeQkVqPz9ls" target="_blank" rel="noopener">Spotify</a>
            <a href="https://podcasts.apple.com/us/podcast/daily-tech-briefing/id6822945922" target="_blank" rel="noopener">Apple Podcasts</a>
          </div>
          <div>
            <h4>More</h4>
            <a href="{p}advertise.html">Advertise</a>
            <a href="{p}contact.html">Contact</a>
            <a href="{p}privacy.html">Privacy Policy</a>
            <a href="{p}terms.html">Terms of Use</a>
          </div>
        </div>
        <div class="site-footer-bottom">
          <span>&copy; 2026 Daily Tech Briefing &middot; dtbrief.com</span>
          <span>AI-assisted and human-directed.</span>
        </div>
      </div>
    </footer>
<!-- /site-footer -->"""


OLD_FOOTER = re.compile(r'<footer>\s*<div class="footer-inner">.*?</div>\s*</footer>', re.S)

targets = []
for pat in ["*.html", "breaking/index.html", "posts/*.html", "learn/*.html", "sections/*.html"]:
    targets.extend(glob.glob(os.path.join(ROOT, pat)))
targets = sorted(set(t for t in targets if os.path.basename(t) != "404.html"))

changed, skipped = [], []
for path in targets:
    rel = os.path.relpath(path, ROOT)
    depth = len(rel.split(os.sep)) - 1
    prefix = "../" * depth
    text = open(path, encoding="utf-8").read()
    if MARKER in text:
        skipped.append(rel)
        continue
    block = footer_html(prefix)
    if OLD_FOOTER.search(text):
        text = OLD_FOOTER.sub(lambda _: block, text, count=1)
        how = "replaced"
    elif "</body>" in text:
        text = text.replace("</body>", "    " + block + "\n</body>", 1)
        how = "inserted"
    else:
        print("WARN no </body>:", rel)
        continue
    open(path, "w", encoding="utf-8").write(text)
    changed.append(f"{rel} ({how}, prefix '{prefix}')")

print("changed:", len(changed))
for c in changed:
    print("  ", c)
print("skipped (already had footer):", len(skipped), skipped)
