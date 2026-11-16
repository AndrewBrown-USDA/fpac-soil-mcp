import {
  createContext,
  useCallback,
  useContext,
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
    setState((prev) => {
      const validCorridor =
        corridor && isActiveCorridor(corridor) ? corridor : null;
      saveCorridor(prev.chatId, validCorridor);
      return { ...prev, corridor: validCorridor };
    });
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
