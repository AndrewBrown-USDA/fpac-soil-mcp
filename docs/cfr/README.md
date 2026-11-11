# CFR Reference Copies

Reference copies of the regulations this server cites, taken from the
Electronic Code of Federal Regulations (eCFR):

| Part | Subject | Source XML | Readable copy |
|---|---|---|---|
| 7 CFR Part 657 | Prime and unique farmlands (important farmland inventory) | `title-7-part-657.xml` | `title-7-part-657.md` |
| 7 CFR Part 658 | Farmland Protection Policy Act (LESA criteria, Site Assessment, corridor rules) | `title-7-part-658.xml` | `title-7-part-658.md` |

`manifest.json` records the eCFR as-of date, each part's latest amendment
date, the source URLs, and the SHA-256 hash of each XML file.

## Use

- Check regulatory wording, point schedules, and citations against these
  files, not against memory or model recall. Cite the section (for example
  `7 CFR 658.5(b)(7)`).
- The XML is the source as served by the eCFR. The Markdown is generated from
  it by `scripts/fetch_ecfr.py`; do not edit either by hand.
- The eCFR is an editorial compilation, not an official legal edition of the
  CFR. These copies support preliminary screening and review only; they do not
  make this service an official FPPA/NRCS determination source.

## Refresh

```bash
make ecfr          # rewrite docs/cfr from the current eCFR text
make ecfr-check    # exit 1 if any stored part differs from the current eCFR text
```

Both targets need network access to `www.ecfr.gov` and use only the Python
standard library. The script defaults to 7 CFR Parts 657 and 658; pass
`--parts`, `--title`, or `--date` for other parts or a point-in-time copy:

```bash
python scripts/fetch_ecfr.py --parts 658 --date 2026-11-06
```

Rerunning with unchanged regulations rewrites identical XML, so the only diffs
are the as-of dates and dated URLs in the Markdown headers and `manifest.json`.
A change in any XML hash means
the regulation text changed: review the diff and every rule that cites it, such
as `src/fpac_soil_mcp/data/site_assessment.v1.json` and
`src/fpac_soil_mcp/constants.py`.

The eCFR versioner API requires an `Accept-Encoding` header that allows
compression for full-text XML (it returns HTTP 406 otherwise); the script sends
one.
