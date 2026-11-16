export type ActiveCorridor = {
  corridor_ref: string;
  centerline: { type: 'LineString'; coordinates: number[][] };
  buffer_distance: number;
  buffer_units: 'feet' | 'meters' | 'miles';
  alternatives: { type: 'LineString'; coordinates: number[][] }[];
  indirect_geometry?: Record<string, unknown>;
};

const STORAGE_PREFIX = 'fpac-map-corridor:';
const REF = /^corridor-[0-9a-f]{8}$/;
const MAX_CHARS = 256 * 1024;

function line(value: unknown): value is ActiveCorridor['centerline'] {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as { type?: unknown; coordinates?: unknown };
  return (
    candidate.type === 'LineString' &&
    Array.isArray(candidate.coordinates) &&
    candidate.coordinates.length >= 2 &&
    candidate.coordinates.every(
      (point) =>
        Array.isArray(point) &&
        point.length >= 2 &&
        point.every((n) => typeof n === 'number' && Number.isFinite(n)) &&
        Math.abs(point[0]) <= 180 &&
        Math.abs(point[1]) <= 90,
    )
  );
}

export function isActiveCorridor(value: unknown): value is ActiveCorridor {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const corridor = value as Partial<ActiveCorridor>;
  try {
    if (
      typeof corridor.corridor_ref !== 'string' ||
      !REF.test(corridor.corridor_ref) ||
      !line(corridor.centerline) ||
      typeof corridor.buffer_distance !== 'number' ||
      !Number.isFinite(corridor.buffer_distance) ||
      corridor.buffer_distance <= 0 ||
      !['feet', 'meters', 'miles'].includes(corridor.buffer_units ?? '') ||
      !Array.isArray(corridor.alternatives) ||
      corridor.alternatives.length > 10 ||
      !corridor.alternatives.every(line)
    )
      return false;
    if (corridor.indirect_geometry !== undefined) {
      const geometry = corridor.indirect_geometry;
      if (
        !geometry ||
        !['Polygon', 'MultiPolygon'].includes(String(geometry.type)) ||
        JSON.stringify(geometry).length > MAX_CHARS
      )
        return false;
    }
    return JSON.stringify(value).length <= MAX_CHARS;
  } catch {
    return false;
  }
}

export function loadCorridor(chatId: string): ActiveCorridor | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_PREFIX + chatId);
    if (!raw || raw.length > MAX_CHARS) return null;
    const value: unknown = JSON.parse(raw);
    return isActiveCorridor(value) ? value : null;
  } catch {
    return null;
  }
}

export function saveCorridor(
  chatId: string | null,
  corridor: ActiveCorridor | null,
) {
  if (!chatId) return;
  try {
    if (corridor)
      sessionStorage.setItem(STORAGE_PREFIX + chatId, JSON.stringify(corridor));
    else sessionStorage.removeItem(STORAGE_PREFIX + chatId);
  } catch {
    // Storage may be unavailable; keep the in-memory context usable.
  }
}
