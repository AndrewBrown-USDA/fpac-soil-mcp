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
import { Check, Map as MapIcon, MousePointer2, Pentagon, Square, Trash2, Undo2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import ncssAcronymColor from '@/assets/ncss-acronym-color.png';
import ncssAcronymWhite from '@/assets/ncss-acronym-white.png';
import { GeoJsonInput } from './GeoJsonInput';
import {
  MAX_AOI_VERTICES,
  countVertices,
  featureCollection,
  geometryBounds,
  toPolygonGeometry,
} from './geojson';
import { IdentifyPopup, resultInfo } from './IdentifyPopup';
import type { IdentifySection, ResultInfo, UseAsAoiResult } from './IdentifyPopup';
import { fetchOutline, identifyArea, identifySoil } from './identify';
import type { AreaInfo } from './identify';
import type { PolygonGeometry } from './geojson';
import { useActiveAoi } from './ActiveAoiContext';
import { MapLegend } from './Legend';
import { IDENTIFY_HIT_LAYER, clearMapBlock, inlineLayers, renderMapBlock } from './mapLayers';
import { useMapResult } from './MapResultContext';
import { CDLContextSummary } from './CDLContextSummary';
import { NO_OVERLAYS, OverlayControl } from './OverlayControl';
import type { OverlayFlags } from './OverlayControl';
import { OVERLAYS, addOverlay, overlayIdForSource, removeOverlay } from './overlays';
import type { OverlayId } from './overlays';
import { NOTICE_CARD, RESULT_CARD, ScreeningResults } from './ScreeningResults';
import { StatusMessage } from './StatusMessage';
import type { StatusVariant } from './StatusMessage';
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

// Terra Draw treats right clicks as clicks by default; only the left button draws.
const LEFT_BUTTON_ONLY = {
  leftClick: true,
  rightClick: false,
  contextMenu: false,
  onDragStart: true,
  onDrag: true,
  onDragEnd: true,
};

const emptyCollection = { type: 'FeatureCollection' as const, features: [] };

type MapPanelProps = {
  onCloseMap: () => void;
};

export function MapPanel({ onCloseMap }: MapPanelProps) {
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
  const [resultHit, setResultHit] = useState<ResultInfo | null>(null);
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
          new TerraDrawPolygonMode({ pointerEvents: LEFT_BUTTON_ONLY }),
          new TerraDrawRectangleMode({ pointerEvents: LEFT_BUTTON_ONLY }),
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
        // One AOI at a time: a finished polygon or rectangle ends drawing, so the next
        // click does not start another shape. Edit (select) mode stays on. Deferred
        // so Terra Draw finishes its own event first.
        const finished = draw.getMode();
        if (finished === 'polygon' || finished === 'rectangle') {
          window.setTimeout(() => {
            draw.setMode('static');
            setMode('static');
          }, 0);
        }
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
    clearMapBlock(map);
    if (shown.cdlSummary) {
      const bounds = aoiRef.current ? geometryBounds(aoiRef.current) : null;
      if (bounds) map.fitBounds(bounds, { padding: 32, maxZoom: 16 });
      return;
    }
    if (!shown.block) return;
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

  // A click identifies the drawn result polygon under it (A7) and the overlays that are
  // on and in range, only when no drawing tool is active (Terra Draw owns clicks in
  // the other modes).
  useEffect(() => {
    if (!mapReady) return;
    const map = mapRef.current;
    if (!map) return;
    const onClick = (event: MapMouseEvent) => {
      if (mode !== 'static') return;
      const on = OVERLAYS.filter((overlay) => overlayOn[overlay.id]);
      const active = on.filter((overlay) => map.getZoom() >= overlay.minzoom);
      const hit = map.getLayer(IDENTIFY_HIT_LAYER)
        ? map.queryRenderedFeatures(event.point, { layers: [IDENTIFY_HIT_LAYER] })[0]
        : undefined;
      const result = resultInfo(hit?.properties);
      if (active.length === 0 && !result) {
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
      setResultHit(result);
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

  // The pressed tool is filled and swaps its icon for a check, so the state is not
  // carried by colour alone.
  const toolButton = (label: string, target: DrawMode, Icon: LucideIcon) => {
    const pressed = mode === target;
    const StateIcon = pressed ? Check : Icon;
    return (
      <Button
        type="button"
        size="sm"
        variant={pressed ? 'primary' : 'default'}
        aria-pressed={pressed}
        onClick={() => chooseMode(pressed ? 'static' : target)}
        disabled={!mapReady}
        className="gap-1.5 px-2"
      >
        <StateIcon aria-hidden="true" />
        {label}
      </Button>
    );
  };

  const groupLabel = 'font-medium text-muted-foreground text-xs uppercase tracking-wide';
  const originBadge = 'rounded-full border border-border bg-muted px-2 py-0.5 font-medium text-xs';

  // Same status text as before, now with a variant for the message bar.
  let statusText: string | null = null;
  let statusVariant: StatusVariant = 'info';
  if (!aoi) statusText = 'Draw or paste one AOI for this chat.';
  else if (activeAoi && screening.status === 'idle')
    statusText = `AOI ${activeAoi.aoi_ref} is attached to this chat.`;
  if (screening.status === 'running') statusText = 'Running preliminary screening.';
  if (screening.status === 'done') {
    statusText = `Preliminary screening done (${inlineLayers(screening.result?.display?.map).length} map layers drawn).`;
    statusVariant = 'success';
  }

  return (
    <section
      aria-label="Map screening"
      className="flex h-full min-h-0 flex-col gap-3 overflow-y-auto p-3"
    >
      {/* The map and its controls fill the panel's visible height; results start
          below and are reached with the panel's scrollbar, so screening never
          shrinks the map. */}
      <div className="flex min-h-full shrink-0 flex-col gap-3">
        <header className="flex items-center justify-between gap-2 border-atlas-soil/50 border-b-2 pb-2">
          <div className="flex items-center gap-2">
            <img
              src={ncssAcronymColor}
              alt="National Cooperative Soil Survey"
              className="h-auto w-12 shrink-0 dark:hidden"
            />
            <img
              src={ncssAcronymWhite}
              alt="National Cooperative Soil Survey"
              className="hidden h-auto w-12 shrink-0 dark:block"
            />
            <h2 className="font-semibold text-sm leading-5 tracking-tight">
              Farmland Protection Policy Act Agent
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`break-all rounded-full border px-2 py-0.5 font-mono text-xs ${
                activeAoi
                  ? 'border-primary/40 bg-primary/10 text-foreground'
                  : 'border-border bg-muted text-muted-foreground'
              }`}
            >
              {activeAoi ? `AOI ${activeAoi.aoi_ref}` : 'No AOI'}
            </span>
            <button
              type="button"
              onClick={onCloseMap}
              aria-expanded
              aria-controls="map-panel"
              className="flex shrink-0 items-center gap-1.5 rounded-md border border-border bg-background px-1.5 py-1 font-medium text-xs shadow-sm hover:bg-[var(--action-default-background-hover)] focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2"
            >
              <MapIcon aria-hidden="true" className="size-4 text-primary" />
              Hide map
            </button>
          </div>
        </header>
        <StatusMessage variant="warning" className="font-medium text-xs">
          <p>Preliminary screening view. Not an official NRCS determination.</p>
        </StatusMessage>
        <div className="flex flex-wrap items-end gap-3" role="toolbar" aria-label="AOI tools">
          <div role="group" aria-label="Draw area" className="flex flex-col gap-1">
            <span aria-hidden="true" className={groupLabel}>
              Draw area
            </span>
            <div className="flex flex-wrap gap-1.5">
              {toolButton('Polygon', 'polygon', Pentagon)}
              {toolButton('Rectangle', 'rectangle', Square)}
            </div>
          </div>
          <div aria-hidden="true" className="hidden h-6 w-px self-end bg-border sm:block" />
          <div role="group" aria-label="Edit area" className="flex flex-col gap-1">
            <span aria-hidden="true" className={groupLabel}>
              Edit area
            </span>
            <div className="flex flex-wrap gap-1.5">
              {toolButton('Edit', 'select', MousePointer2)}
              <Button
                type="button"
                size="sm"
                variant="default"
                onClick={undo}
                disabled={!previousAoi && !aoi}
                className="gap-1.5 px-2"
              >
                <Undo2 aria-hidden="true" />
                Undo
              </Button>
              <Button
                type="button"
                size="sm"
                variant="default"
                onClick={clear}
                disabled={!aoi}
                className="gap-1.5 px-2"
              >
                <Trash2 aria-hidden="true" />
                Clear
              </Button>
            </div>
          </div>
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
          createPortal(
            <IdentifyPopup result={resultHit} sections={sections} onUseAsAoi={applyAreaAsAoi} />,
            popupNode,
          )}
        <GeoJsonInput onGeometry={onPasted} />
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant="primary"
            onClick={runScreening}
            disabled={!aoi || screening.status === 'running'}
          >
            {screening.status === 'running' ? 'Screening...' : 'Run screening'}
          </Button>
          <div aria-live="polite" className="min-w-[12rem] flex-1">
            {statusText && (
              <StatusMessage variant={statusVariant}>
                <p>{statusText}</p>
              </StatusMessage>
            )}
          </div>
        </div>
        {(aoiError || tileError || screening.status === 'error') && (
          <StatusMessage variant="error">
            {aoiError && <p>{aoiError}</p>}
            {screening.status === 'error' && screening.error && <p>{screening.error}</p>}
            {tileError && (
              <p>
                Basemap tiles failed to load. Drawing, screening and the results table
                still work.
              </p>
            )}
          </StatusMessage>
        )}
      </div>
      {shown?.origin === 'tool' ? (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className={originBadge}>Tool result</span>
            <h3 className="font-medium text-sm">
              {shown.cdlSummary ? 'CDL context summary' : `Map of ${shown.tool} result`}
            </h3>
            {screeningMap && (
              <Button type="button" size="sm" variant="secondary" onClick={showScreening}>
                Back to screening
              </Button>
            )}
          </div>
          {shown.cdlSummary ? (
            <CDLContextSummary result={shown.cdlSummary} />
          ) : shown.regulatory_notice ? (
            <div className={NOTICE_CARD}>
              <h3 className="font-semibold text-sm">Regulatory notice</h3>
              <p className="mt-1 whitespace-pre-line">{shown.regulatory_notice}</p>
            </div>
          ) : (
            <p role="alert" className="text-destructive text-sm">
              Regulatory notice missing - treat this result as invalid.
            </p>
          )}
          {shown.block && (
            <div className={RESULT_CARD}>
              <MapLegend block={shown.block} />
            </div>
          )}
        </div>
      ) : (
        screening.status === 'done' &&
        screening.result && (
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className={originBadge}>AOI screening</span>
            </div>
            <ScreeningResults result={screening.result} />
          </div>
        )
      )}
    </section>
  );
}
