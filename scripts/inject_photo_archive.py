#!/usr/bin/env python3
"""Add curated reference links to the Omaezaki photography archive."""

from html import escape
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = "https://omaezakialb.atawi.link"
START = "<!-- PHOTO-ARCHIVE:START -->"
END = "<!-- PHOTO-ARCHIVE:END -->"
GENERATED = re.compile(r"\n?" + re.escape(START) + r".*?" + re.escape(END), re.S)


def page_path(href):
    return ROOT / href.strip("/") / "index.html"


def archive_links(targets, keys):
    return [{"href": ARCHIVE + targets[key]["path"], "label": targets[key]["label"]} for key in keys]


def render_section(group, targets):
    inline = bool(group.get("section"))
    heading = "h3" if inline else "h2"
    title = escape(group["title"])
    note = f'<p class="mini">{escape(group["note"])}</p>' if group.get("note") else ""
    links = "".join(
        f'<li><a href="{escape(link["href"])}" data-track-click="photo_album_context">{escape(link["label"])}</a></li>'
        for link in archive_links(targets, group["links"])
    )
    return (
        f'\n{START}<section class="guide-section archive-reference">'
        f'<{heading}>{title}</{heading}>{note}<ul class="link-list">{links}</ul></section>{END}'
    )


def section_position(page, title, href):
    marker = re.escape(escape(title))
    pattern = rf'<section\b[^>]*>\s*<h2\b[^>]*>{marker}</h2>(?:(?!</?section\b).)*'
    matches = list(re.finditer(pattern, page, re.S))
    if len(matches) != 1 or not page.startswith("</section>", matches[0].end()):
        raise ValueError(f"写真リンクの掲載先を特定できません: {href} / {title}")
    return matches[0].end()


def main_position(page, href):
    match = re.search(r'</div>\s*</main>', page)
    if not match:
        raise ValueError(f"本文末尾が見つかりません: {href}")
    return match.start()


def main():
    spec = json.loads((ROOT / "data/photo-archive-links.json").read_text(encoding="utf-8"))
    targets = spec["targets"]
    place_ids = {place["id"] for place in json.loads((ROOT / "data/places.json").read_text(encoding="utf-8"))}
    if missing := spec["places"].keys() - place_ids:
        raise ValueError(f"施設検索に存在しない施設: {sorted(missing)}")

    paths = {page_path(href): href for href in spec["pages"]}
    for folder in ("life", "discover", "guide", "checklists", "places"):
        for file in (ROOT / folder).rglob("index.html"):
            if file not in paths and START in file.read_text(encoding="utf-8"):
                paths[file] = "/" + file.parent.relative_to(ROOT).as_posix() + "/"

    output = {}
    for file, href in paths.items():
        original = file.read_text(encoding="utf-8")
        page = GENERATED.sub("", original)
        inserts = []
        for group in spec["pages"].get(href, []):
            if section := group.get("section"):
                position = section_position(page, section, href)
            else:
                position = main_position(page, href)
            inserts.append((position, render_section(group, targets)))

        if href == "/places/":
            data = {key: archive_links(targets, links) for key, links in spec["places"].items()}
            payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
            script = f'\n{START}<script type="application/json" id="place-photo-archive">{payload}</script>{END}'
            inserts.append((main_position(page, href), script))

        for position, block in sorted(inserts, reverse=True, key=lambda entry: entry[0]):
            page = page[:position] + block + page[position:]

        if href == "/places/":
            page = re.sub(r'(/assets/enrichment\.js\?v=)[\w-]+', r'\g<1>20261124-archive', page, count=1)
        if page != original:
            output[file] = page

    for file, page in output.items():
        file.write_text(page, encoding="utf-8", newline="\n")

    print(f"御前崎の写真館リンク: {len(spec['pages'])}ページ・施設検索{len(spec['places'])}件")


if __name__ == "__main__":
    main()
