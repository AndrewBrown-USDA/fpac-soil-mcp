import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { MapBlock } from './mapLayers';
import type { CDLContextResult } from './CDLContextSummary';

// The one map result the panel shows: a finished screening or a tool card's
// "Show on map". The last action wins. React state only, never stored or logged.
export type ShownMapResult = {
  origin: 'screening' | 'tool';
  block?: MapBlock;
  cdlSummary?: CDLContextResult;
  regulatory_notice: string | null;
  tool?: string;
  toolCallId?: string;
};

type MapResultContextValue = {
  shown: ShownMapResult | null;
  show: (result: ShownMapResult) => void;
  clear: () => void;
};

const MapResultContext = createContext<MapResultContextValue | null>(null);

// `onShow` runs when a tool result is shown, so the layout can open the map panel.
export function MapResultProvider({
  children,
  onShow,
}: {
  children: ReactNode;
  onShow?: () => void;
}) {
  const [shown, setShown] = useState<ShownMapResult | null>(null);
  const show = useCallback(
    (result: ShownMapResult) => {
      setShown(result);
      if (result.origin === 'tool') onShow?.();
    },
    [onShow],
  );
  const clear = useCallback(() => setShown(null), []);
  const value = useMemo(() => ({ shown, show, clear }), [shown, show, clear]);
  return <MapResultContext.Provider value={value}>{children}</MapResultContext.Provider>;
}

// For components that may render outside the provider: null means no map panel.
export function useOptionalMapResult(): MapResultContextValue | null {
  return useContext(MapResultContext);
}

export function useMapResult(): MapResultContextValue {
  const context = useContext(MapResultContext);
  if (!context) {
    throw new Error('useMapResult must be used inside MapResultProvider');
  }
  return context;
}
