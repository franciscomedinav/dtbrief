# Daily Tech Briefing — Blog

The blog companion to the Daily Tech Briefing podcast. Weekday posts take the
day's top story further: what happened, why it matters, and what to watch
next — with a link to the original reporting and to that day's episode.

Live at: https://franciscomedinav.github.io/dtbrief/
Custom domain (when registered): https://dtbrief.com

## How to add a post

1. Copy an existing file under `posts/` and rename it `YYYY-MM-DD-short-slug.html`.
2. Update the headline, deck, body, source link, and episode note.
3. Add a card for it at the top of the "Latest" section in `index.html`.
4. Push to the `main` branch — GitHub Pages rebuilds automatically.

## Design

Shared look across pages: Newsreader serif body, Archivo sans headings,
red accent `#d63a1f`, light/dark via `prefers-color-scheme`. No build step,
no JavaScript framework — plain static HTML, hosted free on GitHub Pages.
