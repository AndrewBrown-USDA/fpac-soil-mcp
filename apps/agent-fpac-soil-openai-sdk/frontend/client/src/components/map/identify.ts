import { toPolygonGeometry } from './geojson';
import type { PolygonGeometry } from './geojson';
import type { OverlayId } from './overlays';

// Identify and outline requests for the context overlays (D6, probe 44.1.2). Bases
// are string constants; the only inputs are the clicked point (rounded) and a GEOID
// taken from the service's own answer (digits only). Simple GETs without custom
// headers. Nothing is stored or logged.

const SSURGO_WMS = 'https://SDMDataAccess.sc.egov.usda.gov/Spatial/SDM.wms';
const TIGERWEB_QUERY = {
  counties:
    'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query',
  urban: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Urban/MapServer/0/query',
} as const;

export type AreaOverlayId = keyof typeof TIGERWEB_QUERY;
export type IdentifiableOverlayId = 'ssurgo' | AreaOverlayId;

export type SoilInfo = {
  musym: string | null;
  mukey: string | null;
  areasymbol: string | null;
  acres: string | null;
};

export type AreaInfo = { name: string; geoid: string };

const GEOID = /^\d{1,15}$/;

function mercator(lon: number, lat: number): [number, number] {
  const x = (lon * 20037508.34) / 180;
  const y = Math.log(Math.tan(((90 + lat) * Math.PI) / 360)) * 6378137;
  return [x, y];
}

async function getText(url: string, signal: AbortSignal): Promise<string> {
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error('identify request failed');
  return response.text();
}

// `key = 'value'` lines of the first feature in a `text/plain` GetFeatureInfo answer.
// The header line "GetFeatureInfo results:" is skipped; a feature starts at a
// "Feature <id>:" line.
export function parseFeatureInfo(text: string): Record<string, string> | null {
  const fields: Record<string, string> = {};
  let inFeature = false;
  for (const line of text.split('\n')) {
    if (/^\s*Feature\s+\S+:\s*$/.test(line)) {
      if (inFeature) break;
      inFeature = true;
      continue;
    }
    if (!inFeature) continue;
    const match = /^\s*([A-Za-z_]+)\s*=\s*'(.*)'\s*$/.exec(line);
    if (match) fields[match[1]] = match[2];
  }
  return Object.keys(fields).length > 0 ? fields : null;
}

export async function identifySoil(
  lon: number,
  lat: number,
  signal: AbortSignal,
): Promise<SoilInfo | null> {
  const [x, y] = mercator(lon, lat);
  const half = 150;
  const params = new URLSearchParams({
    SERVICE: 'WMS',
    VERSION: '1.1.1',
    REQUEST: 'GetFeatureInfo',
    LAYERS: 'mapunitpoly',
    QUERY_LAYERS: 'mapunitpoly',
    STYLES: '',
    SRS: 'EPSG:3857',
    BBOX: [x - half, y - half, x + half, y + half].map((n) => n.toFixed(2)).join(','),
    WIDTH: '101',
    HEIGHT: '101',
    X: '50',
    Y: '50',
    INFO_FORMAT: 'text/plain',
    FEATURE_COUNT: '1',
  });
  const fields = parseFeatureInfo(await getText(`${SSURGO_WMS}?${params}`, signal));
  if (!fields) return null;
  return {
    musym: fields.musym ?? null,
    mukey: fields.mukey ?? null,
    areasymbol: fields.areasymbol ?? null,
    acres: fields.muareaacres ?? null,
  };
}

type GeoJsonAnswer = {
  features?: { properties?: Record<string, unknown>; geometry?: unknown }[];
};

async function getJson(url: string, signal: AbortSignal): Promise<GeoJsonAnswer> {
  return JSON.parse(await getText(url, signal)) as GeoJsonAnswer;
}

export async function identifyArea(
  overlay: AreaOverlayId,
  lon: number,
  lat: number,
  signal: AbortSignal,
): Promise<AreaInfo | null> {
  const params = new URLSearchParams({
    geometry: `${lon.toFixed(6)},${lat.toFixed(6)}`,
    geometryType: 'esriGeometryPoint',
    inSR: '4326',
    spatialRel: 'esriSpatialRelIntersects',
    outFields: 'GEOID,NAME',
    returnGeometry: 'false',
    f: 'geojson',
  });
  const answer = await getJson(`${TIGERWEB_QUERY[overlay]}?${params}`, signal);
  const props = answer.features?.[0]?.properties;
  const geoid = typeof props?.GEOID === 'string' ? props.GEOID : null;
  const name = typeof props?.NAME === 'string' ? props.NAME : null;
  if (!geoid || !name || !GEOID.test(geoid)) return null;
  return { name, geoid };
}

export function isAreaOverlayId(id: OverlayId): id is AreaOverlayId {
  return id === 'counties' || id === 'urban';
}

export function isIdentifiableOverlayId(id: OverlayId): id is IdentifiableOverlayId {
  return id === 'ssurgo' || isAreaOverlayId(id);
}

export function identifyOverlaysAtPoint(
  overlays: readonly OverlayId[],
  lon: number,
  lat: number,
  signal: AbortSignal,
): { overlayId: IdentifiableOverlayId; query: Promise<{ soil: SoilInfo | null } | { area: AreaInfo | null }> }[] {
  return overlays.flatMap((overlayId) => {
    if (overlayId === 'ssurgo') {
      return [{ overlayId, query: identifySoil(lon, lat, signal).then((soil) => ({ soil })) }];
    }
    if (isAreaOverlayId(overlayId)) {
      return [{ overlayId, query: identifyArea(overlayId, lon, lat, signal).then((area) => ({ area })) }];
    }
    return [];
  });
}

// The exact outline (no `maxAllowableOffset`): Use as AOI never simplifies (D6).
export async function fetchOutline(
  overlay: AreaOverlayId,
  geoid: string,
  signal: AbortSignal,
): Promise<{ geometry: PolygonGeometry; geoid: string; name: string } | null> {
  if (!GEOID.test(geoid)) return null;
  const params = new URLSearchParams({
    where: `GEOID='${geoid}'`,
    outFields: 'GEOID,NAME',
    returnGeometry: 'true',
    outSR: '4326',
    f: 'geojson',
  });
  const answer = await getJson(`${TIGERWEB_QUERY[overlay]}?${params}`, signal);
  const feature = answer.features?.[0];
  const geometry = toPolygonGeometry(feature?.geometry);
  const properties = feature?.properties;
  const responseGeoid = properties?.GEOID;
  const name = properties?.NAME;
  if (
    !geometry ||
    typeof responseGeoid !== 'string' ||
    responseGeoid !== geoid ||
    typeof name !== 'string'
  ) {
    return null;
  }
  return { geometry, geoid: responseGeoid, name };
}
