# Research: USDA NASS CDL ImageServer for FPPA Criterion 2

**Document Version**: 1.0.0
**Date**: November 3, 2026
**Target Repository**: `fpac-soil-mcp`
**Purpose**: Refine the Criterion 2 agricultural-land-use recommendation around the USDA NASS Cropland Data Layer (CDL) ArcGIS ImageServer, with `computeStatisticsHistograms` as the preferred backend operation.

---

## Executive Summary

The USDA NASS CDL ArcGIS ImageServer is the strongest practical first implementation for adding recent mapped agricultural-land-use evidence to `fpac-soil-mcp`:

```text
https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer
```

The service provides a standard ArcGIS ImageServer REST interface and may allow polygon statistics to be computed server-side through `computeStatisticsHistograms`. This is preferable to downloading national CDL rasters for every request and running all raster processing locally. The implementation must first inspect the service metadata and catalog dynamically, because year selection, mosaic fields, raster functions, resolution, and enabled operations must not be assumed.

The recommended backend sequence is:

```text
ImageServer metadata/catalog discovery
        ↓
computeStatisticsHistograms for categorical polygon summaries
        ↓ on failure, ambiguity, or unsupported operation
exportImage + local Rasterio/Shapely masking
        ↓ if the ImageServer cannot provide reliable raw CDL values
official CDL raster download or cached snapshot
```

The ImageServer should provide **screening evidence of recent remotely sensed agricultural land cover**, not a definitive finding that land is actively farmed, owned by a producer, legally agricultural, or subject to an official FPPA/LESA determination. It must remain separate from TIGERweb non-urban evidence, SSURGO farmland classification, soil productivity, and NASS county statistics.

Displaying the CDL layer on a map is useful for user reference, but it is a separate UI-oriented concern. The backend should first establish a deterministic evidence contract and analysis method. A later map implementation can expose the ImageServer as a raster overlay without making the visual layer the source of Criterion 2 scoring.

---

## 1. Decision

### 1.1 Recommended primary source

Use the **USDA NASS CDL ImageServer** as the primary current/recent agricultural-land-cover provider for Criterion 2, subject to runtime capability and result-validation checks.

Primary endpoint:

```text
https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer
```

Preferred operation:

```text
POST /computeStatisticsHistograms
```

Fallback operation:

```text
GET /exportImage
```

Independent fallback/corroboration:

* USDA NASS CDL official raster downloads;
* USGS Annual NLCD for broader annual land-cover context;
* documented state or county agricultural-use/assessor data where local authority and terms are explicit;
* NAIP imagery for manual or separately validated visual corroboration.

### 1.2 Why this changes the earlier recommendation

The original recommendation correctly selected CDL as the strongest national source, but treated access primarily as a download/raster-processing problem. The ImageServer introduces a potentially simpler and more operationally suitable path:

* the service can be queried over standard HTTP/REST;
* polygon statistics may be computed server-side;
* the MCP server may avoid maintaining national or state GeoTIFF archives;
* the same endpoint can support diagnostic point identification and optional map display;
* `exportImage` provides a controlled local-processing fallback when server-side behavior is insufficient.

This does not remove the need to validate year selection, raw categorical values, pixel counting, boundary treatment, nodata handling, or temporal metadata.

---

## 2. Source and Evidentiary Semantics

### 2.1 What CDL measures

CDL is a crop-specific remotely sensed land-cover classification for a documented production year. A positive result means that the relevant pixels were classified by the CDL product as one or more configured agricultural/crop classes for that product vintage.

It does not independently establish:

* ownership, tenancy, or farm operation;
* active management on the exact project date;
* planting, harvest, abandonment, or scheduled harvest;
* legal agricultural zoning or tax status;
* conservation-program enrollment;
* FPPA farmland status;
* official NRCS or LESA conclusions.

The result should therefore be labeled:

> Recent mapped agricultural land-cover evidence from USDA NASS CDL.

It should not be labeled:

> Confirmed active agricultural use.

### 2.2 Criterion 2 relationship

Criterion 2 concerns the share of the site perimeter bordering land in nonurban use under 7 CFR § 658.5. TIGERweb can support non-urban context, but “not urban” is not equivalent to “agricultural.” CDL can add spatially relevant current/recent land-cover evidence, but it remains an indirect classification source.

Automated Criterion 2 points should be awarded only when the evidence contract explicitly confirms:

* the source is authoritative;
* the product vintage is current or recent under configured policy;
* the geometry was spatially intersected successfully;
* the selected CDL classes are configured as qualifying agricultural evidence;
* coverage is sufficient;
* the result is reproducible and verified;
* uncertainty and limitations are reported.

SSURGO farmland classes and soil productivity ratings remain separate FPPA soil/capability evidence. NASS QuickStats remains county-scale context. None of those sources should be silently merged into a CDL current-use result.

---

## 3. Dynamic ImageServer Discovery

The provider must inspect the service definition before selecting an analysis method. Do not hard-code that the service has a particular year field, mosaic rule, resolution, raster function, or enabled operation.

### 3.1 Service metadata

Request:

```text
GET https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer?f=json
```

Cache and validate at least:

| Metadata | Use |
|---|---|
| `capabilities` | Determine whether statistics, export, identify, samples, and catalog operations are enabled. |
| `fields` | Discover catalog attributes and avoid assuming a field named `Year`. |
| `timeInfo` | Determine whether years are exposed as a time dimension. |
| `multidimensionalInfo` | Determine whether years are represented as variables/dimensions. |
| `rasterFunctionInfos` | Identify supported server-side functions and avoid applying display-only functions to analysis. |
| `pixelSizeX`, `pixelSizeY` | Record native or service-reported resolution. |
| `spatialReference` | Transform submitted geometry correctly. |
| `pixelType`, `bandCount` | Confirm categorical single-band behavior. |
| `maxImageHeight`, `maxImageWidth` | Bound `exportImage` requests and corridor tiling. |
| `fullExtent` | Check geographic coverage before analysis. |
| service description and copyright/credits | Preserve attribution and provenance. |

The metadata response should be retained in a bounded cache with retrieval timestamp and response hash. A mutable service URL is not sufficient provenance by itself.

### 3.2 Catalog inspection

If the service exposes a mosaic catalog, inspect:

```text
GET https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer/query
```

Example discovery parameters:

```text
where=1=1
outFields=*
returnGeometry=false
f=json
```

The implementation must treat this as an inspection operation, not a production assumption. Catalog records may reveal:

* CDL year or acquisition-year fields;
* item/object identifiers;
* product footprints;
* source raster names;
* acquisition or publication dates;
* processing or version fields.

The provider should select a year using the discovered schema. If no deterministic year-selection mechanism is available, the provider must return `unavailable` rather than silently analyze an unknown or latest mosaic.

### 3.3 Startup versus request-time inspection

Service metadata may be cached at process startup or with a bounded time-to-live. A request should still verify that the required operation and selected year are available. Startup discovery must not turn a temporary service failure into a process-wide fatal dependency.

Recommended states:

* `available`: metadata and required operation are validated;
* `degraded`: metadata is available but a preferred operation is unavailable;
* `unavailable`: metadata, coverage, or year selection cannot be verified;
* `error`: the request failed unexpectedly after a valid configuration was selected.

---

## 4. Preferred Operation: `computeStatisticsHistograms`

### 4.1 Rationale

For categorical CDL analysis, `computeStatisticsHistograms` is the preferred operation because it may return counts of raster cell values intersecting a submitted polygon without requiring the MCP server to download and process a large raster.

Conceptual request:

```text
POST .../ImageServer/computeStatisticsHistograms
```

Typical parameters include:

* `f=json`;
* `geometryType=esriGeometryPolygon`;
* `geometry=<ESRI JSON polygon>`;
* `mosaicRule=<JSON rule>` when needed;
* service-specific raster/statistics parameters discovered from metadata.

The exact parameter names and response shape must be validated against the live service metadata and a fixture captured from the endpoint. Do not assume that a generic ArcGIS example applies unchanged to this service.

### 4.2 Geometry submission

The provider should:

1. Parse and validate input with existing repository geometry helpers.
2. Buffer corridor centerlines in an appropriate projected CRS before analysis.
3. Preserve the actual buffered corridor footprint for the denominator.
4. Transform the polygon to the ImageServer spatial reference.
5. Encode the geometry as Esri JSON.
6. Submit a bounded request with an explicit timeout.
7. Preserve the submitted CRS and geometry hash in provenance.

The service geometry should not be constructed by manually copying arbitrary coordinate arrays without topology validation. Multipart polygons, holes, and corridor end caps must remain intact.

### 4.3 Mosaic/year selection

The provider may need a mosaic rule when multiple CDL years are available. Possible service representations include:

* separate mosaic records selected by an attribute;
* time-enabled imagery;
* multidimensional variables;
* service-specific raster functions;
* a default “latest” mosaic.

An illustrative attribute-based rule might resemble:

```json
{
  "mosaicMethod": "esriMosaicAttribute",
  "sortField": "Year",
  "sortValue": "2025",
  "where": "Year = 2025"
}
```

This is only an example. The implementation must construct the rule from the actual service definition and catalog schema. A default latest mosaic is not sufficient for reproducible Criterion 2 evidence unless the service exposes and returns the selected product vintage.

### 4.4 Histogram validation

Before using histogram bins as CDL class counts, validate:

* bins represent raw CDL class codes rather than RGB/display values;
* the response corresponds to the requested year;
* categorical values have not been bilinearly or cubically resampled;
* nodata values are identifiable and excluded from the valid denominator;
* counts are stable for repeated requests;
* the service’s geometry rasterization rule is understood;
* the response includes enough metadata to reproduce the query.

Use `identify` for known-point diagnostics and compare results with an official CDL raster or a captured reference cell. Use small known polygons to compare histogram counts and expected class values.

### 4.5 Area and ratio calculation

Histogram cell counts should initially be used to calculate class fractions:

```text
qualifying_fraction =
    qualifying_cell_count / valid_cell_count
```

Estimated qualifying acreage can then be calculated as:

```text
estimated_qualifying_acres =
    qualifying_fraction * equal_area_geometry_acres
```

This is an estimate because cell inclusion may use pixel centers, touched cells, or another service-specific rasterization rule. The provider must report that method and must not multiply Web Mercator pixel dimensions directly to obtain acreage.

For Criterion 2 perimeter screening, the preferred boundary metric is:

```text
qualifying_boundary_length / total_boundary_length
```

However, a histogram operation is naturally an area statistic. The provider must not describe a qualifying-area fraction as a perimeter ratio. If the ImageServer cannot provide a defensible boundary-intersection method, use the result as area-based corroboration and leave automated perimeter scoring `unavailable`.

Potential boundary strategies, in increasing complexity:

1. sample points along the boundary and query `identify`;
2. request a narrow boundary band and use histogram fractions;
3. export the raster and locally mask/intersect boundary pixels;
4. polygonize or use fractional raster intersection locally.

The selected method must be versioned and tested against synthetic fixtures.

---

## 5. Fallback: `exportImage` and Local Masking

Use `exportImage` when:

* `computeStatisticsHistograms` is disabled;
* year selection cannot be made reliably server-side;
* the histogram response does not preserve raw CDL codes;
* the service rasterization rule is unclear;
* complex corridors exceed service request limits;
* local processing is required for a defensible boundary method.

Conceptual request:

```text
GET .../ImageServer/exportImage
```

Important parameters include:

* `bbox`;
* `bboxSR`;
* `imageSR`;
* `size`;
* `format=tiff`;
* `pixelType`;
* `interpolation=RSP_NearestNeighbor`;
* `mosaicRule`;
* `f=json`.

The implementation should:

1. calculate a bounded envelope around the analysis geometry;
2. choose output dimensions from the desired source resolution;
3. respect `maxImageWidth` and `maxImageHeight`;
4. tile large corridors without double-counting cells;
5. request nearest-neighbor interpolation;
6. verify that the response contains raw class codes rather than rendered RGB;
7. mask locally with Rasterio and Shapely;
8. exclude nodata from all denominators;
9. calculate area in an equal-area CRS;
10. retain the returned image URL, request parameters, checksum, and metadata.

If `exportImage` only returns a rendered/colorized image, it is unsuitable for automated class counting. Use official CDL raster downloads instead.

---

## 6. Diagnostics and Non-Primary Operations

### 6.1 `identify`

Use `identify` for:

* known-point class verification;
* year-selection diagnostics;
* investigating unexpected histogram values;
* fixture generation and regression checks.

Do not use it as the primary method for summarizing a polygon or corridor.

### 6.2 `getSamples`

Use `getSamples` for:

* diagnostic transects;
* spot checks along corridor boundaries;
* limited sampling when a full raster summary is unavailable.

It should not replace a complete categorical histogram when the requirement is to estimate agricultural coverage.

### 6.3 `query`

ImageServer `query` generally concerns the image/mosaic catalog rather than the CDL cell values. Use it to discover records, footprints, acquisition metadata, and year-selection fields. Do not interpret catalog records as agricultural classification pixels.

---

## 7. CDL Class Policy

The provider must maintain a versioned class policy. It must not treat every non-background CDL class as equivalent agricultural use.

At minimum, return separate categories for:

* annual and row crops;
* perennial crops, orchards, and vineyards;
* hay;
* pasture/grass;
* fallow or idle cropland;
* aquaculture or specialty agricultural classes where applicable;
* non-agricultural classes;
* nodata/unknown.

The Criterion 2 policy should explicitly state which classes qualify for automated agricultural-use evidence. If pasture, hay, fallow, or specialty classes are project-dependent, they should be reported separately and require manual review or an explicit configuration.

The provider must preserve the raw class code and label in the response. It must not collapse classes into a binary value without retaining the underlying evidence.

---

## 8. Proposed MCP Integration

### 8.1 Provider boundary

Add a dedicated provider/client rather than extending `TigerwebClient` or `SDAClient` with CDL-specific behavior. The provider should use the existing shared HTTP helper and injected `httpx.Client` pattern.

Suggested responsibilities:

```text
CDLImageServerClient
    - get_service_metadata()
    - get_catalog_metadata()
    - select_product_year()
    - compute_statistics_histograms()
    - export_image()
    - identify()
    - get_samples()
```

```text
CDLAgriculturalUseProvider
    - analyze_polygon()
    - analyze_buffered_corridor()
    - classify_result_status()
    - apply_class_policy()
    - produce_provenance()
```

The provider should return a typed evidence object compatible with the existing `criterion_2_perimeter_evidence` manifest path, while preserving the distinction between:

* TIGERweb non-urban evidence;
* CDL current/recent land-cover evidence;
* SSURGO farmland-classification evidence;
* NASS county agricultural context.

### 8.2 Suggested operation

An internal provider API could expose:

```python
analyze_cdl_land_use(
    geometry,
    geometry_crs="EPSG:4326",
    years=None,
    method="server_histogram",
    include_boundary_metrics=True,
)
```

This is an implementation proposal, not a public MCP contract. The public tool surface should be chosen only after response models, manifest behavior, documentation, and evaluation fixtures are defined.

### 8.3 Evidence output

The result should include:

* `evidence_status`: `measured`, `unavailable`, `not_provided`, or `error`;
* source agency and dataset;
* ImageServer URL;
* selected operation;
* selected CDL year and layer/catalog identifier;
* service metadata retrieval timestamp;
* request parameters or canonical request hash;
* response/snapshot checksum where available;
* input and analysis geometry hashes;
* source and analysis CRS;
* pixel size and resampling method;
* raw class counts and labels;
* valid and unknown cell counts;
* area fractions and estimated acreage;
* boundary method and perimeter metrics, if validated;
* class-policy version;
* verification flags;
* limitations and error details.

Automated scoring must remain unavailable when required fields are missing or when the method only establishes area-based land-cover evidence but Criterion 2 requires a perimeter-specific ratio.

---

## 9. Offline Testing and Validation

The repository’s existing `httpx.MockTransport` pattern is appropriate for deterministic tests. Capture small, sanitized fixtures for:

1. service metadata;
2. catalog metadata with multiple years;
3. successful histogram response;
4. histogram response containing nodata;
5. malformed or unexpected categorical values;
6. failed year selection;
7. unsupported histogram operation;
8. successful `exportImage` JSON response and tiny GeoTIFF;
9. rendered RGB export that must be rejected for analysis;
10. identify responses for known cells;
11. timeout, 429, 5xx, malformed JSON, and upstream error responses;
12. partial geographic coverage;
13. thin corridors and boundary-sensitive polygons;
14. multipart polygons, holes, and corridor end caps;
15. conflicting annual and multi-year class evidence.

Representative geometry fixtures should include:

* fully qualifying agricultural polygon;
* mixed agricultural/non-agricultural perimeter;
* prime SSURGO soil but non-agricultural CDL;
* pasture/hay and fallow cases;
* corridor narrower than one pixel;
* corridor crossing tile boundaries;
* no-data and unsupported-coverage cases.

Validation should compare:

* histogram class codes against `identify`;
* ImageServer output against a small official CDL raster;
* server histogram fractions against local Rasterio masking;
* repeated requests for deterministic results;
* Web Mercator service behavior against equal-area acreage calculations;
* pixel-center/touched/fractional boundary methods using synthetic rasters.

No live service should be required for the default test suite. Live ImageServer tests should be opt-in and should validate service reachability, metadata drift, and a small known fixture only.

---

## 10. Map Display Is a Separate UI Concern

The ImageServer can also support a visual CDL overlay, but displaying it is not required for backend Criterion 2 analysis.

### Backend responsibility

The MCP/backend should provide:

* source URL and layer metadata;
* selected CDL year;
* attribution and data-vintage text;
* optional raster overlay descriptor;
* bounded geometry and analysis evidence;
* explicit statement that the overlay is reference imagery/classification, not a legal determination.

### UI responsibility

A map client may later add the ImageServer as:

* an ArcGIS raster layer;
* an `exportImage`-backed raster tile/overlay;
* a WMS or equivalent display layer if the service exposes one;
* a map-specific proxy when browser CORS or egress rules require it.

The UI should not reconstruct authoritative CDL evidence from a screenshot or map pixels. It should render the backend’s source/vintage/legend metadata and keep visual display separate from the scoring result.

This fits the existing spatial-visualization strategy: authoritative analysis should come from server-returned, provenance-bearing results, while map overlays are contextual display layers. A future UI task can evaluate MapLibre, raster source configuration, legends, attribution, caching, and accessibility independently.

---

## 11. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Service metadata or catalog schema changes | Discover fields dynamically; cache metadata with version/hash; fail closed when year selection is ambiguous. |
| Histogram returns display/RGB values | Validate against `identify` and official raster fixtures; reject non-categorical output. |
| Unknown pixel inclusion rules | Empirically validate and version the boundary method; use local export fallback where needed. |
| Web Mercator area distortion | Use histogram counts for fractions and calculate acreage from an equal-area geometry. |
| Thin corridor instability | Report pixel size, unknown boundary length, and resolution sensitivity; require manual review or return unavailable. |
| Large/complex geometry request failure | Partition requests deterministically; use `exportImage` tiles; avoid double counting. |
| “No crop pixels” misread as no agriculture | Preserve nodata, unsupported, pasture, fallow, and unknown states separately. |
| CDL classification mistaken for active farming | Use explicit preliminary-screening language and require project-specific/manual evidence for definitive conclusions. |
| Public map overlay treated as scoring evidence | Keep UI overlay metadata and backend evidence/scoring contracts separate. |
| Sensitive farm-location inference | Avoid producer identifiers and raw sensitive joins; return bounded aggregates and provenance only. |

---

## 12. Recommendation and Next Steps

Implement the CDL ImageServer in two backend stages:

1. **Discovery and proof-of-capability**
   * inspect and cache service metadata;
   * inspect the catalog and determine year selection;
   * exercise `computeStatisticsHistograms`;
   * validate raw class codes, nodata, resolution, and geometry behavior;
   * capture deterministic fixtures.

2. **Production provider**
   * add typed CDL evidence models;
   * add server-histogram analysis;
   * add `exportImage` plus local masking fallback;
   * add class policy, temporal checks, coverage rules, and provenance;
   * integrate with `criterion_2_perimeter_evidence`;
   * retain explicit unavailable/error/not-provided behavior;
   * add offline tests before enabling automated scoring.

Defer the CDL map overlay to a separate UI-oriented task. The overlay can reuse the same ImageServer metadata and attribution, but it should not block or redefine the backend evidence contract.

## References

1. [USDA NASS Cropland Data Layer release and national downloads](https://www.nass.usda.gov/Research_and_Science/Cropland/Release/)
2. [ArcGIS ImageServer REST API](https://developers.arcgis.com/rest/services-reference/enterprise/image-service/)
3. [ArcGIS Image Service `computeStatisticsHistograms`](https://developers.arcgis.com/rest/services-reference/enterprise/compute-statistics-histograms/)
4. [ArcGIS Image Service `exportImage`](https://developers.arcgis.com/rest/services-reference/enterprise/export-image/)
5. [ArcGIS Image Service `identify`](https://developers.arcgis.com/rest/services-reference/enterprise/identify/)
6. [ArcGIS Image Service `getSamples`](https://developers.arcgis.com/rest/services-reference/enterprise/get-samples/)
7. [7 C.F.R. § 658.5](https://www.ecfr.gov/current/title-7/section-658.5)
8. [USGS Annual NLCD](https://www.usgs.gov/centers/eros/science/annual-national-land-cover-database)
9. Repository integration points: `src/fpac_soil_mcp/http_client.py`, `src/fpac_soil_mcp/geometry.py`, `src/fpac_soil_mcp/tigerweb_client.py`, `src/fpac_soil_mcp/lesa.py`, `src/fpac_soil_mcp/corridor_analysis.py`, `src/fpac_soil_mcp/polygon_analysis.py`, and `tests/conftest.py`.
