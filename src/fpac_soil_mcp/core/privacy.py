"""Public-only data handling and privacy policy enforcement.

Ensures request payloads contain only permitted public/operational project fields
and reject or sanitize sensitive personal information (PII/direct personal contact data).
"""

import copy
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from fpac_soil_mcp.core.errors import ValidationError

# Field names (lowercased) that are strictly prohibited in public FPPA requests
PROHIBITED_PERSONAL_KEY_PATTERNS: frozenset[str] = frozenset(
    {
        "email",
        "email_address",
        "e_mail",
        "phone",
        "phone_number",
        "telephone",
        "cell_phone",
        "mobile_phone",
        "fax",
        "ssn",
        "social_security",
        "tax_id",
        "ein",
        "first_name",
        "last_name",
        "full_name",
        "person_name",
        "contact_name",
        "applicant_name",
        "owner_name",
        "home_address",
        "street_address",
        "address_line1",
        "address_line2",
        "residential_address",
        "zip_code",
        "postal_code",
        "personal_email",
        "personal_phone",
    }
)


class SanitizationResult(BaseModel):
    """Outcome of public-only request payload sanitization."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sanitized_payload: dict[str, Any] = Field(
        description="Deep copy of the payload with all prohibited personal fields removed"
    )
    removed_field_paths: list[str] = Field(
        default_factory=list,
        description="Deterministic list of dotted or indexed paths of fields removed",
    )


def _find_prohibited_paths(data: Any, current_path: str = "") -> list[str]:
    prohibited: list[str] = []
    if isinstance(data, dict):
        for k, v in data.items():
            path = f"{current_path}.{k}" if current_path else str(k)
            k_lower = str(k).strip().lower()
            if k_lower in PROHIBITED_PERSONAL_KEY_PATTERNS:
                prohibited.append(path)
            else:
                prohibited.extend(_find_prohibited_paths(v, path))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            path = f"{current_path}[{idx}]"
            prohibited.extend(_find_prohibited_paths(item, path))
    return prohibited


def validate_public_payload(payload: dict[str, Any]) -> list[str]:
    """Inspect payload for prohibited personal fields without mutating or logging values.

    Returns a sorted list of dotted/indexed paths of prohibited fields found.
    """
    if not isinstance(payload, dict):
        raise TypeError("Payload must be a dictionary.")
    return sorted(_find_prohibited_paths(payload))


class ProhibitedPersonalDataError(ValidationError):
    """Raised when a payload contains sensitive personal data."""

    def __init__(self, prohibited_paths: list[str]) -> None:
        self.prohibited_paths = prohibited_paths
        paths_str = ", ".join(prohibited_paths)
        super().__init__(
            f"Public-only policy violation: Payload contains prohibited personal fields at [{paths_str}]."
        )


def assert_public_payload(payload: dict[str, Any]) -> None:
    """Validate payload against public-only policy, raising an explicit error on violations."""
    violations = validate_public_payload(payload)
    if violations:
        raise ProhibitedPersonalDataError(violations)


def _sanitize_recursive(data: Any, current_path: str = "") -> tuple[Any, list[str]]:
    removed_paths: list[str] = []
    if isinstance(data, dict):
        sanitized_dict: dict[str, Any] = {}
        for k, v in data.items():
            path = f"{current_path}.{k}" if current_path else str(k)
            k_lower = str(k).strip().lower()
            if k_lower in PROHIBITED_PERSONAL_KEY_PATTERNS:
                removed_paths.append(path)
            else:
                sanitized_val, child_removed = _sanitize_recursive(v, path)
                sanitized_dict[k] = sanitized_val
                removed_paths.extend(child_removed)
        return sanitized_dict, removed_paths
    elif isinstance(data, list):
        sanitized_list: list[Any] = []
        for idx, item in enumerate(data):
            path = f"{current_path}[{idx}]"
            sanitized_item, child_removed = _sanitize_recursive(item, path)
            sanitized_list.append(sanitized_item)
            removed_paths.extend(child_removed)
        return sanitized_list, removed_paths
    else:
        return data, []


def sanitize_public_payload(payload: dict[str, Any]) -> SanitizationResult:
    """Sanitize a request payload by stripping prohibited personal data into a new copy.

    Does NOT mutate the original payload.
    """
    if not isinstance(payload, dict):
        raise TypeError("Payload must be a dictionary.")
    payload_copy = copy.deepcopy(payload)
    sanitized, removed = _sanitize_recursive(payload_copy)
    return SanitizationResult(
        sanitized_payload=sanitized,
        removed_field_paths=sorted(removed),
    )
