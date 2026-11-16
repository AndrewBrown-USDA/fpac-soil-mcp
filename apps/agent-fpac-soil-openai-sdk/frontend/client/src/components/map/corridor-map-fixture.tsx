import { createRoot } from 'react-dom/client';
import { useEffect } from 'react';
import '@/index.css';
import { ActiveAoiProvider, useActiveAoi } from './ActiveAoiContext';
import { ActiveCorridorProvider, useOptionalActiveCorridor } from './ActiveCorridorContext';
import { ActiveAoiChip } from './ActiveAoiChip';
import { MapResultProvider } from './MapResultContext';
import { MapPanel } from './MapPanel';

function Fixture() {
  const { setChatId: setAoiChatId } = useActiveAoi();
  const setCorridorChatId = useOptionalActiveCorridor()?.setChatId;
  useEffect(() => {
    setAoiChatId('corridor-fixture');
    setCorridorChatId?.('corridor-fixture');
  }, [setAoiChatId, setCorridorChatId]);
  return (
    <MapResultProvider>
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
        <ActiveAoiChip />
        <div style={{ flex: 1, minHeight: 0 }}>
          <MapPanel onCloseMap={() => {}} />
        </div>
      </div>
    </MapResultProvider>
  );
}
const root = document.getElementById('root');
if (root) createRoot(root).render(<ActiveAoiProvider><ActiveCorridorProvider><Fixture /></ActiveCorridorProvider></ActiveAoiProvider>);
