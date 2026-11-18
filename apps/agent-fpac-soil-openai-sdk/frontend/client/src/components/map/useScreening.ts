import { useCallback, useRef, useState } from 'react';
import type { PolygonGeometry } from './geojson';
import type { MapBlock } from './mapLayers';

export type SoilFeatureCollection = {
  type: 'FeatureCollection';
  features: Array<{
    type: 'Feature';
    geometry: unknown;
    properties?: Record<string, unknown> | null;
  }>;
};

export type DisplayMapUnit = {
  mukey?: string | null;
  musym?: string | null;
  muname?: string | null;
  farmlndcl?: string | null;
  acres?: number | null;
  pct?: number | null;
};

// Shape of `display.analysis` from `geo.select_display_analysis` (browser-only).
export type DisplayAnalysis = {
  total_aoi_acres?: number | null;
  coverage_status?: string | null;
  farmland_summary?: Record<string, unknown>;
  urban_intersected?: boolean | null;
  map_units?: DisplayMapUnit[];
  source?: { service_name?: string | null; timestamp_utc?: string | null };
};

export type ScreeningResponse = {
  aoi_ref: string;
  display: {
    analysis?: DisplayAnalysis;
    // ADR 0017 map block from the server, drawn by mapLayers.renderMapBlock.
    map?: MapBlock | null;
    regulatory_notice?: string | null;
    error?: string;
  };
  chat_summary: Record<string, unknown>;
  chat_summary_text: string;
};

export type ScreeningStatus = 'idle' | 'running' | 'done' | 'error';

// The chat summary to attach for a finished screening (ADR 0016): a valid result
// with its MCP notice, or the server's screening_failed summary so the agent is
// told the screening failed. A result without its notice is invalid (ADR 0003)
// and is never attached.
export function summaryToAttach(
  status: ScreeningStatus,
  result: ScreeningResponse | null,
): Record<string, unknown> | null {
  if (!result) return null;
  if (status === 'done' && !result.display?.error && result.display?.regulatory_notice) {
    return result.chat_summary;
  }
  if (status === 'error' && result.display?.error === 'screening_failed') {
    return result.chat_summary;
  }
  return null;
}

// Calls the out-of-band screening route. The response stays in React state only
// (no localStorage or sessionStorage) and is never logged.
export function useScreening() {
  const [status, setStatus] = useState<ScreeningStatus>('idle');
  const [result, setResult] = useState<ScreeningResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  // aoiRef is the chat's active AOI reference; the route reuses it in its summary.
  const run = useCallback(async (geometry: PolygonGeometry, aoiRef?: string) => {
    const id = ++requestId.current;
    setStatus('running');
    setError(null);
    try {
      const response = await fetch('/api/geo/screen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(aoiRef ? { geometry, aoi_ref: aoiRef } : { geometry }),
      });
      if (id !== requestId.current) return;
      if (!response.ok) {
        // The server's 422 messages are fixed, bounded strings that never echo input.
        let detail: string | null = null;
        if (response.status === 422) {
          try {
            const body = (await response.json()) as { detail?: unknown };
            if (typeof body.detail === 'string' && body.detail.length <= 200) {
              detail = body.detail;
            }
          } catch {
            detail = null;
          }
        }
        if (id !== requestId.current) return;
        setResult(null);
        setStatus('error');
        setError(
          response.status === 422
            ? `The AOI was rejected: ${detail ?? 'check the type and size.'}`
            : response.status === 502
              ? 'Screening unavailable: the soil service could not be reached. Try again later.'
              : 'Screening is unavailable right now. Try again later.',
        );
        return;
      }
      const body = (await response.json()) as ScreeningResponse;
      if (id !== requestId.current) return;
      setResult(body);
      if (body.display?.error) {
        setStatus('error');
        setError('The screening service reported an error for this AOI.');
      } else {
        setStatus('done');
      }
    } catch {
      if (id !== requestId.current) return;
      setResult(null);
      setStatus('error');
      setError('Screening request failed. Check your connection.');
    }
  }, []);

  const reset = useCallback(() => {
    requestId.current += 1;
    setStatus('idle');
    setResult(null);
    setError(null);
  }, []);

  return { status, result, error, run, reset };
}
