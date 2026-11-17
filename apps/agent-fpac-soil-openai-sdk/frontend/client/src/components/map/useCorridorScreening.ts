import { useCallback, useRef, useState } from 'react';
import type { ActiveCorridor } from './corridorSession';
import type { MapBlock } from './mapLayers';

export type CorridorDisplay = {
  corridor_ref: string;
  status: 'preliminary_screening';
  buffer_distance: number | null;
  buffer_units: string | null;
  impact_breakdown: Record<string, number | null>;
  composite_relative_rating: number | null;
  county_segments: Array<Record<string, string | number | null>>;
  alternatives: Array<Record<string, string | number | null>>;
};

export type CorridorScreeningResponse = {
  display: CorridorDisplay;
  map: MapBlock | null;
  regulatory_notice: string | null;
  status: 'preliminary_screening';
};

export async function requestCorridorScreening(
  corridor: ActiveCorridor,
): Promise<{ result: CorridorScreeningResponse | null; error: string | null }> {
  try {
    const response = await fetch('/api/geo/corridor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corridor),
    });
    if (!response.ok) {
      return {
        result: null,
        error: response.status === 502
          ? 'Corridor screening unavailable. Try again later.'
          : 'Corridor screening request was rejected. Check the corridor and try again.',
      };
    }
    const result = (await response.json()) as CorridorScreeningResponse;
    // A null notice is kept, not rejected: the results view then shows it as
    // invalid (ADR 0003, ADR 0016 amendment 2026-11-17).
    if (!result.display || result.status !== 'preliminary_screening') {
      return { result: null, error: 'Corridor screening returned an incomplete result.' };
    }
    return { result, error: null };
  } catch {
    return { result: null, error: 'Corridor screening request failed. Check your connection.' };
  }
}

export function useCorridorScreening() {
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const [result, setResult] = useState<CorridorScreeningResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const run = useCallback(async (corridor: ActiveCorridor) => {
    const id = ++requestId.current;
    setStatus('running');
    setError(null);
    const response = await requestCorridorScreening(corridor);
    if (id !== requestId.current) return;
    setResult(response.result);
    setError(response.error);
    setStatus(response.error ? 'error' : 'done');
  }, []);

  const reset = useCallback(() => {
    requestId.current += 1;
    setStatus('idle');
    setResult(null);
    setError(null);
  }, []);

  return { status, result, error, run, reset };
}
