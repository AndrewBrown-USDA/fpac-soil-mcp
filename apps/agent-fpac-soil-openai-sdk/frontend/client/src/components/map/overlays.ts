import type { Map as MapLibreMap } from 'maplibre-gl';

// Fixed context-layer catalog (Plan 44 D5, probes 44.1.2 and 44.8.2). Every URL is a
// string constant; MapLibre fills only `{bbox-epsg-3857}` per tile. The browser loads
// the services directly with simple GETs (no custom headers: TIGERweb's preflight
// has no CORS header).

export const CONTEXT_LABEL = 'Context layer, not an analysis result';

export type OverlayId = 'ssurgo' | 'counties' | 'urban';

export type Overlay = {
  id: OverlayId;
  title: string;
  tiles: string;
  // Below this map zoom the layer is hidden and the control says "Zoom in to see".
  minzoom: number;
  // Display size of one tile in CSS pixels. The service draws labels at a fixed
  // pixel size, so a tile image smaller than `tileSize` enlarges its labels.
  tileSize: number;
  opacity: number;
  source: string;
  vintage: string;
  attribution: string;
};

// SDA WMS ignores DPI parameters (MAP_RESOLUTION, FORMAT_OPTIONS=dpi, DPI; checked
// 2026-11-06), so map unit labels are enlarged by drawing 384 px images on 512 px
// tiles (about 1.33x, slightly soft).
const SSURGO_WMS_TILES =
  'https://SDMDataAccess.sc.egov.usda.gov/Spatial/SDM.wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=mapunitpoly&STYLES=&SRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=384&HEIGHT=384&FORMAT=image/png&TRANSPARENT=true';

// Counties are scale-banded generalized layers (1, 3, 5, ... 13); showing all bands
// draws counties at every zoom from about 7 (layer 1 alone is blank above zoom 14).
const TIGERWEB_COUNTY_TILES =
  'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png32&transparent=true&layers=show:1,3,5,7,9,11,13&f=image';

const TIGERWEB_URBAN_TILES =
  'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Urban/MapServer/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png32&transparent=true&layers=show:0&f=image';

export const OVERLAYS: readonly Overlay[] = [
  {
    id: 'ssurgo',
    title: 'SSURGO soil map units',
    tiles: SSURGO_WMS_TILES,
    minzoom: 12,
    tileSize: 512,
    opacity: 0.8,
    source: 'USDA NRCS Soil Data Access (SDA) WMS',
    vintage: 'SSURGO, current SDA publication',
    attribution: 'USDA NRCS SSURGO',
  },
  {
    id: 'counties',
    title: 'Counties',
    tiles: TIGERWEB_COUNTY_TILES,
    minzoom: 6,
    tileSize: 256,
    opacity: 0.9,
    source: 'US Census Bureau TIGERweb',
    vintage: 'TIGERweb counties (current)',
    attribution: 'US Census Bureau TIGERweb',
  },
  {
    id: 'urban',
    title: 'Census 2020 urban areas',
    tiles: TIGERWEB_URBAN_TILES,
    minzoom: 7,
    tileSize: 256,
    opacity: 0.6,
    source: 'US Census Bureau TIGERweb',
    vintage: 'Census 2020 Urban Areas',
    attribution: 'US Census Bureau TIGERweb',
  },
] as const;

const SOURCE_PREFIX = 'overlay-';
const RESULT_PREFIX = 'result-';

export function overlaySourceId(id: OverlayId): string {
  return `${SOURCE_PREFIX}${id}`;
}

export function overlayIdForSource(sourceId: string | undefined): OverlayId | null {
  if (!sourceId?.startsWith(SOURCE_PREFIX)) return null;
  const id = sourceId.slice(SOURCE_PREFIX.length);
  return OVERLAYS.some((overlay) => overlay.id === id) ? (id as OverlayId) : null;
}

// Overlays sit above the basemap and below server result layers and the AOI outline.
function overlayBeforeId(map: MapLibreMap): string | undefined {
  const result = map.getStyle().layers.find((layer) => layer.id.startsWith(RESULT_PREFIX));
  if (result) return result.id;
  return map.getLayer('aoi-line') ? 'aoi-line' : undefined;
}

export function addOverlay(map: MapLibreMap, overlay: Overlay): void {
  const id = overlaySourceId(overlay.id);
  if (map.getSource(id)) return;
  // A 512 px tile covers what 256 px tiles cover one zoom level higher, so its source
  // zoom range starts one level lower than the map zoom.
  const sourceMinzoom = Math.max(0, overlay.minzoom - Math.log2(overlay.tileSize / 256));
  map.addSource(id, {
    type: 'raster',
    tiles: [overlay.tiles],
    tileSize: overlay.tileSize,
    minzoom: sourceMinzoom,
    maxzoom: 18,
    attribution: overlay.attribution,
  });
  map.addLayer(
    {
      id,
      type: 'raster',
      source: id,
      minzoom: overlay.minzoom,
      paint: { 'raster-opacity': overlay.opacity },
    },
    overlayBeforeId(map),
  );
}

export function removeOverlay(map: MapLibreMap, overlay: Overlay): void {
  const id = overlaySourceId(overlay.id);
  if (map.getLayer(id)) map.removeLayer(id);
  if (map.getSource(id)) map.removeSource(id);
}
