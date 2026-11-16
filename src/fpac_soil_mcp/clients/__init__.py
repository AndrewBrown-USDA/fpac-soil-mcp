"""HTTP and external service client adapters for fpac-soil-mcp."""

from fpac_soil_mcp.clients.cdl import (
    CDLClient,
    CDLVintageUnavailable,
    parse_histogram_payload,
)
from fpac_soil_mcp.clients.http import (
    HttpClientError,
    HttpRequestError,
    HttpStatusError,
    execute_http_request_with_retry,
)
from fpac_soil_mcp.clients.nass import (
    NassClient,
)
from fpac_soil_mcp.clients.tigerweb import (
    DEFAULT_TIGERWEB_COUNTY_URL,
    PerimeterEvidence,
    TigerwebClient,
    TigerwebClientError,
    _esri_rings_to_geometry,
    _lineal_parts,
    _normalize_ring_winding,
    _polygon_to_esri_rings,
    _polygonal_parts,
)

__all__ = [
    "DEFAULT_TIGERWEB_COUNTY_URL",
    "CDLClient",
    "CDLVintageUnavailable",
    "HttpClientError",
    "HttpRequestError",
    "HttpStatusError",
    "NassClient",
    "PerimeterEvidence",
    "TigerwebClient",
    "TigerwebClientError",
    "_esri_rings_to_geometry",
    "_lineal_parts",
    "_normalize_ring_winding",
    "_polygon_to_esri_rings",
    "_polygonal_parts",
    "execute_http_request_with_retry",
    "parse_histogram_payload",
]
