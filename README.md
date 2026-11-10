# Calm Before Breakfast

Static signup page for the Calm Before Breakfast daily email. Hosted on GitHub Pages at calmbeforebreakfast.com.

## Local preview

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000

## Adding a note

Notes are static pages at `/notes/<slug>/`. GitHub Pages uses the legacy Jekyll build, so `_templates/` is not published. `scripts/` is listed in `_config.yml` and stays off the site too.

Write a body file with the unpacking first, then a `## Try this today` section. You can add related notes under `## Related`, one `slug | Title` line each, or pass `--related` instead. `**bold**` and links to `https://calmbeforebreakfast.com/...` are the only markup.

```markdown
Marcus wrote this as an emperor bracing for a day of senators. You are bracing for a four-year-old who will declare the blue cup an act of war. Same idea.

## Try this today

Before anyone else is up, name the one moment most likely to go sideways, and decide now how you want to sound when it does.

## Related

how-to-not-yell-at-your-kids | How to Not Yell at Your Kids
morning-routine-with-kids | Morning Routine with Kids
```

From the repo root:

```bash
python3 scripts/new-note.py \
  --slug how-to-stay-calm-with-a-toddler \
  --title "How to Stay Calm with a Toddler This Morning" \
  --meta "A short unique sentence for search and shares." \
  --date 2026-11-10 \
  --quote "Begin the morning by saying to thyself..." \
  --author "Marcus Aurelius" \
  --work "Meditations, Book II" \
  --translator "George Long" \
  --body path/to/body.md
```

The script writes `notes/<slug>/index.html` from `_templates/note.html`, then updates `sitemap.xml`, `notes/index.html`, and `feed.xml`. Running it again for the same slug updates that note in place. Use only public-domain translations for quotations. Do not use em dashes or en dashes, and do not add health or medical claims.

## Before going live

The signup form already posts to Kit form `10168577`:

```
https://app.kit.com/forms/10168577/subscriptions
```

In the Kit form settings, set the success redirect to:

```
https://calmbeforebreakfast.com/thank-you.html
```

The `CNAME` file is already set to `calmbeforebreakfast.com`. After this repo is on GitHub, enable GitHub Pages and point DNS at it.

## Files

- `index.html` and `style.css`: the signup page
- `thank-you.html`: shown after a successful signup
- `confirmed.html`: Kit sends people here after they click the confirmation email
- `notes/index.html`: the list of notes
- `_templates/note.html`: fill-in template used by `scripts/new-note.py`
- `feed.xml`: RSS feed of notes
- `sitemap.xml` and `robots.txt`
- `404.html`: custom not-found page
- `CNAME`: GitHub Pages custom domain
- `favicon.svg` and `og.png`

Copy and colors come from the approved landing draft. Do not use em dashes or en dashes, and do not add health or medical claims.
