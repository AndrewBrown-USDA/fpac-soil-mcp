import type { ActiveCorridor } from './corridorSession';
import type { PolygonGeometry } from './geojson';

export type LineGeometry = ActiveCorridor['centerline'];
export type CorridorUnit = ActiveCorridor['buffer_units'];
export type CorridorInput = Omit<ActiveCorridor, 'corridor_ref'>;

export const DEFAULT_CORRIDOR_UNIT: CorridorUnit = 'feet';

export function isLineGeometry(value: unknown): value is LineGeometry {
  if (!value || typeof value !== 'object') return false;
  const geometry = value as { type?: unknown; coordinates?: unknown };
  return (
    geometry.type === 'LineString' &&
    Array.isArray(geometry.coordinates) &&
    geometry.coordinates.length >= 2 &&
    geometry.coordinates.every(
      (point) =>
        Array.isArray(point) &&
        point.length >= 2 &&
        point.length <= 3 &&
        point.every((number) => typeof number === 'number' && Number.isFinite(number)) &&
        Math.abs(point[0]) <= 180 &&
        Math.abs(point[1]) <= 90,
    )
  );
}

export function isCorridorPolygon(value: unknown): value is PolygonGeometry {
  if (!value || typeof value !== 'object') return false;
  const geometry = value as { type?: unknown; coordinates?: unknown };
  const polygons =
    geometry.type === 'Polygon'
      ? [geometry.coordinates]
      : geometry.type === 'MultiPolygon'
        ? geometry.coordinates
        : null;
  return (
    Array.isArray(polygons) &&
    polygons.length > 0 &&
    polygons.every(
      (polygon) =>
        Array.isArray(polygon) &&
        polygon.length > 0 &&
        polygon.every(
          (ring) =>
            Array.isArray(ring) &&
            ring.length >= 4 &&
            ring[0]?.[0] === ring.at(-1)?.[0] &&
            ring[0]?.[1] === ring.at(-1)?.[1] &&
            ring.every(
              (point) =>
                Array.isArray(point) &&
                point.length >= 2 &&
                point.every((number) => typeof number === 'number' && Number.isFinite(number)) &&
                Math.abs(point[0]) <= 180 &&
                Math.abs(point[1]) <= 90,
            ),
        ),
    )
  );
}

export function combineStagingAreas(areas: readonly PolygonGeometry[]): PolygonGeometry | undefined {
  if (!areas.length || !areas.every(isCorridorPolygon)) return undefined;
  if (areas.length === 1) return areas[0];
  return {
    type: 'MultiPolygon',
    coordinates: areas.flatMap((area) =>
      area.type === 'Polygon' ? [area.coordinates] : area.coordinates,
    ),
  };
}

export function createCorridorInput(
  centerline: unknown,
  alternatives: readonly { label: string; geometry: unknown }[],
  staging: readonly PolygonGeometry[],
  bufferText: string,
  bufferUnits: CorridorUnit,
): CorridorInput | null {
  const bufferDistance = Number(bufferText);
  const indirect_geometry = combineStagingAreas(staging);
  if (
    !isLineGeometry(centerline) ||
    !bufferText.trim() ||
    !Number.isFinite(bufferDistance) ||
    bufferDistance <= 0 ||
    !['feet', 'meters', 'miles'].includes(bufferUnits) ||
    alternatives.length > 10 ||
    alternatives.some(({ label, geometry }) => !label.trim() || !isLineGeometry(geometry)) ||
    (staging.length > 0 && !indirect_geometry)
  ) return null;
  return {
    centerline,
    buffer_distance: bufferDistance,
    buffer_units: bufferUnits,
    alternatives: alternatives.map(({ geometry }) => geometry as LineGeometry),
    ...(indirect_geometry ? { indirect_geometry } : {}),
  };
}

export function corridorReference(): string {
  return `corridor-${crypto.randomUUID().replaceAll('-', '').slice(0, 8)}`;
}

export const BUFFER_SIDE_NOTICE = 'Buffer distance applies on each side of the centerline.';
