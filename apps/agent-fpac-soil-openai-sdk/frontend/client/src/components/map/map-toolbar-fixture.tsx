import { createRoot } from 'react-dom/client';
import '@/index.css';
import { ActiveAoiProvider } from './ActiveAoiContext';
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

const root = document.getElementById('root');
if (root) createRoot(root).render(
  <ActiveAoiProvider>
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
