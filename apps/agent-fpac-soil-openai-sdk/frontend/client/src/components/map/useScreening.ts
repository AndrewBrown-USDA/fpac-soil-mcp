import { useCallback, useRef, useState } from 'react';
import type { PolygonGeometry } from './geojson';

export type SoilFeatureCollection = {
  type: 'FeatureCollection';
  features: Array<{
    type: 'Feature';
    geometry: unknown;
    properties?: Record<string, unknown> | null;
  }>;
};

export type ScreeningResponse = {
  aoi_ref: string;
  display: {
    analysis?: Record<string, unknown>;
    soil_polygons?: SoilFeatureCollection;
    regulatory_notice?: string | null;
    error?: string;
  };
  chat_summary: Record<string, unknown>;
  chat_summary_text: string;
};

export type ScreeningStatus = 'idle' | 'running' | 'done' | 'error';

// Calls the out-of-band screening route. The response stays in React state only
// (no localStorage or sessionStorage) and is never logged.
export function useScreening() {
  const [status, setStatus] = useState<ScreeningStatus>('idle');
  const [result, setResult] = useState<ScreeningResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const run = useCallback(async (geometry: PolygonGeometry) => {
    const id = ++requestId.current;
    setStatus('running');
    setError(null);
    try {
      const response = await fetch('/api/geo/screen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ geometry }),
      });
      if (id !== requestId.current) return;
      if (!response.ok) {
        setResult(null);
        setStatus('error');
        setError(
          response.status === 422
            ? 'The AOI was rejected (check the type and size).'
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
