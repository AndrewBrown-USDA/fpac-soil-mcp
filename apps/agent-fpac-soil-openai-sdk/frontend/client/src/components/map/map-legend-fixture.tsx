import { createRoot } from 'react-dom/client';
import '@/index.css';
import { ActiveAoiProvider } from './ActiveAoiContext';
import { MapResultProvider, useMapResult } from './MapResultContext';
import { MapPanel } from './MapPanel';

function Fixture() {
  const { show, clear } = useMapResult();
  return <div style={{ height: '100vh' }}>
    <button type="button" onClick={() => show({ origin: 'tool', regulatory_notice: 'Preliminary', block: { layers: [{ id: 'tool', title: 'Tool layer', kind: 'polygon', delivery: 'omitted', authority: 'reference_data', source: 'Test source', legend: [{ value: 'custom', label: 'Server custom', code: 'Z9', color: '#123456', pattern: 'cross_hatch' }] }], warnings: ['Server warning'] } })}>Show tool fixture</button>
    <button type="button" onClick={clear}>Clear fixture</button>
    <button type="button" onClick={() => show({ origin: 'tool', regulatory_notice: null, cdlSummary: { status: 'ok', product_vintage: null, vintage_verified: false, aoi: null, one_mile_ring: null, thirty_meter_band: null, limitations: [], error_message: null } })}>Show CDL fixture</button>
    <MapPanel onCloseMap={() => {}} />
  </div>;
}

const root = document.getElementById('root');
if (root) createRoot(root).render(<ActiveAoiProvider><MapResultProvider><Fixture /></MapResultProvider></ActiveAoiProvider>);
