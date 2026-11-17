import { createRoot } from 'react-dom/client';
import { useEffect } from 'react';
import '@/index.css';
import { ActiveAoiProvider, useActiveAoi } from './ActiveAoiContext';
import { MapResultProvider } from './MapResultContext';
import { MapPanel } from './MapPanel';

declare global {
  interface Window {
    __mapCamera?: {
      read: () => { center: [number, number]; zoom: number };
      jumpTo: (center: [number, number], zoom: number) => void;
    };
  }
}

// The map only accepts AOI input inside an open chat (issue #89 B1).
function FixtureChat() {
  const { setChatId } = useActiveAoi();
  useEffect(() => {
    setChatId('fixture-chat');
  }, [setChatId]);
  return null;
}

const root = document.getElementById('root');
if (root) createRoot(root).render(
  <ActiveAoiProvider>
    <FixtureChat />
    <MapResultProvider>
      <div style={{ height: '100vh' }}><MapPanel onCloseMap={() => {}} onMapReady={(map) => {
        window.__mapCamera = {
          read: () => {
            const center = map.getCenter();
            return { center: [center.lng, center.lat], zoom: map.getZoom() };
          },
          jumpTo: (center, zoom) => map.jumpTo({ center, zoom }),
        };
      }} /></div>
    </MapResultProvider>
  </ActiveAoiProvider>,
);
