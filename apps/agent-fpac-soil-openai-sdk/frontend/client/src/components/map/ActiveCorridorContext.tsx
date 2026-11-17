import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import {
  isActiveCorridor,
  loadCorridor,
  saveCorridor,
} from './corridorSession';
import type { ActiveCorridor } from './corridorSession';
import { GEOMETRY_ATTACH_EVENT } from './ActiveAoiContext';

// Fired by the chip's Detach so the map panel clears the drawn corridor too
// (issue #89 C); there is no corridor Undo.
export const CORRIDOR_DETACH_EVENT = 'fpac:corridor-detach';

type Value = {
  chatId: string | null;
  activeCorridor: ActiveCorridor | null;
  // Null while no chat is open: the corridor is cleared and writes are ignored.
  setChatId: (chatId: string | null) => void;
  setCorridor: (corridor: ActiveCorridor | null) => void;
  detach: () => void;
};

const Context = createContext<Value | null>(null);

export function ActiveCorridorProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<{
    chatId: string | null;
    corridor: ActiveCorridor | null;
  }>({
    chatId: null,
    corridor: null,
  });
  // Read synchronously by setCorridor, so no attach event fires without a chat.
  const chatIdRef = useRef<string | null>(null);
  const setChatId = useCallback((chatId: string | null) => {
    chatIdRef.current = chatId;
    setState((prev) =>
      prev.chatId === chatId
        ? prev
        : { chatId, corridor: chatId ? loadCorridor(chatId) : null },
    );
  }, []);
  // Without an open chat there is nowhere to attach geometry (issue #89 B1).
  const setCorridor = useCallback((corridor: ActiveCorridor | null) => {
    if (!chatIdRef.current) return;
    if (corridor && isActiveCorridor(corridor)) {
      window.dispatchEvent(
        new CustomEvent(GEOMETRY_ATTACH_EVENT, { detail: 'corridor' }),
      );
    }
    setState((prev) => {
      if (!prev.chatId) return prev;
      const validCorridor =
        corridor && isActiveCorridor(corridor) ? corridor : null;
      saveCorridor(prev.chatId, validCorridor);
      return { ...prev, corridor: validCorridor };
    });
  }, []);
  useEffect(() => {
    const detach = (event: Event) => {
      if ((event as CustomEvent).detail !== 'aoi') return;
      setState((prev) => {
        if (!prev.corridor || !prev.chatId) return prev;
        saveCorridor(prev.chatId, null);
        return { ...prev, corridor: null };
      });
    };
    window.addEventListener(GEOMETRY_ATTACH_EVENT, detach);
    return () => window.removeEventListener(GEOMETRY_ATTACH_EVENT, detach);
  }, []);
  const detach = useCallback(() => {
    if (chatIdRef.current) window.dispatchEvent(new Event(CORRIDOR_DETACH_EVENT));
    setCorridor(null);
  }, [setCorridor]);
  const value = useMemo(
    () => ({
      chatId: state.chatId,
      activeCorridor: state.corridor,
      setChatId,
      setCorridor,
      detach,
    }),
    [state, setChatId, setCorridor, detach],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useOptionalActiveCorridor(): Value | null {
  return useContext(Context);
}
