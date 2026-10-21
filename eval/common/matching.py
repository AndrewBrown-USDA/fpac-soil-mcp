"""Text normalization, tool-name matching, and keyword checks for eval scoring."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

_DASHES = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]")
_SPACES = re.compile(r"[\u00a0\u2000-\u200b\u202f\u205f\u3000]")


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


def keywords_present(text: str, keywords: Iterable[str]) -> tuple[bool, list[str]]:
    """Check case-insensitive keyword presence over normalized text.

    Returns ``(all_present, missing_keywords)``.
    """
    haystack = normalize_text(text).lower()
    missing = [kw for kw in keywords if normalize_text(kw).lower() not in haystack]
    return not missing, missing
