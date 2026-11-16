// Parsing and bounds helpers for the single session-only AOI.
// Nothing here stores or logs geometry.

export type Position = number[];
export type PolygonGeometry =
  | { type: 'Polygon'; coordinates: Position[][] }
  | { type: 'MultiPolygon'; coordinates: Position[][][] };

export type ParseResult =
  | { ok: true; geometry: PolygonGeometry }
  | { ok: false; message: string };

const isPosition = (value: unknown): value is Position =>
  Array.isArray(value) &&
  value.length >= 2 &&
  value.length <= 3 &&
  value.every((n) => typeof n === 'number' && Number.isFinite(n));

const isRing = (value: unknown): value is Position[] =>
  Array.isArray(value) && value.length >= 4 && value.every(isPosition);

const isPolygonCoords = (value: unknown): value is Position[][] =>
  Array.isArray(value) && value.length > 0 && value.every(isRing);

export function toPolygonGeometry(value: unknown): PolygonGeometry | null {
  if (!value || typeof value !== 'object') return null;
  const geometry = value as { type?: unknown; coordinates?: unknown };
  if (geometry.type === 'Polygon' && isPolygonCoords(geometry.coordinates)) {
    return { type: 'Polygon', coordinates: geometry.coordinates };
  }
  if (
    geometry.type === 'MultiPolygon' &&
    Array.isArray(geometry.coordinates) &&
    geometry.coordinates.length > 0 &&
    geometry.coordinates.every(isPolygonCoords)
  ) {
    return {
      type: 'MultiPolygon',
      coordinates: geometry.coordinates as Position[][][],
    };
  }
  return null;
}

/** Accept a Geometry, a Feature, or a FeatureCollection with exactly one feature. */
export function parseAoiText(text: string): ParseResult {
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    return { ok: false, message: 'The input is not valid JSON.' };
  }
  if (!value || typeof value !== 'object') {
    return { ok: false, message: 'Expected a GeoJSON object.' };
  }
  let candidate = value as { type?: unknown; features?: unknown; geometry?: unknown };
  if (candidate.type === 'FeatureCollection') {
    const features = Array.isArray(candidate.features) ? candidate.features : [];
    if (features.length !== 1) {
      return {
        ok: false,
        message: 'A FeatureCollection must contain exactly one feature.',
      };
    }
    candidate = features[0] as typeof candidate;
  }
  if (candidate?.type === 'Feature') {
    candidate = candidate.geometry as typeof candidate;
  }
  const geometry = toPolygonGeometry(candidate);
  if (!geometry) {
    return {
      ok: false,
      message:
        'Only Polygon or MultiPolygon geometry is supported (rings need at least 4 positions).',
    };
  }
  return { ok: true, geometry };
}

export function geometryBounds(
  geometry: PolygonGeometry,
): [[number, number], [number, number]] | null {
  const validGeometry = toPolygonGeometry(geometry);
  if (!validGeometry) return null;
  const polygons =
    validGeometry.type === 'Polygon' ? [validGeometry.coordinates] : validGeometry.coordinates;
  if (!Array.isArray(polygons)) return null;
  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  for (const polygon of polygons) {
    if (!Array.isArray(polygon)) continue;
    for (const ring of polygon) {
      if (!Array.isArray(ring)) continue;
      for (const [x, y] of ring) {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    }
  }
  if (!Number.isFinite(minX)) return null;
  return [
    [minX, minY],
    [maxX, maxY],
  ];
}

export const featureCollection = (geometry: PolygonGeometry | null) => ({
  type: 'FeatureCollection' as const,
  features: geometry
    ? [{ type: 'Feature' as const, properties: {}, geometry }]
    : [],
});

// Same rule as `agent_server/geo.py` `count_vertices`: every ring position counts,
// the closing position included, summed over rings and polygons.
export const MAX_AOI_VERTICES = 2000;

export function countVertices(geometry: PolygonGeometry): number {
  const validGeometry = toPolygonGeometry(geometry);
  if (!validGeometry) return 0;
  const polygons =
    validGeometry.type === 'Polygon' ? [validGeometry.coordinates] : validGeometry.coordinates;
  return polygons.reduce(
    (total, polygon) => total + polygon.reduce((sum, ring) => sum + ring.length, 0),
    0,
  );
}
