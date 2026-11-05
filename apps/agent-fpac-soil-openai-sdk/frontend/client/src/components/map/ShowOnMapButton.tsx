import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useOptionalActiveAoi } from './ActiveAoiContext';
import { inlineLayers } from './mapLayers';
import type { MapBlock } from './mapLayers';
import { useOptionalMapResult } from './MapResultContext';

// The tools whose results carry an ADR 0017 map block (`geo.MAP_TOOLS`).
export const MAP_TOOLS: ReadonlySet<string> = new Set([
  'analyze_farmland_by_polygon',
  'analyze_corridor_fppa',
]);

const AOI_REF = /^aoi-[0-9a-f]{8}$/;

type MapResponse = {
  map?: MapBlock | null;
  regulatory_notice?: string | null;
};

// AOI references among the top-level arguments (the agent passes the reference, not
// the shape; /api/geo/map substitutes only the active AOI).
function aoiRefs(input: unknown): string[] {
  if (!input || typeof input !== 'object') return [];
  return Object.values(input as Record<string, unknown>).filter(
    (value): value is string => typeof value === 'string' && AOI_REF.test(value.trim()),
  );
}

// Fixed messages per status; nothing from the arguments or response is shown or logged.
function failureMessage(status: number): string {
  if (status === 400) return 'This tool call cannot be shown on the map.';
  if (status === 413) return 'This tool call is too large to show on the map.';
  if (status === 502) return 'The map service is unavailable. Try again later.';
  return 'Map layers are unavailable right now. Try again later.';
}

export function ShowOnMapButton({
  tool,
  toolCallId,
  input,
}: {
  tool: string;
  toolCallId: string;
  input: unknown;
}) {
  const aoiContext = useOptionalActiveAoi();
  const mapResult = useOptionalMapResult();
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle');
  const [message, setMessage] = useState<string | null>(null);
  if (!aoiContext || !mapResult) return null;

  const activeAoi = aoiContext.activeAoi;
  const refs = aoiRefs(input);
  const isObject = !!input && typeof input === 'object' && !Array.isArray(input);
  const unavailable = !isObject
    ? 'Not available: this call has no arguments to map.'
    : refs.some((ref) => ref.trim() !== activeAoi?.aoi_ref)
      ? 'Not available: the AOI this call used is no longer attached to the chat.'
      : null;
  const isShown =
    mapResult.shown?.origin === 'tool' && mapResult.shown.toolCallId === toolCallId;

  const run = async () => {
    setStatus('loading');
    setMessage(null);
    try {
      const response = await fetch('/api/geo/map', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool,
          arguments: input,
          ...(refs.length > 0 && activeAoi
            ? { active_aoi: { aoi_ref: activeAoi.aoi_ref, geometry: activeAoi.geometry } }
            : {}),
        }),
      });
      if (!response.ok) {
        setStatus('error');
        setMessage(failureMessage(response.status));
        return;
      }
      const body = (await response.json()) as MapResponse;
      if (!body.map || inlineLayers(body.map).length === 0) {
        setStatus('error');
        setMessage('No map layers came back for this result.');
        return;
      }
      mapResult.show({
        origin: 'tool',
        tool,
        toolCallId,
        block: body.map,
        regulatory_notice: body.regulatory_notice ?? null,
      });
      setStatus('idle');
    } catch {
      setStatus('error');
      setMessage('Map request failed. Check your connection.');
    }
  };

  if (unavailable) {
    return <p className="mt-2 text-muted-foreground text-xs">{unavailable}</p>;
  }
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2">
      <Button
        type="button"
        size="sm"
        variant="secondary"
        onClick={run}
        disabled={status === 'loading'}
      >
        {status === 'loading' ? 'Loading map...' : isShown ? 'Show on map again' : 'Show on map'}
      </Button>
      {isShown && status !== 'loading' && (
        <span className="text-muted-foreground text-xs">Shown on the map.</span>
      )}
      {status === 'error' && message && (
        <span role="alert" className="text-destructive text-xs">
          {message}
        </span>
      )}
    </div>
  );
}
