import { createRoot } from 'react-dom/client';
import { useEffect } from 'react';
import '@/index.css';
import { ActiveAoiProvider, useActiveAoi } from './ActiveAoiContext';
import { ActiveCorridorProvider, useOptionalActiveCorridor } from './ActiveCorridorContext';
import { ActiveAoiChip } from './ActiveAoiChip';
import { MapResultProvider, useMapResult } from './MapResultContext';
import { MapPanel } from './MapPanel';
import { ShowOnMapButton } from './ShowOnMapButton';

// Test-only fixture (issue #89): AOI and corridor chat state with a switchable
// fake chat id. `?chat=none` starts with no chat id. The probe exposes the state
// the specs assert on; geo requests are faked by Playwright routes.
const CHATS = ['fixture-chat-a', 'fixture-chat-b'] as const;

function StateProbe() {
  const aoi = useActiveAoi();
  const corridor = useOptionalActiveCorridor();
  const { shown } = useMapResult();
  return (
    <output
      data-testid="fixture-state"
      data-shown={shown ? shown.origin : ''}
      data-chat-id={aoi.chatId ?? ''}
      data-corridor-chat-id={corridor?.chatId ?? ''}
      data-aoi-ref={aoi.activeAoi?.aoi_ref ?? ''}
      data-aoi-geometry={aoi.activeAoi ? JSON.stringify(aoi.activeAoi.geometry) : ''}
      data-aoi-summary={aoi.activeAoi?.summary ? JSON.stringify(aoi.activeAoi.summary) : ''}
      data-corridor-ref={corridor?.activeCorridor?.corridor_ref ?? ''}
      style={{ display: 'none' }}
    />
  );
}

// A tool-result card's Show on map, bound to the current AOI (issue #89 B2).
function FixtureShowOnMap() {
  const { activeAoi } = useActiveAoi();
  return (
    <ShowOnMapButton
      tool="analyze_farmland_by_polygon"
      toolCallId="fixture-map-call"
      input={{ aoi_ref: activeAoi?.aoi_ref ?? 'aoi-00000000' }}
    />
  );
}

function Fixture() {
  const { setChatId: setAoiChatId } = useActiveAoi();
  const setCorridorChatId = useOptionalActiveCorridor()?.setChatId;
  // null mimics the chat view unmounting ("Loading chat...").
  const select = (chatId: string | null) => {
    setAoiChatId(chatId);
    setCorridorChatId?.(chatId);
  };
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('chat') === 'none') return;
    setAoiChatId(CHATS[0]);
    setCorridorChatId?.(CHATS[0]);
  }, [setAoiChatId, setCorridorChatId]);
  return (
    <MapResultProvider>
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', gap: 8, padding: 4 }}>
          <button type="button" onClick={() => select(CHATS[0])}>Fixture chat A</button>
          <button type="button" onClick={() => select(CHATS[1])}>Fixture chat B</button>
          <button type="button" onClick={() => select(null)}>Close fixture chat</button>
          <ActiveAoiChip />
          <FixtureShowOnMap />
        </div>
        <StateProbe />
        <div style={{ flex: 1, minHeight: 0 }}>
          <MapPanel
            onCloseMap={() => {}}
            onMapReady={(map) => {
              (window as unknown as { __mapJumpTo?: (center: [number, number], zoom: number) => void }).__mapJumpTo =
                (center, zoom) => map.jumpTo({ center, zoom });
            }}
          />
        </div>
      </div>
    </MapResultProvider>
  );
}

const root = document.getElementById('root');
if (root) createRoot(root).render(<ActiveAoiProvider><ActiveCorridorProvider><Fixture /></ActiveCorridorProvider></ActiveAoiProvider>);
