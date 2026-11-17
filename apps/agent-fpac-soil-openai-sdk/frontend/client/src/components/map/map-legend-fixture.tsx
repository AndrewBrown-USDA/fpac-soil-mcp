import { createRoot } from 'react-dom/client';
import { useEffect } from 'react';
import '@/index.css';
import { ActiveAoiProvider, useActiveAoi } from './ActiveAoiContext';
import { MapResultProvider, useMapResult } from './MapResultContext';
import { MapPanel } from './MapPanel';

// The map only accepts AOI input inside an open chat (issue #89 B1).
function FixtureChat() {
  const { setChatId } = useActiveAoi();
  useEffect(() => {
    setChatId('fixture-chat');
  }, [setChatId]);
  return null;
}

function Fixture() {
  const { show, clear } = useMapResult();
  return <div style={{ height: '100vh' }}>
    <button type="button" onClick={() => show({ origin: 'tool', regulatory_notice: 'Preliminary', block: { layers: [
      { id: 'tool', title: 'Tool layer', kind: 'polygon', delivery: 'omitted', authority: 'reference_data', source: 'Test source', legend: [{ value: 'custom', label: 'Server custom', code: 'Z9', color: '#123456', pattern: 'cross_hatch' }] },
      { id: 'farmland_classes', title: 'Farmland classes', kind: 'polygon', delivery: 'omitted', authority: 'machine_estimate', source: 'Farmland source', legend: [{ value: 'farmland', label: 'Server farmland', code: 'FC', color: '#654321', pattern: 'solid' }] },
    ], warnings: ['Server warning'] } })}>Show tool fixture</button>
    <button type="button" onClick={clear}>Clear fixture</button>
    <button type="button" onClick={() => show({ origin: 'tool', regulatory_notice: null, cdlSummary: { status: 'ok', product_vintage: null, vintage_verified: false, aoi: null, one_mile_ring: null, thirty_meter_band: null, limitations: [], error_message: null } })}>Show CDL fixture</button>
    <button type="button" onClick={() => show({ origin: 'tool', regulatory_notice: 'Fixture result', block: { layers: [
      { id: 'farmland_classes', title: 'Farmland classes', kind: 'polygon', delivery: 'inline_geojson', authority: 'machine_estimate', source: 'Fixture source', feature_collection: { type: 'FeatureCollection', features: [{ type: 'Feature', geometry: { type: 'Polygon', coordinates: [[[-93, 42], [-92.99, 42], [-92.99, 42.01], [-93, 42.01], [-93, 42]]] }, properties: { farmlndcl: 'Prime farmland' } }] }, legend: [{ value: 'prime', label: 'Prime farmland', code: 'P', color: '#2E7D32', pattern: 'solid' }] },
    ] } })}>Show overlap fixture</button>
    <MapPanel onCloseMap={() => {}} />
  </div>;
}

const root = document.getElementById('root');
if (root) createRoot(root).render(<ActiveAoiProvider><FixtureChat /><MapResultProvider><Fixture /></MapResultProvider></ActiveAoiProvider>);
