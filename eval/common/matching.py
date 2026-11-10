"""Text normalization, tool-name matching, and keyword checks for eval scoring."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Any

_DASHES = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]")
_SPACES = re.compile(r"[\u00a0\u2000-\u200b\u202f\u205f\u3000]")
# "CFR Part 658", "CFR § 658.5", "CFR §§ 658", "CFR Sec. 658" -> "cfr 658" (lowercased input).
_CFR_UNIT = re.compile(r"\bc\.?f\.?r\.?\s*(?:parts?\b|§§?|sections?\b|sec\.)?\s*")


def normalize_text(text: str) -> str:
    """Apply NFKD normalization and map Unicode dashes and spaces to ASCII."""
    normalized = unicodedata.normalize("NFKD", text)
    normalized = _DASHES.sub("-", normalized)
    return _SPACES.sub(" ", normalized)


def tool_matches(expected: str, called: Iterable[str]) -> bool:
    """Return True if ``expected`` was called exactly or as a client-prefixed name.

    MCP clients often prefix tool names with the server name, for example
    ``fpac-soil_list_farmland_classes`` or ``fpac-soil:list_farmland_classes``.
    """
    suffixes = (f"_{expected}", f":{expected}")
    return any(name == expected or name.endswith(suffixes) for name in called)


def _keyword_form(text: str) -> str:
    """Comparison form: normalized, lowercased, CFR Part/section markers unified."""
    return _CFR_UNIT.sub("cfr ", normalize_text(text).lower())


def _keyword_pattern(form: str) -> re.Pattern[str]:
    """Literal pattern for ``form`` that cannot extend a number at a digit edge."""
    pattern = re.escape(form)
    if form[:1].isdigit():
        pattern = r"(?<!\d)" + pattern
    if form[-1:].isdigit():
        pattern += r"(?!\d)"
    return re.compile(pattern)


def keywords_present(text: str, keywords: Iterable[str]) -> tuple[bool, list[str]]:
    """Check case-insensitive keyword presence over normalized text.

    CFR citations compare by title and part number, so the keyword
    ``7 CFR Part 658`` matches ``7 CFR Part 658``, ``7 CFR § 658.5``, and
    ``7 C.F.R. 658``.

    Numbers are not extended: a keyword that starts with a digit must not be
    preceded by a digit, and one that ends with a digit must not be followed by
    a digit. Any other character, including ``.``, may follow, so ``160``
    matches ``160.`` but not ``1600``, and ``7 CFR`` does not match ``27 CFR``.

    Returns ``(all_present, missing_keywords)``.
    """
    haystack = _keyword_form(text)
    missing = [kw for kw in keywords if not _keyword_pattern(_keyword_form(kw)).search(haystack)]
    return not missing, missing


def value_at_path(payload: Any, path: str) -> Any:
    """Read a dotted path from mappings and list indexes."""
    current = payload
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(path)
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            try:
                current = current[int(part)]
            except IndexError as exc:
                raise KeyError(path) from exc
        else:
            raise KeyError(path)
    return current


def match_expected(actual: Any, expected: dict[str, Any]) -> tuple[bool, str]:
    """Match one deterministic gold-set expectation."""
    path = expected["path"]
    try:
        value = value_at_path(actual, path)
    except KeyError:
        return False, f"{path}: missing"
    if "equals" in expected:
        return (
            value == expected["equals"],
            f"{path}: expected {expected['equals']!r}, got {value!r}",
        )
    if "approx" in expected:
        target = expected["approx"]["value"]
        tolerance = expected["approx"]["abs_tol"]
        ok = isinstance(value, int | float) and abs(value - target) <= tolerance
        return ok, f"{path}: expected {target} ± {tolerance}, got {value!r}"
    if "is_null" in expected:
        ok = (value is None) is expected["is_null"]
        return ok, f"{path}: expected null={expected['is_null']}, got {value!r}"
    raise ValueError(f"{path}: expectation must contain equals, approx, or is_null")
