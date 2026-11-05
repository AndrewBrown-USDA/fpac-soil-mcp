import type {
  ExpressionSpecification,
  FilterSpecification,
  GeoJSONSourceSpecification,
  Map as MapLibreMap,
} from 'maplibre-gl';

// Types for the ADR 0017 `map` block (src/fpac_soil_mcp/map_contract.py). The browser
// draws what the server sends: geometry, style keys, legends and notes.
export type LegendPattern =
  | 'solid'
  | 'diagonal_hatch'
  | 'cross_hatch'
  | 'dot_stipple'
  | 'outline'
  | 'dashed_outline';

export type MapLegendItem = {
  value: string;
  label: string;
  color: string;
  pattern?: LegendPattern;
  code?: string | null;
};

export type LayerAuthority = 'user_input' | 'machine_estimate' | 'reference_data';

export type MapFeatureCollection = {
  type: 'FeatureCollection';
  features: Array<{
    type: 'Feature';
    geometry: unknown;
    properties?: Record<string, unknown> | null;
  }>;
};

export type MapLayer = {
  id: string;
  title: string;
  kind: 'polygon' | 'line' | 'point';
  delivery: 'inline_geojson' | 'omitted';
  authority: LayerAuthority;
  source: string;
  data_vintage?: string | null;
  style_key?: string | null;
  legend?: MapLegendItem[];
  simplified?: boolean;
  simplify_tolerance_m?: number | null;
  truncated?: boolean;
  feature_count?: number | null;
  feature_collection?: MapFeatureCollection | null;
};

export type MapBlock = {
  display_crs?: string;
  bounds?: [number, number, number, number] | null;
  layers: MapLayer[];
  warnings?: string[];
};

export const AUTHORITY_LABELS: Record<LayerAuthority, string> = {
  user_input: 'Your input',
  machine_estimate: 'Preliminary Machine Estimate',
  reference_data: 'Reference data',
};

// Every source, layer and image this module adds starts with the prefix, so a
// redraw removes exactly the previous result and nothing else (basemap, AOI, draw).
const PREFIX = 'result-';
const FILL_OPACITY = 0.55;
// Outline-only layers (AOI, corridors, counties, urban areas) are thin and partly
// transparent so a narrow fill underneath, such as a corridor strip, stays visible.
const OUTLINE_WIDTH = 1.25;
const OUTLINE_OPACITY = 0.75;
const EDGE_COLOR = '#333333';
const FALLBACK_COLOR = '#424242';
const PATTERNS = ['diagonal_hatch', 'cross_hatch', 'dot_stipple'] as const;
type FillPattern = (typeof PATTERNS)[number];
const PATTERN_SIZE = 16;

function isFillPattern(pattern: LegendPattern | undefined): pattern is FillPattern {
  return (PATTERNS as readonly string[]).includes(pattern ?? '');
}

function isOutline(pattern: LegendPattern | undefined): boolean {
  return pattern === 'outline' || pattern === 'dashed_outline';
}

export function patternImageId(pattern: FillPattern): string {
  return `${PREFIX}pattern-${pattern}`;
}

// Dark marks on a transparent tile, drawn over the class colour fill.
function drawPattern(pattern: FillPattern): ImageData | null {
  const canvas = document.createElement('canvas');
  canvas.width = PATTERN_SIZE;
  canvas.height = PATTERN_SIZE;
  const context = canvas.getContext('2d');
  if (!context) return null;
  context.strokeStyle = 'rgba(0, 0, 0, 0.45)';
  context.fillStyle = 'rgba(0, 0, 0, 0.5)';
  context.lineWidth = 1.5;
  const s = PATTERN_SIZE;
  const diagonal = (flip: boolean) => {
    for (const offset of [-s, 0, s]) {
      context.beginPath();
      if (flip) {
        context.moveTo(offset, 0);
        context.lineTo(offset + s, s);
      } else {
        context.moveTo(offset, s);
        context.lineTo(offset + s, 0);
      }
      context.stroke();
    }
  };
  if (pattern === 'diagonal_hatch') diagonal(false);
  if (pattern === 'cross_hatch') {
    diagonal(false);
    diagonal(true);
  }
  if (pattern === 'dot_stipple') {
    for (const [x, y] of [
      [4, 4],
      [12, 12],
    ]) {
      context.beginPath();
      context.arc(x, y, 1.6, 0, Math.PI * 2);
      context.fill();
    }
  }
  return context.getImageData(0, 0, s, s);
}

function ensurePatternImages(map: MapLibreMap) {
  for (const pattern of PATTERNS) {
    const id = patternImageId(pattern);
    if (map.hasImage(id)) continue;
    const image = drawPattern(pattern);
    if (image) map.addImage(id, image);
  }
}

function keyExpression(styleKey: string): ExpressionSpecification {
  return ['to-string', ['get', styleKey]];
}

// `match` on the style key; a layer without a key (single-entry legend) is constant.
function byValue(
  layer: MapLayer,
  pick: (item: MapLegendItem) => string | number,
  fallback: string | number,
): ExpressionSpecification | string | number {
  const legend = layer.legend ?? [];
  if (!layer.style_key) return legend.length > 0 ? pick(legend[0]) : fallback;
  if (legend.length === 0) return fallback;
  return [
    'match',
    keyExpression(layer.style_key),
    ...legend.flatMap((item) => [item.value, pick(item)]),
    fallback,
  ] as unknown as ExpressionSpecification;
}

// Features whose legend pattern satisfies `test`; with no style key the single
// legend entry decides for the whole layer.
function filterFor(
  layer: MapLayer,
  test: (item: MapLegendItem) => boolean,
  includeUnknown: boolean,
): FilterSpecification | null {
  const legend = layer.legend ?? [];
  if (!layer.style_key) {
    const item = legend[0];
    const passes = item ? test(item) : includeUnknown;
    return passes ? (['all'] as unknown as FilterSpecification) : null;
  }
  const values = legend.filter(test).map((item) => item.value);
  const others = legend.filter((item) => !test(item)).map((item) => item.value);
  if (includeUnknown) {
    return [
      '!',
      ['in', keyExpression(layer.style_key), ['literal', others]],
    ] as unknown as FilterSpecification;
  }
  if (values.length === 0) return null;
  return [
    'in',
    keyExpression(layer.style_key),
    ['literal', values],
  ] as unknown as FilterSpecification;
}

export function inlineLayers(block: MapBlock | null | undefined): MapLayer[] {
  return (block?.layers ?? []).filter(
    (layer) => layer.delivery === 'inline_geojson' && layer.feature_collection,
  );
}

// A layer that draws no fill: lines, points, or polygons whose legend is all outlines.
export function isOutlineOnly(layer: MapLayer): boolean {
  if (layer.kind !== 'polygon') return true;
  const legend = layer.legend ?? [];
  return legend.length > 0 && legend.every((item) => isOutline(item.pattern));
}

// Server layer order is size-cap drop priority, not draw order (ADR 0017). Draw
// filled layers first and outline-only layers above them, each group in server order,
// so corridor and urban outlines are never hidden under the farmland fill.
export function drawOrder(layers: readonly MapLayer[]): MapLayer[] {
  return [
    ...layers.filter((layer) => !isOutlineOnly(layer)),
    ...layers.filter((layer) => isOutlineOnly(layer)),
  ];
}

export function clearMapBlock(map: MapLibreMap) {
  const style = map.getStyle();
  for (const layer of [...(style?.layers ?? [])].reverse()) {
    if (layer.id.startsWith(PREFIX)) map.removeLayer(layer.id);
  }
  for (const id of Object.keys(style?.sources ?? {})) {
    if (id.startsWith(PREFIX)) map.removeSource(id);
  }
}

function addPolygonLayers(map: MapLibreMap, layer: MapLayer, source: string, beforeId?: string) {
  const id = `${PREFIX}${layer.id}`;
  const fill = filterFor(layer, (item) => !isOutline(item.pattern), true);
  if (fill) {
    map.addLayer(
      {
        id: `${id}-fill`,
        type: 'fill',
        source,
        filter: fill,
        paint: {
          'fill-color': byValue(layer, (item) => item.color, FALLBACK_COLOR) as string,
          'fill-opacity': FILL_OPACITY,
        },
      },
      beforeId,
    );
  }
  const patterned = filterFor(layer, (item) => isFillPattern(item.pattern), false);
  if (patterned) {
    map.addLayer(
      {
        id: `${id}-pattern`,
        type: 'fill',
        source,
        filter: patterned,
        paint: {
          'fill-pattern': byValue(
            layer,
            (item) => (isFillPattern(item.pattern) ? patternImageId(item.pattern) : ''),
            '',
          ) as string,
        },
      },
      beforeId,
    );
  }
  const solidEdge = filterFor(layer, (item) => item.pattern !== 'dashed_outline', true);
  if (solidEdge) {
    map.addLayer(
      {
        id: `${id}-line`,
        type: 'line',
        source,
        filter: solidEdge,
        paint: {
          'line-color': byValue(
            layer,
            (item) => (item.pattern === 'outline' ? item.color : EDGE_COLOR),
            EDGE_COLOR,
          ) as string,
          'line-width': byValue(
            layer,
            (item) => (item.pattern === 'outline' ? OUTLINE_WIDTH : 0.5),
            0.5,
          ) as number,
          'line-opacity': byValue(
            layer,
            (item) => (item.pattern === 'outline' ? OUTLINE_OPACITY : 1),
            1,
          ) as number,
        },
      },
      beforeId,
    );
  }
  const dashed = filterFor(layer, (item) => item.pattern === 'dashed_outline', false);
  if (dashed) {
    map.addLayer(
      {
        id: `${id}-dash`,
        type: 'line',
        source,
        filter: dashed,
        paint: {
          'line-color': byValue(layer, (item) => item.color, FALLBACK_COLOR) as string,
          'line-width': OUTLINE_WIDTH,
          'line-opacity': OUTLINE_OPACITY,
          'line-dasharray': [3, 2],
        },
      },
      beforeId,
    );
  }
}

// Draw every inline layer, bottom to top, below `beforeId` (the panel's AOI outline).
export function renderMapBlock(
  map: MapLibreMap,
  block: MapBlock | null | undefined,
  beforeId?: string,
) {
  clearMapBlock(map);
  const layers = drawOrder(inlineLayers(block));
  if (layers.length === 0) return;
  ensurePatternImages(map);
  const below = beforeId && map.getLayer(beforeId) ? beforeId : undefined;
  for (const layer of layers) {
    const source = `${PREFIX}${layer.id}`;
    map.addSource(source, {
      type: 'geojson',
      data: layer.feature_collection as GeoJSONSourceSpecification['data'],
    });
    if (layer.kind === 'polygon') {
      addPolygonLayers(map, layer, source, below);
    } else if (layer.kind === 'line') {
      const dashedLine = (layer.legend ?? [])[0]?.pattern === 'dashed_outline';
      map.addLayer(
        {
          id: `${source}-line`,
          type: 'line',
          source,
          paint: {
            'line-color': byValue(layer, (item) => item.color, FALLBACK_COLOR) as string,
            'line-width': OUTLINE_WIDTH,
            'line-opacity': OUTLINE_OPACITY,
            ...(dashedLine ? { 'line-dasharray': [3, 2] } : {}),
          },
        },
        below,
      );
    } else {
      map.addLayer(
        {
          id: `${source}-circle`,
          type: 'circle',
          source,
          paint: {
            'circle-color': byValue(layer, (item) => item.color, FALLBACK_COLOR) as string,
            'circle-radius': 5,
            'circle-stroke-color': EDGE_COLOR,
            'circle-stroke-width': 1,
          },
        },
        below,
      );
    }
  }
}
