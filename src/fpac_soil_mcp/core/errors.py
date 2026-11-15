"""Base exception hierarchy for fpac-soil-mcp."""


class DomainError(Exception):
    """Base exception for all domain and operational errors in fpac-soil-mcp."""


class ValidationError(DomainError, ValueError):
    """Raised when domain or input validation fails."""


class UpstreamError(DomainError):
    """Raised when an external or upstream service call fails or returns unexpected data."""
