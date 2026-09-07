#!/usr/bin/env python3
"""Validate a Jekyll build without additional packages or network access."""
import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree as ET

root = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
base_path = sys.argv[2].rstrip("/") if len(sys.argv) > 2 else ""
origin = "https://najx.dev"
errors = []

def check(condition, message):
    if not condition:
        errors.append(message)

class Page(HTMLParser):
    def __init__(self, file):
        super().__init__(convert_charrefs=True)
        self.file = file
        self.ids = []
        self.refs = []
        self.images = []
        self.metas = []
        self.h1 = 0
        self.canonicals = []
        self.json_blocks = []
        self.scripts = []
        self.in_json = False
        self.title = ""
        self.in_title = False
        self.lang = ""
        self.feed(file.read_text())

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "html":
            self.lang = a.get("lang", "")
        if tag == "h1":
            self.h1 += 1
        if tag == "title":
            self.in_title = True
        if tag == "img":
            self.images.append(a)
        if tag == "meta":
            self.metas.append(a)
        if tag == "link" and a.get("rel") == "canonical":
            self.canonicals.append(a.get("href", ""))
        if tag == "script":
            self.scripts.append(a.get("src", ""))
            self.in_json = a.get("type") == "application/ld+json"
            if self.in_json:
                self.json_blocks.append("")
        for attr in ("href", "src"):
            if a.get(attr) and tag != "iframe":
                self.refs.append(a[attr])

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "script":
            self.in_json = False

    def handle_data(self, data):
        if self.in_json:
            self.json_blocks[-1] += data
        if self.in_title:
            self.title += data

check(root.is_dir(), f"Missing build directory: {root}")
pages = {p.relative_to(root).as_posix(): Page(p) for p in root.rglob("*.html")}
check(bool(pages), "No HTML pages found")

def page_url(name):
    return origin + base_path + "/" + (name[:-10] if name.endswith("index.html") else name)

def local_target(ref, current):
    url = urlsplit(urljoin(page_url(current), ref))
    if url.netloc != "najx.dev" or url.scheme not in ("http", "https"):
        return None, None
    path = unquote(url.path)
    if base_path and path.startswith(base_path + "/"):
        path = path[len(base_path):]
    target = root / path.lstrip("/")
    if target.is_dir():
        target = target / "index.html"
    return target, unquote(url.fragment)

for name, page in pages.items():
    check(page.h1 == 1, f"{name}: expected one H1, found {page.h1}")
    check(bool(page.title.strip()), f"{name}: missing title")
    check(page.lang in ("en", "en-US", "fr"), f"{name}: invalid language {page.lang!r}")
    check(len(page.ids) == len(set(page.ids)), f"{name}: duplicate IDs")
    check(page.canonicals == [page_url(name)], f"{name}: incorrect canonical {page.canonicals}")
    descriptions = [m.get("content", "") for m in page.metas if m.get("name") == "description"]
    check(len(descriptions) == 1 and bool(descriptions[0]), f"{name}: missing/duplicate description")
    check(len(page.json_blocks) == 1, f"{name}: expected one structured-data block")
    for raw in page.json_blocks:
        try:
            data = json.loads(raw)
            check(data["url"] == page_url(name), f"{name}: schema URL mismatch")
            check(data.get("description"), f"{name}: empty schema description")
            if data["@type"] == "BlogPosting":
                for prop in ("headline", "datePublished", "dateModified", "author", "mainEntityOfPage"):
                    check(bool(data.get(prop)), f"{name}: missing article property {prop}")
                if data.get("image"):
                    target, _ = local_target(data["image"], name)
                    check(target and target.exists(), f"{name}: missing schema image")
        except (ValueError, KeyError) as error:
            errors.append(f"{name}: invalid JSON-LD: {error}")
    check(sum("googletagmanager.com/gtag/js" in src for src in page.scripts) <= 1, f"{name}: duplicate analytics")
    for img in page.images:
        check("alt" in img, f"{name}: image missing alternative text")
        if img.get("src", "").startswith(("/assets/", base_path + "/assets/")):
            check(img["src"].endswith(".svg"), f"{name}: non-vector local image")
            check(img.get("width") and img.get("height"), f"{name}: missing image dimensions")
    for ref in page.refs:
        if ref.startswith(("mailto:", "tel:", "javascript:", "data:")):
            continue
        target, fragment = local_target(ref, name)
        if target is None:
            continue
        check(target.exists(), f"{name}: broken local reference {ref}")
        if target.exists() and fragment and target.suffix == ".html":
            target_page = pages.get(target.relative_to(root).as_posix())
            check(target_page and fragment in target_page.ids, f"{name}: missing anchor {ref}")

svg_files = list((root / "assets").rglob("*.svg"))
check(bool(svg_files), "No SVG assets found")
for file in svg_files:
    try:
        svg = ET.parse(file).getroot()
        ns = "{http://www.w3.org/2000/svg}"
        check(svg.tag == ns + "svg" and svg.get("viewBox"), f"{file}: invalid SVG root")
        check(svg.find(ns + "title") is not None, f"{file}: missing SVG title")
        check(svg.find(".//" + ns + "image") is None, f"{file}: embedded bitmap")
        check(svg.find(".//" + ns + "script") is None, f"{file}: unexpected script")
    except ET.ParseError as error:
        errors.append(f"{file}: {error}")
rasters = [p for p in (root / "assets").rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico")]
check(not rasters, f"Bitmap assets remain: {rasters}")
for file in ("sitemap.xml", "feed.xml"):
    check((root / file).exists(), f"Missing {file}")
    if (root / file).exists():
        ET.parse(root / file)
check((root / "robots.txt").exists(), "Missing robots.txt")
check((root / "CNAME").read_text().strip() == "najx.dev", "Incorrect or missing CNAME")
search = json.loads((root / "assets/search.json").read_text())
post_count = sum('"@type": "BlogPosting"' in block for p in pages.values() for block in p.json_blocks)
check(len(search) == post_count, "Search index does not contain every article")
manifest = json.loads((root / "assets/favicons/site.webmanifest").read_text())
for icon in manifest["icons"]:
    check(icon["type"] == "image/svg+xml" and (root / icon["src"].lstrip("/")).exists(), "Broken manifest icon")
for path, count in Counter(p.canonicals[0] for p in pages.values() if p.canonicals).items():
    check(count == 1, f"Duplicate canonical URL: {path}")

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
print(f"Validated {len(pages)} HTML pages, {post_count} articles and {len(svg_files)} SVG assets: links, anchors, metadata, JSON-LD, feeds, search and manifest.")
