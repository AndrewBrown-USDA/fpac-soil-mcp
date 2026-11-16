import { createRoot } from 'react-dom/client';
import '@/index.css';
import { ActiveAoiProvider } from './ActiveAoiContext';
import { MapResultProvider } from './MapResultContext';
import { MapPanel } from './MapPanel';

const root = document.getElementById('root');
if (root) createRoot(root).render(<ActiveAoiProvider><MapResultProvider><div style={{ height: '100vh' }}><MapPanel onCloseMap={() => {}} /></div></MapResultProvider></ActiveAoiProvider>);
