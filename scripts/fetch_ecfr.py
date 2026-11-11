"""Fetch current eCFR text for the regulations this server cites.

Downloads the eCFR versioner XML for each part, then writes, per part:

- ``title-<T>-part-<P>.xml``: the source XML exactly as served (reference copy);
- ``title-<T>-part-<P>.md``: a readable Markdown rendering generated from that XML;
- ``manifest.json``: as-of date, latest amendment date, source URLs, and SHA-256 hashes.

Standard library only, so it runs with any Python 3.11+ interpreter::

    uv run python scripts/fetch_ecfr.py              # refresh docs/cfr
    uv run python scripts/fetch_ecfr.py --check      # exit 1 if docs/cfr is stale
    uv run python scripts/fetch_ecfr.py --parts 658 --date 2026-11-06

The eCFR is an editorial compilation, not an official legal edition of the CFR.
The stored copies are for reference and review only.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

API = "https://www.ecfr.gov/api/versioner/v1"
WEB = "https://www.ecfr.gov"
DEFAULT_TITLE = 7
DEFAULT_PARTS = (657, 658)
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "docs" / "cfr"
USER_AGENT = "fpac-soil-mcp/fetch_ecfr"
TIMEOUT_SECONDS = 60


def _get(url: str, accept: str) -> bytes:
    """GET a URL. The versioner XML endpoint requires an Accept-Encoding header."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": accept, "Accept-Encoding": "gzip"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        body = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    return body


def _get_json(url: str) -> dict:
    return json.loads(_get(url, "application/json"))


def title_as_of(title: int) -> str:
    """Return the date through which the eCFR title is current."""
    titles = _get_json(f"{API}/titles.json")["titles"]
    entry = next(item for item in titles if item["number"] == title)
    return entry["up_to_date_as_of"]


def latest_amendment(title: int, part: int) -> str | None:
    """Return the most recent amendment date recorded for any section of the part."""
    versions = _get_json(f"{API}/versions/title-{title}.json?part={part}")
    dates = [
        v["amendment_date"] for v in versions.get("content_versions", []) if v.get("amendment_date")
    ]
    return max(dates) if dates else None


def xml_url(title: int, part: int, date: str) -> str:
    return f"{API}/full/{date}/title-{title}.xml?part={part}"


# --- XML to Markdown -------------------------------------------------------------

_EMPHASIS = {"I", "E"}
_HEADING_LEVEL = {"DIV5": 1, "DIV6": 2, "DIV8": 3}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _inline(element: ET.Element) -> str:
    parts = [element.text or ""]
    for child in element:
        inner = _inline(child)
        parts.append(f"*{inner.strip()}*" if child.tag in _EMPHASIS and inner.strip() else inner)
        parts.append(child.tail or "")
    return "".join(parts)


def _render(element: ET.Element, blocks: list[str], unknown: set[str]) -> None:
    tag = element.tag
    if tag in _HEADING_LEVEL:
        head = element.find("HEAD")
        if head is not None:
            blocks.append("#" * _HEADING_LEVEL[tag] + " " + _clean(_inline(head)))
        for child in element:
            if child.tag != "HEAD":
                _render(child, blocks, unknown)
    elif tag in {"AUTH", "SOURCE"}:
        label = _clean(_inline(element.find("HED"))) if element.find("HED") is not None else tag
        body = " ".join(_clean(_inline(c)) for c in element if c.tag != "HED")
        blocks.append(f"**{label}** {body}")
    elif tag == "EXTRACT":
        for child in element:
            _render(child, blocks, unknown)
    elif tag.startswith("FP"):
        blocks.append("- " + _clean(_inline(element)))
    elif tag in {"P", "CITA", "NOTE"}:
        blocks.append(_clean(_inline(element)))
    else:
        unknown.add(tag)
        text = _clean(_inline(element))
        if text:
            blocks.append(text)


def to_markdown(xml_bytes: bytes, header: str) -> tuple[str, set[str]]:
    """Render eCFR part XML as Markdown; return text and any unhandled tags."""
    blocks: list[str] = []
    unknown: set[str] = set()
    _render(ET.fromstring(xml_bytes), blocks, unknown)
    lines: list[str] = [header, ""]
    for index, block in enumerate(blocks):
        is_item = block.startswith("- ")
        previous_item = index > 0 and blocks[index - 1].startswith("- ")
        if lines[-1] != "" and not (is_item and previous_item):
            lines.append("")
        lines.append(block)
    return "\n".join(lines).rstrip() + "\n", unknown


# --- Main -----------------------------------------------------------------------


def fetch_part(title: int, part: int, date: str) -> dict:
    url = xml_url(title, part, date)
    xml_bytes = _get(url, "application/xml")
    root = ET.fromstring(xml_bytes)
    head = root.find("HEAD")
    return {
        "part": part,
        "heading": _clean(_inline(head)) if head is not None else f"Part {part}",
        "latest_amendment_date": latest_amendment(title, part),
        "source_xml_url": url,
        "web_url": f"{WEB}/on/{date}/title-{title}/part-{part}",
        "sha256": hashlib.sha256(xml_bytes).hexdigest(),
        "_xml": xml_bytes,
    }


def _read_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise TypeError(f"{path} must contain a JSON object")
    if not isinstance(manifest.get("parts", []), list):
        raise TypeError(f"{path} has an invalid 'parts' list")
    return manifest


def _check_local_copies(
    out_dir: Path, title: int, fetched: list[dict], manifest: dict
) -> list[str]:
    stored_parts = {
        item.get("part"): item
        for item in manifest.get("parts", [])
        if isinstance(item, dict) and isinstance(item.get("part"), int)
    }
    if manifest.get("title", title) != title:
        stored_parts = {}
    stale: list[str] = []
    for item in fetched:
        part = item["part"]
        stored = stored_parts.get(part)
        reasons = []
        if stored is None:
            reasons.append("missing manifest entry")
        elif stored.get("sha256") != item["sha256"]:
            reasons.append("eCFR XML differs from manifest")

        xml_path = out_dir / f"title-{title}-part-{part}.xml"
        if not xml_path.is_file():
            reasons.append("missing local XML")
        elif stored is not None:
            local_hash = hashlib.sha256(xml_path.read_bytes()).hexdigest()
            if local_hash != stored.get("sha256"):
                reasons.append("local XML differs from manifest")

        if reasons:
            stale.append(f"{part} ({', '.join(reasons)})")
    return stale


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--title", type=int, default=DEFAULT_TITLE)
    parser.add_argument(
        "--parts",
        default=",".join(str(p) for p in DEFAULT_PARTS),
        help="Comma-separated part numbers (default: %(default)s)",
    )
    parser.add_argument("--date", help="eCFR point-in-time date (default: title up-to-date-as-of)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output directory")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Write nothing; exit 1 if any stored XML differs from the current eCFR text",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    parts = [int(p) for p in args.parts.split(",") if p.strip()]
    try:
        date = args.date or title_as_of(args.title)
        fetched = [fetch_part(args.title, part, date) for part in parts]
    except (urllib.error.URLError, TimeoutError, StopIteration, KeyError) as error:
        print(f"eCFR request failed: {error}", file=sys.stderr)
        return 2

    manifest_path = args.out / "manifest.json"
    if args.check:
        try:
            stored = _read_manifest(manifest_path)
        except (OSError, json.JSONDecodeError, TypeError) as error:
            print(f"Invalid eCFR manifest: {error}", file=sys.stderr)
            return 2
        stale = _check_local_copies(args.out, args.title, fetched, stored)
        if stale:
            print(f"Stale or missing eCFR copies for title {args.title} parts: {stale}")
            return 1
        print(f"eCFR copies current as of {date} for title {args.title} parts: {parts}")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    try:
        stored = _read_manifest(manifest_path)
    except (OSError, json.JSONDecodeError, TypeError) as error:
        print(f"Invalid eCFR manifest: {error}", file=sys.stderr)
        return 2
    requested_parts = {item["part"] for item in fetched}
    manifest_parts = [
        item
        for item in stored.get("parts", [])
        if isinstance(item, dict)
        and isinstance(item.get("part"), int)
        and item["part"] not in requested_parts
        and stored.get("title", args.title) == args.title
    ]
    for item in fetched:
        stem = f"title-{args.title}-part-{item['part']}"
        xml_bytes = item.pop("_xml")
        (args.out / f"{stem}.xml").write_bytes(xml_bytes)
        header = (
            f"<!-- Generated by scripts/fetch_ecfr.py from {stem}.xml; do not edit by hand. -->\n\n"
            f"> Reference copy of {args.title} CFR Part {item['part']} from the eCFR, current as\n"
            f"> of {date} (latest amendment {item['latest_amendment_date']}). The eCFR is an\n"
            f"> editorial compilation, not an official legal edition of the CFR.\n"
            f"> Source: <{item['web_url']}>"
        )
        markdown, unknown = to_markdown(xml_bytes, header)
        if unknown:
            print(f"Part {item['part']}: unhandled XML tags {sorted(unknown)}", file=sys.stderr)
        (args.out / f"{stem}.md").write_text(markdown, encoding="utf-8")
        manifest_parts.append({**item, "xml_file": f"{stem}.xml", "markdown_file": f"{stem}.md"})
        print(f"Wrote {stem}.xml and {stem}.md ({len(xml_bytes)} bytes XML)")

    manifest = {
        "generated_by": "scripts/fetch_ecfr.py",
        "title": args.title,
        "as_of": date,
        "parts": manifest_parts,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {manifest_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
