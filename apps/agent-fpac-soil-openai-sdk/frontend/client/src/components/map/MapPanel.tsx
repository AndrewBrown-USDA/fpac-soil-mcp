import { useCallback, useEffect, useRef, useState } from 'react';
import { Map as MapLibreMap } from 'maplibre-gl';
import type { GeoJSONSource, StyleSpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import {
  TerraDraw,
  TerraDrawPolygonMode,
  TerraDrawRectangleMode,
  TerraDrawSelectMode,
} from 'terra-draw';
import { TerraDrawMapLibreGLAdapter } from 'terra-draw-maplibre-gl-adapter';
import { Button } from '@/components/ui/button';
import { GeoJsonInput } from './GeoJsonInput';
import { featureCollection, geometryBounds, toPolygonGeometry } from './geojson';
import type { PolygonGeometry } from './geojson';
import { useMapSummary } from './MapSummaryContext';
import { useScreening } from './useScreening';

// USGS The National Map, USGSTopo cached tiles (ArcGIS order: z/row/col).
// Metadata checked 2026-10-30: 256 px Web Mercator tiles, cached to zoom 16, CORS *.
const USGS_TOPO_TILES =
  'https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}';

const BASE_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    usgsTopo: {
      type: 'raster',
      tiles: [USGS_TOPO_TILES],
      tileSize: 256,
      maxzoom: 16,
      attribution: 'USGS The National Map',
    },
  },
  layers: [{ id: 'usgs-topo', type: 'raster', source: 'usgsTopo' }],
};

// Simple class colours; the full legend arrives with the results view.
const FARMLAND_FILL = [
  'case',
  ['==', ['get', 'farmlndcl'], 'All areas are prime farmland'],
  '#1a9641',
  ['in', 'Prime farmland if', ['coalesce', ['get', 'farmlndcl'], '']],
  '#a6d96a',
  ['in', 'statewide importance', ['coalesce', ['get', 'farmlndcl'], '']],
  '#fdae61',
  ['in', 'local importance', ['coalesce', ['get', 'farmlndcl'], '']],
  '#fee08b',
  ['in', 'unique importance', ['coalesce', ['get', 'farmlndcl'], '']],
  '#d7191c',
  ['==', ['get', 'farmlndcl'], 'Not prime farmland'],
  '#bababa',
  '#7b3294',
] as unknown as string;

type DrawMode = 'polygon' | 'rectangle' | 'select' | 'static';

const emptyCollection = { type: 'FeatureCollection' as const, features: [] };

export function MapPanel() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const drawRef = useRef<TerraDraw | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [mode, setMode] = useState<DrawMode>('static');
  const [aoi, setAoi] = useState<PolygonGeometry | null>(null);
  const [previousAoi, setPreviousAoi] = useState<PolygonGeometry | null>(null);
  const aoiRef = useRef<PolygonGeometry | null>(null);
  const screening = useScreening();
  const { reset: resetScreening } = screening;
  const { offerSummary } = useMapSummary();
  // Only the server-built, geometry-free text goes to chat (ADR 0016); never `display`.
  const summaryText =
    screening.status === 'done' && !screening.result?.display?.error
      ? screening.result?.chat_summary_text
      : undefined;

  // One AOI at a time: a new AOI replaces the old and becomes undoable.
  const replaceAoi = useCallback(
    (next: PolygonGeometry | null) => {
      setPreviousAoi(aoiRef.current);
      aoiRef.current = next;
      setAoi(next);
      resetScreening();
    },
    [resetScreening],
  );

  // Keep Terra Draw holding at most the current AOI (Polygon only; MultiPolygon
  // AOIs are shown by the AOI layer and are not editable).
  const syncDraw = useCallback((geometry: PolygonGeometry | null) => {
    const draw = drawRef.current;
    if (!draw) return;
    draw.clear();
    if (geometry?.type === 'Polygon') {
      draw.addFeatures([
        { type: 'Feature', geometry, properties: { mode: 'polygon' } },
      ]);
    }
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new MapLibreMap({
      container: containerRef.current,
      style: BASE_STYLE,
      center: [-98, 39],
      zoom: 3,
      maxZoom: 18,
      attributionControl: { compact: true },
    });
    mapRef.current = map;

    map.on('load', () => {
      map.addSource('soil', { type: 'geojson', data: emptyCollection });
      map.addLayer({
        id: 'soil-fill',
        type: 'fill',
        source: 'soil',
        paint: { 'fill-color': FARMLAND_FILL, 'fill-opacity': 0.55 },
      });
      map.addLayer({
        id: 'soil-line',
        type: 'line',
        source: 'soil',
        paint: { 'line-color': '#333333', 'line-width': 0.5 },
      });
      map.addSource('aoi', { type: 'geojson', data: emptyCollection });
      map.addLayer({
        id: 'aoi-line',
        type: 'line',
        source: 'aoi',
        paint: { 'line-color': '#1f4e9c', 'line-width': 2.5 },
      });

      const draw = new TerraDraw({
        adapter: new TerraDrawMapLibreGLAdapter({ map }),
        modes: [
          new TerraDrawPolygonMode(),
          new TerraDrawRectangleMode(),
          new TerraDrawSelectMode({
            flags: {
              polygon: {
                feature: {
                  draggable: true,
                  coordinates: {
                    midpoints: true,
                    draggable: true,
                    deletable: true,
                  },
                },
              },
              rectangle: { feature: { draggable: true } },
            },
          }),
        ],
      });
      draw.start();
      draw.on('finish', (id) => {
        const feature = draw.getSnapshot().find((f) => f.id === id);
        const geometry = toPolygonGeometry(feature?.geometry);
        if (!geometry) return;
        for (const other of draw.getSnapshot()) {
          if (other.id !== id && other.id !== undefined) {
            draw.removeFeatures([other.id]);
          }
        }
        replaceAoi(geometry);
      });
      drawRef.current = draw;
      setMapReady(true);
    });

    return () => {
      drawRef.current?.stop();
      drawRef.current = null;
      map.remove();
      mapRef.current = null;
    };
  }, [replaceAoi]);

  useEffect(() => {
    if (!mapReady) return;
    const source = mapRef.current?.getSource('aoi') as GeoJSONSource | undefined;
    source?.setData(featureCollection(aoi));
  }, [aoi, mapReady]);

  useEffect(() => {
    if (!mapReady) return;
    const source = mapRef.current?.getSource('soil') as GeoJSONSource | undefined;
    const polygons = screening.result?.display?.soil_polygons;
    source?.setData(
      (polygons ?? emptyCollection) as Parameters<GeoJSONSource['setData']>[0],
    );
    if (screening.status === 'done' && aoiRef.current) {
      const bounds = geometryBounds(aoiRef.current);
      if (bounds) mapRef.current?.fitBounds(bounds, { padding: 32, maxZoom: 16 });
    }
  }, [screening.result, screening.status, mapReady]);

  const chooseMode = (next: DrawMode) => {
    drawRef.current?.setMode(next);
    setMode(next);
  };

  const onPasted = (geometry: PolygonGeometry) => {
    syncDraw(geometry);
    replaceAoi(geometry);
    chooseMode('static');
    const bounds = geometryBounds(geometry);
    if (bounds) mapRef.current?.fitBounds(bounds, { padding: 32, maxZoom: 16 });
  };

  const undo = () => {
    const restored = previousAoi;
    setPreviousAoi(null);
    aoiRef.current = restored;
    setAoi(restored);
    syncDraw(restored);
    resetScreening();
  };

  const clear = () => {
    syncDraw(null);
    replaceAoi(null);
    chooseMode('static');
  };

  const toolButton = (label: string, target: DrawMode) => (
    <Button
      type="button"
      size="sm"
      variant={mode === target ? 'default' : 'secondary'}
      aria-pressed={mode === target}
      onClick={() => chooseMode(mode === target ? 'static' : target)}
      disabled={!mapReady}
    >
      {label}
    </Button>
  );

  return (
    <section
      aria-label="Map screening"
      className="flex h-full min-h-0 flex-col gap-3 overflow-y-auto p-3"
    >
      <div className="flex flex-wrap gap-2" role="toolbar" aria-label="Draw AOI">
        {toolButton('Polygon', 'polygon')}
        {toolButton('Rectangle', 'rectangle')}
        {toolButton('Edit', 'select')}
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={undo}
          disabled={!previousAoi && !aoi}
        >
          Undo
        </Button>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={clear}
          disabled={!aoi}
        >
          Clear
        </Button>
      </div>
      <div
        ref={containerRef}
        className="min-h-[18rem] flex-1 overflow-hidden rounded-md border border-border"
      />
      <GeoJsonInput onGeometry={onPasted} />
      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          onClick={() => aoi && screening.run(aoi)}
          disabled={!aoi || screening.status === 'running'}
        >
          {screening.status === 'running' ? 'Screening...' : 'Run screening'}
        </Button>
        {summaryText && (
          <Button
            type="button"
            variant="outline"
            onClick={() => offerSummary(summaryText)}
          >
            Add result to chat
          </Button>
        )}
        <p className="text-muted-foreground text-sm" aria-live="polite">
          {!aoi && 'Draw or paste one AOI.'}
          {aoi && screening.status === 'idle' && 'AOI ready.'}
          {screening.status === 'running' && 'Running preliminary screening.'}
          {screening.status === 'done' &&
            `Preliminary screening done (${screening.result?.display?.soil_polygons?.features.length ?? 0} soil polygons).`}
          {screening.status === 'error' && screening.error}
        </p>
      </div>
    </section>
  );
}
