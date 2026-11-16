import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
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

type Value = {
  chatId: string | null;
  activeCorridor: ActiveCorridor | null;
  setChatId: (chatId: string) => void;
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
  const setChatId = useCallback((chatId: string) => {
    setState((prev) =>
      prev.chatId === chatId
        ? prev
        : { chatId, corridor: loadCorridor(chatId) },
    );
  }, []);
  const setCorridor = useCallback((corridor: ActiveCorridor | null) => {
    if (corridor && isActiveCorridor(corridor)) {
      window.dispatchEvent(
        new CustomEvent(GEOMETRY_ATTACH_EVENT, { detail: 'corridor' }),
      );
    }
    setState((prev) => {
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
        if (!prev.corridor) return prev;
        saveCorridor(prev.chatId, null);
        return { ...prev, corridor: null };
      });
    };
    window.addEventListener(GEOMETRY_ATTACH_EVENT, detach);
    return () => window.removeEventListener(GEOMETRY_ATTACH_EVENT, detach);
  }, []);
  const detach = useCallback(() => setCorridor(null), [setCorridor]);
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
