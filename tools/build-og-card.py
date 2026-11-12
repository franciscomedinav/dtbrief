#!/usr/bin/env python3
"""Build the site-wide share card (og:image), 1200x630, brand v2.0.
Mark geometry from brand/v2/logo-mark.svg (viewBox 96), drawn like
build_show_cover_v3.py. Output: assets/og-card-1200x630.png"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1200, 630
INK = (10, 15, 30); SIGNAL = (0, 194, 255); VOLT = (255, 200, 0)
WHITE = (255, 255, 255); AIR = (237, 241, 248)
FONTS = "/home/hatch/workspace/youtube/daily-tech-briefing/brand/fonts"
def F(name, size): return ImageFont.truetype(FONTS + "/" + name, size)

img = Image.new("RGB", (W, H), INK)
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse((W - 500, -420, W + 260, 340), fill=(0, 194, 255, 70))
glow = glow.filter(ImageFilter.GaussianBlur(140))
img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
d = ImageDraw.Draw(img)

# --- mark, tile 250px, left ---
MS = 250; S = MS / 96.0
MX, MY = 72, (H - 96 * S) / 2
tx, ty = MX + 4 * S, MY + 14 * S; tw = 66 * S
d.rounded_rectangle((tx, ty, tx + tw, ty + tw), radius=17 * S, fill=SIGNAL)
d.polygon([(MX + 34 * S, MY + 33.5 * S), (MX + 34 * S, MY + 62.5 * S), (MX + 61 * S, MY + 48 * S)], fill=INK)
for (cx, cy, r, alpha) in ((76, 37, 17, 255), (84.5, 37, 29, 115)):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.arc((MX + (cx - r) * S, MY + (cy - r) * S, MX + (cx + r) * S, MY + (cy + r) * S),
           start=-90, end=90, fill=VOLT + (alpha,), width=max(3, int(6.5 * S)))
    img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    d = ImageDraw.Draw(img)

# --- wordmark + tagline, right of the mark ---
X = 470
f_word = F("Sora-ExtraBold.ttf", 104)
while d.textlength("Tech Briefing.", font=f_word) > W - X - 48:
    f_word = F("Sora-ExtraBold.ttf", f_word.size - 2)
d.text((X, 168), "Tech Briefing", font=f_word, fill=WHITE)
w1 = d.textlength("Tech Briefing", font=f_word)
d.text((X + w1, 168), ".", font=f_word, fill=SIGNAL)
f_tag = F("IBMPlexMono-SemiBold.ttf", 30)
d.text((X + 4, 312), "YOUR DAILY DOSE OF TECH NEWS", font=f_tag, fill=VOLT)
d.text((X + 4, 356), "SIGNAL, NOT NOISE.", font=f_tag, fill=VOLT)
f_dom = F("IBMPlexMono-SemiBold.ttf", 26)
d.text((X + 4, 448), "DTBRIEF.COM", font=f_dom, fill=AIR)

os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
out = os.path.join(ROOT, "assets", "og-card-1200x630.png")
img.save(out)
print("saved", out, os.path.getsize(out), "bytes")
