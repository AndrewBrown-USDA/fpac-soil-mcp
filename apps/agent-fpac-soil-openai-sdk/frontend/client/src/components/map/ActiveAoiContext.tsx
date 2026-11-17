import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { toPolygonGeometry } from './geojson';
import type { PolygonGeometry } from './geojson';

// The map AOI is chat session context (ADR 0016): one AOI per conversation, kept in
// sessionStorage under the chat id and sent with every chat turn as `activeAoi`.
// `summary` is the server-built `chat_summary` of the latest screening.
export type ActiveAoi = {
  aoi_ref: string;
  geometry: PolygonGeometry;
  summary: Record<string, unknown> | null;
};

const STORAGE_PREFIX = 'fpac-map-aoi:';
const AOI_REF = /^aoi-[0-9a-f]{8}$/;
export const GEOMETRY_ATTACH_EVENT = 'fpac:geometry-attached';

export function newAoiRef(): string {
  const bytes = new Uint8Array(4);
  crypto.getRandomValues(bytes);
  return `aoi-${Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function load(chatId: string): ActiveAoi | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_PREFIX + chatId);
    if (!raw) return null;
    const value: unknown = JSON.parse(raw);
    if (!isRecord(value)) return null;
    const geometry = toPolygonGeometry(value.geometry);
    if (typeof value.aoi_ref !== 'string' || !AOI_REF.test(value.aoi_ref) || !geometry) {
      return null;
    }
    return {
      aoi_ref: value.aoi_ref,
      geometry,
      summary: isRecord(value.summary) ? value.summary : null,
    };
  } catch {
    return null;
  }
}

function save(chatId: string | null, aoi: ActiveAoi | null) {
  if (!chatId) return;
  try {
    if (aoi) {
      sessionStorage.setItem(STORAGE_PREFIX + chatId, JSON.stringify(aoi));
    } else {
      sessionStorage.removeItem(STORAGE_PREFIX + chatId);
    }
  } catch {
    // Storage full or unavailable: the AOI still works until the page reloads.
  }
}

type State = { chatId: string | null; aoi: ActiveAoi | null };

type ActiveAoiContextValue = {
  chatId: string | null;
  activeAoi: ActiveAoi | null;
  // Called by the chat view; switching chats loads that chat's AOI (or none).
  // Null while no chat is open: the AOI is cleared and writes are ignored.
  setChatId: (chatId: string | null) => void;
  // A new geometry gets a new reference; null detaches the AOI.
  setGeometry: (geometry: PolygonGeometry | null) => void;
  // Ignored unless `aoiRef` is still the attached AOI.
  setSummary: (aoiRef: string, summary: Record<string, unknown>) => void;
  detach: () => void;
};

const ActiveAoiContext = createContext<ActiveAoiContextValue | null>(null);

export function ActiveAoiProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>({ chatId: null, aoi: null });
  // Read synchronously by setGeometry, so no attach event fires without a chat.
  const chatIdRef = useRef<string | null>(null);

  const setChatId = useCallback((chatId: string | null) => {
    chatIdRef.current = chatId;
    setState((prev) =>
      prev.chatId === chatId ? prev : { chatId, aoi: chatId ? load(chatId) : null },
    );
  }, []);

  // Without an open chat there is nowhere to attach geometry (issue #89 B1).
  const setGeometry = useCallback((geometry: PolygonGeometry | null) => {
    if (!chatIdRef.current) return;
    if (geometry) window.dispatchEvent(new CustomEvent(GEOMETRY_ATTACH_EVENT, { detail: 'aoi' }));
    setState((prev) => {
      if (!prev.chatId) return prev;
      const aoi = geometry ? { aoi_ref: newAoiRef(), geometry, summary: null } : null;
      save(prev.chatId, aoi);
      return { ...prev, aoi };
    });
  }, []);

  useEffect(() => {
    const detach = (event: Event) => {
      if ((event as CustomEvent).detail !== 'corridor') return;
      setState((prev) => {
        if (!prev.aoi || !prev.chatId) return prev;
        save(prev.chatId, null);
        return { ...prev, aoi: null };
      });
    };
    window.addEventListener(GEOMETRY_ATTACH_EVENT, detach);
    return () => window.removeEventListener(GEOMETRY_ATTACH_EVENT, detach);
  }, []);

  const setSummary = useCallback((aoiRef: string, summary: Record<string, unknown>) => {
    setState((prev) => {
      if (!prev.chatId || prev.aoi?.aoi_ref !== aoiRef) return prev;
      const aoi = { ...prev.aoi, summary };
      save(prev.chatId, aoi);
      return { ...prev, aoi };
    });
  }, []);

  const detach = useCallback(() => setGeometry(null), [setGeometry]);

  const value = useMemo(
    () => ({
      chatId: state.chatId,
      activeAoi: state.aoi,
      setChatId,
      setGeometry,
      setSummary,
      detach,
    }),
    [state, setChatId, setGeometry, setSummary, detach],
  );

  return <ActiveAoiContext.Provider value={value}>{children}</ActiveAoiContext.Provider>;
}

// For components that may render outside the provider: null means no map panel.
export function useOptionalActiveAoi(): ActiveAoiContextValue | null {
  return useContext(ActiveAoiContext);
}

export function useActiveAoi(): ActiveAoiContextValue {
  const context = useContext(ActiveAoiContext);
  if (!context) {
    throw new Error('useActiveAoi must be used inside ActiveAoiProvider');
  }
  return context;
}
