import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

// Holds the geometry-free screening summary the user may add to the chat input.
// React state only; nothing is persisted.
type MapSummaryContextValue = {
  pendingSummary: string | null;
  offerSummary: (text: string) => void;
  consumeSummary: () => string | null;
};

const MapSummaryContext = createContext<MapSummaryContextValue | null>(null);

export function MapSummaryProvider({ children }: { children: ReactNode }) {
  const [pendingSummary, setPendingSummary] = useState<string | null>(null);

  const offerSummary = useCallback((text: string) => {
    setPendingSummary(text);
  }, []);

  const consumeSummary = useCallback(() => {
    const text = pendingSummary;
    setPendingSummary(null);
    return text;
  }, [pendingSummary]);

  const value = useMemo(
    () => ({ pendingSummary, offerSummary, consumeSummary }),
    [pendingSummary, offerSummary, consumeSummary],
  );

  return (
    <MapSummaryContext.Provider value={value}>
      {children}
    </MapSummaryContext.Provider>
  );
}

// For components that may render outside the provider: null means no map panel.
export function useOptionalMapSummary(): MapSummaryContextValue | null {
  return useContext(MapSummaryContext);
}

export function useMapSummary(): MapSummaryContextValue {
  const context = useContext(MapSummaryContext);
  if (!context) {
    throw new Error('useMapSummary must be used inside MapSummaryProvider');
  }
  return context;
}
