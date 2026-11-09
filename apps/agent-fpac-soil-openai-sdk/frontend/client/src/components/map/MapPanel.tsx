import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Map as MapLibreMap, Popup } from 'maplibre-gl';
import type { MapMouseEvent } from 'maplibre-gl';
import type { GeoJSONSource, StyleSpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import './maplibreWorker';
import {
  TerraDraw,
  TerraDrawPolygonMode,
  TerraDrawRectangleMode,
  TerraDrawSelectMode,
} from 'terra-draw';
import { TerraDrawMapLibreGLAdapter } from 'terra-draw-maplibre-gl-adapter';
import { Button } from '@/components/ui/button';
import { GeoJsonInput } from './GeoJsonInput';
import {
  MAX_AOI_VERTICES,
  countVertices,
  featureCollection,
  geometryBounds,
  toPolygonGeometry,
} from './geojson';
import { IdentifyPopup } from './IdentifyPopup';
import type { IdentifySection, UseAsAoiResult } from './IdentifyPopup';
import { fetchOutline, identifyArea, identifySoil } from './identify';
import type { AreaInfo } from './identify';
import type { PolygonGeometry } from './geojson';
import { useActiveAoi } from './ActiveAoiContext';
import { MapLegend } from './Legend';
import { clearMapBlock, inlineLayers, renderMapBlock } from './mapLayers';
import { useMapResult } from './MapResultContext';
import { NO_OVERLAYS, OverlayControl } from './OverlayControl';
import type { OverlayFlags } from './OverlayControl';
import { OVERLAYS, addOverlay, overlayIdForSource, removeOverlay } from './overlays';
import type { OverlayId } from './overlays';
import { ScreeningResults } from './ScreeningResults';
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

type DrawMode = 'polygon' | 'rectangle' | 'select' | 'static';

const emptyCollection = { type: 'FeatureCollection' as const, features: [] };

export function MapPanel() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const drawRef = useRef<TerraDraw | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [mode, setMode] = useState<DrawMode>('static');
  const [previousAoi, setPreviousAoi] = useState<PolygonGeometry | null>(null);
  const [aoiError, setAoiError] = useState<string | null>(null);
  const [tileError, setTileError] = useState(false);
  // Context overlays (D5): panel state only, off by default, never stored.
  const [overlayOn, setOverlayOn] = useState<OverlayFlags>(NO_OVERLAYS);
  const [overlayError, setOverlayError] = useState<OverlayFlags>(NO_OVERLAYS);
  const [overlayLoading, setOverlayLoading] = useState<OverlayFlags>(NO_OVERLAYS);
  const [zoom, setZoom] = useState(3);
  const [layersOpen, setLayersOpen] = useState(false);
  // Short hint when a click has nothing to identify (no layer on, or none in range).
  const [identifyHint, setIdentifyHint] = useState<string | null>(null);
  // Identify popup (D6): MapLibre popup whose content is rendered through a portal.
  const popupRef = useRef<Popup | null>(null);
  const identifyAbort = useRef<AbortController | null>(null);
  const [popupNode, setPopupNode] = useState<HTMLDivElement | null>(null);
  const [sections, setSections] = useState<IdentifySection[]>([]);
  // The AOI is chat session context (ADR 0016): the active-AOI context owns it, keyed
  // by chat id. `aoiRef` is the geometry this panel last drew or loaded.
  const { chatId, activeAoi, setGeometry, setSummary } = useActiveAoi();
  // The result drawn on the map: this panel's screening or a tool card's "Show on map".
  const { shown, show, clear: clearShown } = useMapResult();
  const aoi = activeAoi?.geometry ?? null;
  const aoiRef = useRef<PolygonGeometry | null>(null);
  const screenedRef = useRef<string | null>(null);
  const screening = useScreening();
  const { reset: resetScreening } = screening;

  // One AOI at a time: a new AOI replaces the old and becomes undoable.
  const replaceAoi = useCallback(
    (next: PolygonGeometry | null) => {
      setPreviousAoi(aoiRef.current);
      aoiRef.current = next;
      setGeometry(next);
      setAoiError(null);
      resetScreening();
    },
    [resetScreening, setGeometry],
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

    // Basemap tile failures are shown in the panel, never as a silent blank map.
    // Overlay failures are reported per overlay and never as a basemap error.
    map.on('error', (event) => {
      const sourceId = (event as { sourceId?: string }).sourceId;
      if (sourceId === 'usgsTopo') {
        setTileError(true);
        return;
      }
      const overlayId = overlayIdForSource(sourceId);
      if (overlayId) setOverlayError((prev) => ({ ...prev, [overlayId]: true }));
    });
    map.on('sourcedataloading', (event) => {
      const overlayId = overlayIdForSource(event.sourceId);
      if (overlayId) setOverlayLoading((prev) => ({ ...prev, [overlayId]: true }));
    });
    map.on('idle', () => setOverlayLoading(NO_OVERLAYS));
    map.on('zoomend', () => setZoom(map.getZoom()));

    map.on('load', () => {
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
        if (!geometry) {
          setAoiError('The drawn shape is not a valid polygon. Draw it again.');
          return;
        }
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

  // Switching chats loads that chat's AOI (or none): redraw it and drop old results.
  useEffect(() => {
    if (!mapReady || aoi === aoiRef.current) return;
    aoiRef.current = aoi;
    setPreviousAoi(null);
    setAoiError(null);
    syncDraw(aoi);
    resetScreening();
    const bounds = aoi ? geometryBounds(aoi) : null;
    if (bounds) mapRef.current?.fitBounds(bounds, { padding: 32, maxZoom: 16 });
  }, [aoi, mapReady, syncDraw, resetScreening]);

  useEffect(() => {
    if (!mapReady) return;
    const source = mapRef.current?.getSource('aoi') as GeoJSONSource | undefined;
    source?.setData(featureCollection(aoi));
  }, [aoi, mapReady]);

  // The latest valid screening becomes the AOI's chat summary. A result without its
  // regulatory notice is invalid (ADR 0003) and is not attached.
  useEffect(() => {
    const result = screening.result;
    if (
      screening.status === 'done' &&
      result &&
      !result.display?.error &&
      result.display?.regulatory_notice &&
      screenedRef.current
    ) {
      setSummary(screenedRef.current, result.chat_summary);
    }
  }, [screening.status, screening.result, setSummary]);

  const runScreening = () => {
    if (!aoi || !activeAoi) return;
    screenedRef.current = activeAoi.aoi_ref;
    screening.run(aoi, activeAoi.aoi_ref);
  };

  // A finished screening becomes the shown result; a new or reset screening drops it.
  const screeningMap =
    screening.status === 'done' ? (screening.result?.display?.map ?? null) : null;
  const screeningNotice = screening.result?.display?.regulatory_notice ?? null;
  const showScreening = useCallback(() => {
    if (screeningMap) {
      show({ origin: 'screening', block: screeningMap, regulatory_notice: screeningNotice });
    }
  }, [screeningMap, screeningNotice, show]);
  useEffect(() => {
    showScreening();
  }, [showScreening]);
  useEffect(() => {
    if (screening.status !== 'done' && shown?.origin === 'screening') clearShown();
  }, [screening.status, shown, clearShown]);

  // A tool result belongs to the chat and AOI it was shown for.
  // biome-ignore lint/correctness/useExhaustiveDependencies: clears on chat or AOI change
  useEffect(() => {
    clearShown();
  }, [aoi, chatId, clearShown]);

  useEffect(() => {
    if (!mapReady) return;
    const map = mapRef.current;
    if (!map) return;
    if (!shown) {
      clearMapBlock(map);
      return;
    }
    // Server layers draw below the panel's own AOI outline (`aoi-line`).
    renderMapBlock(map, shown.block, 'aoi-line');
    // Screening zooms to the AOI (urban areas are not clipped); a tool result zooms to
    // its layers (a corridor has no AOI).
    const bounds =
      shown.origin === 'screening' && aoiRef.current
        ? geometryBounds(aoiRef.current)
        : (shown.block.bounds ?? null);
    if (bounds) map.fitBounds(bounds, { padding: 32, maxZoom: 16 });
  }, [shown, mapReady]);

  // Add or remove overlays to match the toggles; a removed overlay forgets its error.
  useEffect(() => {
    if (!mapReady) return;
    const map = mapRef.current;
    if (!map) return;
    for (const overlay of OVERLAYS) {
      if (overlayOn[overlay.id]) addOverlay(map, overlay);
      else removeOverlay(map, overlay);
    }
  }, [overlayOn, mapReady]);

  const toggleOverlay = useCallback((id: OverlayId, next: boolean) => {
    setOverlayOn((prev) => ({ ...prev, [id]: next }));
    setOverlayError((prev) => ({ ...prev, [id]: false }));
  }, []);

  // A click identifies the overlays that are on and in range, only when no drawing
  // tool is active (Terra Draw owns clicks in the other modes).
  useEffect(() => {
    if (!mapReady) return;
    const map = mapRef.current;
    if (!map) return;
    const onClick = (event: MapMouseEvent) => {
      if (mode !== 'static') return;
      const on = OVERLAYS.filter((overlay) => overlayOn[overlay.id]);
      const active = on.filter((overlay) => map.getZoom() >= overlay.minzoom);
      if (active.length === 0) {
        setIdentifyHint(
          on.length === 0
            ? 'Turn on a context layer to identify what is here.'
            : 'Zoom in to identify the layers that are on.',
        );
        return;
      }
      setIdentifyHint(null);
      identifyAbort.current?.abort();
      const controller = new AbortController();
      identifyAbort.current = controller;
      popupRef.current?.remove();
      const node = document.createElement('div');
      const popup = new Popup({ closeButton: true, maxWidth: 'none' })
        .setLngLat(event.lngLat)
        .setDOMContent(node)
        .addTo(map);
      // Clear MapLibre's fixed white box and tip so the themed content shows in dark
      // mode; the close button takes the content colour.
      const element = popup.getElement();
      const content = element.querySelector<HTMLElement>('.maplibregl-popup-content');
      if (content) Object.assign(content.style, { background: 'transparent', padding: '0', boxShadow: 'none' });
      const tip = element.querySelector<HTMLElement>('.maplibregl-popup-tip');
      if (tip) tip.style.display = 'none';
      const close = element.querySelector<HTMLElement>('.maplibregl-popup-close-button');
      if (close) Object.assign(close.style, { color: 'inherit', right: '2px', top: '2px' });
      node.className = 'text-popover-foreground';
      popup.on('close', () => {
        if (popupRef.current !== popup) return;
        popupRef.current = null;
        controller.abort();
        setPopupNode(null);
      });
      popupRef.current = popup;
      setPopupNode(node);
      setSections(active.map((overlay) => ({ overlay, state: 'loading' as const })));
      const { lng, lat } = event.lngLat;
      for (const overlay of active) {
        const query =
          overlay.id === 'ssurgo'
            ? identifySoil(lng, lat, controller.signal).then((soil) => ({ soil }))
            : identifyArea(overlay.id, lng, lat, controller.signal).then((area) => ({ area }));
        query
          .then((found) => {
            if (controller.signal.aborted) return;
            setSections((prev) =>
              prev.map((s) =>
                s.overlay.id === overlay.id ? { overlay, state: 'done' as const, ...found } : s,
              ),
            );
          })
          .catch(() => {
            if (controller.signal.aborted) return;
            setSections((prev) =>
              prev.map((s) =>
                s.overlay.id === overlay.id ? { overlay, state: 'error' as const } : s,
              ),
            );
          });
      }
    };
    map.on('click', onClick);
    return () => {
      map.off('click', onClick);
    };
  }, [mapReady, mode, overlayOn]);

  // The hint clears itself after a few seconds.
  useEffect(() => {
    if (!identifyHint) return;
    const timer = window.setTimeout(() => setIdentifyHint(null), 5000);
    return () => window.clearTimeout(timer);
  }, [identifyHint]);

  const openLayers = () => {
    setLayersOpen(true);
    setIdentifyHint(null);
  };

  // MapLibre picks the popup anchor from the content size when it is added, but the
  // portal fills the content afterwards. Re-anchor once the sections render (and
  // when they change size) so the popup flips to stay inside the map.
  // biome-ignore lint/correctness/useExhaustiveDependencies: re-run when sections render
  useEffect(() => {
    const popup = popupRef.current;
    if (popup && popupNode) popup.setLngLat(popup.getLngLat());
  }, [sections, popupNode]);

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

  // Use as AOI: the exact outline, refused above the vertex cap (D6, never simplified).
  const applyAreaAsAoi = async (section: IdentifySection, area: AreaInfo): Promise<UseAsAoiResult> => {
    const overlayId = section.overlay.id;
    if (overlayId === 'ssurgo') return { ok: false, message: 'Soil map units cannot be an AOI.' };
    const controller = new AbortController();
    let geometry: PolygonGeometry | null = null;
    try {
      geometry = await fetchOutline(overlayId, area.geoid, controller.signal);
    } catch {
      return { ok: false, message: 'Could not load this outline. Try again later.' };
    }
    if (!geometry) return { ok: false, message: 'Could not load this outline. Try again later.' };
    const vertices = countVertices(geometry);
    if (vertices > MAX_AOI_VERTICES) {
      return {
        ok: false,
        message: `This outline has ${vertices} vertices; the AOI limit is ${MAX_AOI_VERTICES}. Draw or paste a smaller AOI.`,
      };
    }
    popupRef.current?.remove();
    onPasted(geometry);
    return { ok: true };
  };

  const undo = () => {
    const restored = previousAoi;
    setPreviousAoi(null);
    aoiRef.current = restored;
    setGeometry(restored);
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
      {/* The map and its controls fill the panel's visible height; results start
          below and are reached with the panel's scrollbar, so screening never
          shrinks the map. */}
      <div className="flex min-h-full shrink-0 flex-col gap-3">
        <p className="rounded-md border border-amber-500/60 bg-amber-500/10 px-2 py-1 font-medium text-xs">
          Preliminary screening view. Not an official NRCS determination.
        </p>
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
        <div className="relative min-h-[18rem] flex-1 overflow-hidden rounded-md border border-border">
          {/* Inline position: maplibre-gl.css sets `.maplibregl-map { position: relative }`. */}
          <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />
          <OverlayControl
            on={overlayOn}
            errors={overlayError}
            loading={overlayLoading}
            zoom={zoom}
            open={layersOpen}
            onOpenChange={setLayersOpen}
            onToggle={toggleOverlay}
          />
          <div aria-live="polite" className="absolute bottom-2 left-2 z-10 max-w-[18rem]">
            {identifyHint && (
              <p className="flex items-center gap-2 rounded-md border border-border bg-popover px-2 py-1 text-popover-foreground text-xs shadow-md">
                {identifyHint}
                {!layersOpen && (
                  <button type="button" className="font-medium underline" onClick={openLayers}>
                    Layers
                  </button>
                )}
              </p>
            )}
          </div>
        </div>
        {popupNode &&
          createPortal(<IdentifyPopup sections={sections} onUseAsAoi={applyAreaAsAoi} />, popupNode)}
        <GeoJsonInput onGeometry={onPasted} />
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            onClick={runScreening}
            disabled={!aoi || screening.status === 'running'}
          >
            {screening.status === 'running' ? 'Screening...' : 'Run screening'}
          </Button>
          <p className="text-muted-foreground text-sm" aria-live="polite">
            {!aoi && 'Draw or paste one AOI for this chat.'}
            {aoi && activeAoi && screening.status === 'idle' &&
              `AOI ${activeAoi.aoi_ref} is attached to this chat.`}
            {screening.status === 'running' && 'Running preliminary screening.'}
            {screening.status === 'done' &&
              `Preliminary screening done (${inlineLayers(screening.result?.display?.map).length} map layers drawn).`}
          </p>
        </div>
        {(aoiError || tileError || screening.status === 'error') && (
          <div role="alert" className="flex flex-col gap-1 text-destructive text-sm">
            {aoiError && <p>{aoiError}</p>}
            {screening.status === 'error' && screening.error && <p>{screening.error}</p>}
            {tileError && (
              <p>
                Basemap tiles failed to load. Drawing, screening and the results table
                still work.
              </p>
            )}
          </div>
        )}
      </div>
      {shown?.origin === 'tool' ? (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-medium text-sm">Map of {shown.tool} result</h3>
            {screeningMap && (
              <Button type="button" size="sm" variant="secondary" onClick={showScreening}>
                Back to screening
              </Button>
            )}
          </div>
          {shown.regulatory_notice ? (
            <div className="rounded-md border border-border bg-muted p-2 text-sm">
              <h3 className="font-medium">Regulatory notice</h3>
              <p className="whitespace-pre-line">{shown.regulatory_notice}</p>
            </div>
          ) : (
            <p role="alert" className="text-destructive text-sm">
              Regulatory notice missing - treat this result as invalid.
            </p>
          )}
          <MapLegend block={shown.block} />
        </div>
      ) : (
        screening.status === 'done' &&
        screening.result && <ScreeningResults result={screening.result} />
      )}
    </section>
  );
}
