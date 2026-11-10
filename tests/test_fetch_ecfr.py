import hashlib
import json

from scripts import fetch_ecfr


def _part(part: int, xml: bytes, date: str = "2026-11-06") -> dict:
    return {
        "part": part,
        "heading": f"Part {part}",
        "latest_amendment_date": "2026-01-01",
        "source_xml_url": fetch_ecfr.xml_url(7, part, date),
        "web_url": f"https://www.ecfr.gov/on/{date}/title-7/part-{part}",
        "sha256": hashlib.sha256(xml).hexdigest(),
        "_xml": xml,
    }


def _manifest_part(item: dict) -> dict:
    return {key: value for key, value in item.items() if key != "_xml"} | {
        "xml_file": f"title-7-part-{item['part']}.xml",
        "markdown_file": f"title-7-part-{item['part']}.md",
    }


def test_ecfr_check_detects_missing_and_modified_local_xml(tmp_path, monkeypatch) -> None:
    xml = b"<ROOT />"
    item = _part(657, xml)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"title": 7, "parts": [_manifest_part(item)]}),
        encoding="utf-8",
    )
    (tmp_path / "title-7-part-657.xml").write_bytes(xml)
    monkeypatch.setattr(fetch_ecfr, "fetch_part", lambda *_args: item)

    args = ["--check", "--parts", "657", "--date", "2026-11-06", "--out", str(tmp_path)]
    assert fetch_ecfr.main(args) == 0

    (tmp_path / "title-7-part-657.xml").write_bytes(b"<ROOT changed='yes' />")
    assert fetch_ecfr.main(args) == 1
    (tmp_path / "title-7-part-657.xml").unlink()
    assert fetch_ecfr.main(args) == 1


def test_partial_ecfr_refresh_preserves_unselected_manifest_entries(tmp_path, monkeypatch) -> None:
    old_part = _part(657, b"<OLD />", "2025-01-01")
    refreshed_part = _part(658, b"<NEW />")
    old_entry = _manifest_part(old_part)
    (tmp_path / "title-7-part-657.xml").write_bytes(old_part["_xml"])
    (tmp_path / "title-7-part-657.md").write_text("old markdown", encoding="utf-8")
    (tmp_path / "manifest.json").write_text(
        json.dumps({"title": 7, "as_of": "2025-01-01", "parts": [old_entry]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(fetch_ecfr, "fetch_part", lambda _title, _part, _date: refreshed_part)

    result = fetch_ecfr.main(["--parts", "658", "--date", "2026-11-06", "--out", str(tmp_path)])

    assert result == 0
    stored = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert {item["part"] for item in stored["parts"]} == {657, 658}
    assert next(item for item in stored["parts"] if item["part"] == 657) == old_entry
    assert (tmp_path / "title-7-part-657.xml").read_bytes() == old_part["_xml"]
