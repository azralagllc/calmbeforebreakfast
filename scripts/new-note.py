#!/usr/bin/env python3
"""Create or update a note page, then refresh the sitemap, notes index, and RSS feed."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "_templates" / "note.html"
NOTES_DIR = ROOT / "notes"
NOTES_INDEX = NOTES_DIR / "index.html"
SITEMAP = ROOT / "sitemap.xml"
FEED = ROOT / "feed.xml"
SITE = "https://calmbeforebreakfast.com"

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DASH_RE = re.compile(r"[\u2012\u2013\u2014\u2015]")
INLINE_RE = re.compile(
    r"\*\*(.+?)\*\*|\[([^\]]+)\]\((https://calmbeforebreakfast\.com/[^)]+)\)"
)
JSON_LD_RE = re.compile(r'<script type="application/ld\+json">.*?</script>', re.S)
NOTES_START = "<!-- notes:start -->"
NOTES_END = "<!-- notes:end -->"

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ATOM_NS = "http://www.w3.org/2005/Atom"
RSS_ITEM_TAG = "item"


def die(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def html_escape(value: str) -> str:
    return html.escape(value, quote=True)


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        die(f"Dates must be YYYY-MM-DD, got {value!r}.")


def display_date(value: date) -> str:
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def rfc822(value: date) -> str:
    stamped = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return stamped.strftime("%a, %d %b %Y %H:%M:%S +0000")


def reject_dashes(label: str, value: str) -> None:
    if DASH_RE.search(value):
        die(f"{label} contains an em dash or en dash. Use a comma, a colon, or a period instead.")


def parse_related_lines(text: str, label: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" not in line:
            die(f"{label} should look like 'slug | Title', got {line!r}.")
        slug, title = [bit.strip() for bit in line.split("|", 1)]
        if not SLUG_RE.match(slug):
            die(f"Invalid related slug {slug!r}.")
        if not title:
            die(f"Related note {slug} is missing a title.")
        reject_dashes(f"Related title for {slug}", title)
        items.append((slug, title))
    return items


def parse_body(text: str) -> tuple[str, str, list[tuple[str, str]]]:
    text = text.replace("\r\n", "\n").strip()
    if not text:
        die("The body file is empty.")
    reject_dashes("The body file", text)

    chunks = re.split(r"(?m)^##\s+", text)
    unpacking_src = chunks[0].strip()
    try_src = ""
    related: list[tuple[str, str]] = []

    for chunk in chunks[1:]:
        heading, _, rest = chunk.partition("\n")
        key = re.sub(r"\s+", " ", heading).strip().lower().rstrip(":")
        rest = rest.strip()
        if key in {"try this today", "try this"}:
            try_src = rest
        elif key in {"related", "related notes"}:
            related = parse_related_lines(rest, "Related notes")
        else:
            die(
                f"Unknown body heading {heading.strip()!r}. "
                "Use '## Try this today' or '## Related'."
            )

    if not unpacking_src:
        die("The body file needs an unpacking section before any headings.")
    if not try_src:
        die("The body file needs a '## Try this today' section.")

    return markdownish(unpacking_src), markdownish(try_src), related


def markdownish(text: str) -> str:
    blocks = re.split(r"\n\s*\n", text.strip())
    paragraphs: list[str] = []
    for block in blocks:
        paragraph = " ".join(line.strip() for line in block.splitlines() if line.strip())
        if paragraph:
            paragraphs.append(f"<p>{inline_format(paragraph)}</p>")
    if not paragraphs:
        die("A body section did not have any paragraphs.")
    return "\n          ".join(paragraphs)


def inline_format(text: str) -> str:
    parts: list[str] = []
    cursor = 0
    for match in INLINE_RE.finditer(text):
        if match.start() > cursor:
            parts.append(html_escape(text[cursor:match.start()]))
        if match.group(1) is not None:
            parts.append(f"<strong>{html_escape(match.group(1))}</strong>")
        else:
            label, url = match.group(2), match.group(3)
            parts.append(f'<a href="{html_escape(url)}">{html_escape(label)}</a>')
        cursor = match.end()
    parts.append(html_escape(text[cursor:]))
    return "".join(parts)


def related_html(items: list[tuple[str, str]]) -> str:
    lines = [
        f'<li><a href="{html_escape(f"{SITE}/notes/{slug}/")}">{html_escape(title)}</a></li>'
        for slug, title in items
    ]
    return ("\n          ".join(lines) + "\n          ") if lines else ""


def build_json_ld(
    slug: str,
    title: str,
    meta: str,
    published: date,
    modified: date,
    quote: str,
    author: str,
    work: str,
    translator: str,
) -> str:
    payload = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "@id": f"{SITE}/notes/{slug}/#article",
                "headline": title,
                "description": meta,
                "url": f"{SITE}/notes/{slug}/",
                "mainEntityOfPage": f"{SITE}/notes/{slug}/",
                "datePublished": published.isoformat(),
                "dateModified": modified.isoformat(),
                "image": f"{SITE}/og.png",
                "inLanguage": "en-US",
                "isAccessibleForFree": True,
                "author": {
                    "@type": "Organization",
                    "name": "Calm Before Breakfast",
                    "url": f"{SITE}/",
                },
                "publisher": {"@id": f"{SITE}/#org"},
            },
            {
                "@type": "Quotation",
                "text": quote,
                "creator": {"@type": "Person", "name": author},
                "isPartOf": {
                    "@type": "CreativeWork",
                    "name": work,
                    "translator": {"@type": "Person", "name": translator},
                },
            },
        ],
    }
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f'<script type="application/ld+json">{serialized}</script>'


def render_page(
    template: str,
    *,
    slug: str,
    title: str,
    meta: str,
    published: date,
    modified: date,
    quote: str,
    author: str,
    work: str,
    translator: str,
    unpacking: str,
    try_this: str,
    related: list[tuple[str, str]],
) -> str:
    if not JSON_LD_RE.search(template):
        die("The note template is missing its JSON-LD script tag.")

    page = JSON_LD_RE.sub(
        build_json_ld(
            slug,
            title,
            meta,
            published,
            modified,
            quote,
            author,
            work,
            translator,
        ),
        template,
        count=1,
    )

    # Fill template slots before inserting body copy, so a title or author
    # string cannot be rewritten inside the unpacking or try-this sections.
    if page.count("YYYY-MM-DD") != 1:
        die("Expected one remaining YYYY-MM-DD token for the visible date.")
    page = page.replace("YYYY-MM-DD", published.isoformat())

    for token, value in {
        "DATE_DISPLAY": html_escape(display_date(published)),
        "WORK_BOOK": html_escape(work),
        "TRANSLATOR": html_escape(translator),
        "AUTHOR": html_escape(author),
        "QUOTE": html_escape(quote),
        "TITLE": html_escape(title),
        "META": html_escape(meta),
        "SLUG": html_escape(slug),
    }.items():
        page = page.replace(token, value)

    page = page.replace("RELATED_ITEMS", related_html(related))
    page = page.replace("UNPACKING", unpacking)
    page = page.replace("TRY_THIS", try_this)

    leftover = [
        token
        for token in (
            "DATE_DISPLAY",
            "YYYY-MM-DD",
            "RELATED_ITEMS",
            "UNPACKING",
            "TRY_THIS",
            "WORK_BOOK",
            "TRANSLATOR",
            "TITLE",
            "META",
            "SLUG",
        )
        if token in page
    ]
    # AUTHOR, QUOTE, and WORK can appear naturally in body copy, so they are
    # filled before leftover checks and not treated as an error if they remain
    # only as ordinary words. After replacement they should be gone as tokens
    # in the template slots. A leftover TITLE/META/SLUG is still a bug.
    if leftover:
        die("Unfilled template placeholders remain: " + ", ".join(leftover))

    reject_dashes("The generated note page", page)
    return page


def upsert_sitemap(slug: str, lastmod: date) -> None:
    ET.register_namespace("", SITEMAP_NS)
    tree = ET.parse(SITEMAP)
    root = tree.getroot()
    loc_tag = f"{{{SITEMAP_NS}}}loc"
    lastmod_tag = f"{{{SITEMAP_NS}}}lastmod"
    url_tag = f"{{{SITEMAP_NS}}}url"

    def upsert(loc: str) -> None:
        for url in root.findall(url_tag):
            loc_el = url.find(loc_tag)
            if loc_el is not None and loc_el.text == loc:
                lastmod_el = url.find(lastmod_tag)
                if lastmod_el is None:
                    lastmod_el = ET.SubElement(url, lastmod_tag)
                lastmod_el.text = lastmod.isoformat()
                return
        url = ET.SubElement(root, url_tag)
        loc_el = ET.SubElement(url, loc_tag)
        loc_el.text = loc
        lastmod_el = ET.SubElement(url, lastmod_tag)
        lastmod_el.text = lastmod.isoformat()

    upsert(f"{SITE}/notes/")
    upsert(f"{SITE}/notes/{slug}/")
    ET.indent(tree, space="  ")
    tree.write(SITEMAP, encoding="UTF-8", xml_declaration=True)
    # ElementTree writes a declaration without a newline that matches the file.
    text = SITEMAP.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        SITEMAP.write_text(text + "\n", encoding="utf-8")


def upsert_feed(slug: str, title: str, meta: str, published: date) -> None:
    ET.register_namespace("atom", ATOM_NS)
    tree = ET.parse(FEED)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        die("feed.xml is missing a channel element.")

    link = f"{SITE}/notes/{slug}/"
    existing = None
    for item in list(channel.findall(RSS_ITEM_TAG)):
        guid = item.findtext("guid") or item.findtext("link")
        if guid == link:
            existing = item
            break
    if existing is not None:
        channel.remove(existing)

    item = ET.Element(RSS_ITEM_TAG)
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "link").text = link
    ET.SubElement(item, "guid").text = link
    ET.SubElement(item, "pubDate").text = rfc822(published)
    ET.SubElement(item, "description").text = meta
    channel.append(item)

    items = channel.findall(RSS_ITEM_TAG)
    for item in items:
        channel.remove(item)

    def sort_key(entry: ET.Element) -> str:
        return entry.findtext("pubDate") or ""

    # RFC 822 dates sort incorrectly as strings across months, so parse them.
    def published_stamp(entry: ET.Element) -> datetime:
        raw = entry.findtext("pubDate") or ""
        try:
            return datetime.strptime(raw, "%a, %d %b %Y %H:%M:%S +0000").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

    for item in sorted(items, key=published_stamp, reverse=True):
        channel.append(item)

    ET.indent(tree, space="  ")
    tree.write(FEED, encoding="UTF-8", xml_declaration=True)
    text = FEED.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        FEED.write_text(text + "\n", encoding="utf-8")


def upsert_notes_index(slug: str, title: str, published: date) -> None:
    page = NOTES_INDEX.read_text(encoding="utf-8")
    start = page.find(NOTES_START)
    end = page.find(NOTES_END)
    if start == -1 or end == -1 or end < start:
        die("notes/index.html is missing the notes:start / notes:end markers.")

    inner = page[start + len(NOTES_START) : end]
    pattern = re.compile(
        rf'<li data-slug="{re.escape(slug)}">.*?</li>\n?',
        re.S,
    )
    inner = pattern.sub("", inner)

    item = (
        f'<li data-slug="{html_escape(slug)}">'
        f'<a href="{html_escape(f"{SITE}/notes/{slug}/")}">{html_escape(title)}</a>'
        f'<time datetime="{published.isoformat()}">{html_escape(display_date(published))}</time>'
        f"</li>"
    )

    entries = [line.strip() for line in inner.splitlines() if line.strip()]
    entries = [line for line in entries if f'data-slug="{slug}"' not in line]
    entries.append(item)

    def entry_date(line: str) -> date:
        match = re.search(r'datetime="(\d{4}-\d{2}-\d{2})"', line)
        if not match:
            return date.min
        return date.fromisoformat(match.group(1))

    entries.sort(key=entry_date, reverse=True)
    rebuilt = "\n        " + "\n        ".join(entries) + "\n        "

    page = page[: start + len(NOTES_START)] + rebuilt + page[end:]

    # Reveal the list and hide the empty state once at least one note exists.
    page = page.replace(
        '<p class="empty-notes" data-empty-notes>',
        '<p class="empty-notes" data-empty-notes hidden>',
        1,
    )
    page = page.replace(
        '<ul class="note-list" data-note-list hidden>',
        '<ul class="note-list" data-note-list>',
        1,
    )

    reject_dashes("notes/index.html", page)
    NOTES_INDEX.write_text(page, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or update a Calm Before Breakfast note page."
    )
    parser.add_argument("--slug", required=True, help="URL slug, lowercase with hyphens")
    parser.add_argument("--title", required=True, help="Used for both <title> and H1")
    parser.add_argument("--meta", required=True, help="Unique meta description")
    parser.add_argument("--date", required=True, help="Publish date, YYYY-MM-DD")
    parser.add_argument(
        "--modified",
        help="Last modified date, YYYY-MM-DD. Defaults to --date.",
    )
    parser.add_argument("--quote", required=True, help="Public-domain quotation")
    parser.add_argument("--author", required=True, help="Author of the quotation")
    parser.add_argument(
        "--work",
        required=True,
        help='Work and book, for example "Meditations, Book II"',
    )
    parser.add_argument("--translator", required=True, help="Translator of the quotation")
    parser.add_argument(
        "--body",
        required=True,
        type=Path,
        help="Markdown-ish body file with unpacking, Try this today, and optional Related",
    )
    parser.add_argument(
        "--related",
        action="append",
        default=[],
        help='Related note as "slug | Title". Repeat as needed. Merged with the body file.',
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    slug = args.slug.strip()
    if not SLUG_RE.match(slug):
        die(f"Invalid slug {slug!r}. Use lowercase letters, numbers, and hyphens.")

    for label, value in {
        "title": args.title,
        "meta": args.meta,
        "quote": args.quote,
        "author": args.author,
        "work": args.work,
        "translator": args.translator,
    }.items():
        reject_dashes(label, value)

    published = parse_iso_date(args.date)
    modified = parse_iso_date(args.modified) if args.modified else published
    if not args.body.is_file():
        die(f"Body file not found: {args.body}")

    unpacking, try_this, related = parse_body(args.body.read_text(encoding="utf-8"))
    related.extend(parse_related_lines("\n".join(args.related), "--related"))

    # Keep first occurrence of a slug if it shows up twice.
    deduped: list[tuple[str, str]] = []
    seen: set[str] = set()
    for related_slug, related_title in related:
        if related_slug == slug or related_slug in seen:
            continue
        seen.add(related_slug)
        deduped.append((related_slug, related_title))
    related = deduped

    if not TEMPLATE.is_file():
        die(f"Missing template at {TEMPLATE}")

    page = render_page(
        TEMPLATE.read_text(encoding="utf-8"),
        slug=slug,
        title=args.title,
        meta=args.meta,
        published=published,
        modified=modified,
        quote=args.quote,
        author=args.author,
        work=args.work,
        translator=args.translator,
        unpacking=unpacking,
        try_this=try_this,
        related=related,
    )

    dest_dir = NOTES_DIR / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "index.html").write_text(page, encoding="utf-8")

    upsert_sitemap(slug, modified)
    upsert_feed(slug, args.title, args.meta, published)
    upsert_notes_index(slug, args.title, published)

    print(f"Wrote {dest_dir / 'index.html'}")
    print("Updated sitemap.xml, feed.xml, and notes/index.html.")


if __name__ == "__main__":
    main()
