import { useState } from 'react';
import { createRoot } from 'react-dom/client';

function MapTabsFixture() {
  const [tab, setTab] = useState<'map' | 'results'>('map');
  const [screened, setScreened] = useState(false);
  const [toolResult, setToolResult] = useState(false);
  return (
    <main>
      <button type="button" onClick={() => { setScreened(true); setTab('results'); }}>Complete screening</button>
      <button type="button" onClick={() => setToolResult(true)}>Show tool result</button>
      <div role="tablist" aria-label="Map and screening results">
        {(['map', 'results'] as const).map((name) => <button key={name} type="button" role="tab" aria-selected={tab === name} aria-controls={`panel-${name}`} onClick={() => setTab(name)}>{name === 'map' ? 'Map' : 'Results'}</button>)}
      </div>
      <section id="panel-map" role="tabpanel" hidden={tab !== 'map'}>Map view</section>
      <section id="panel-results" role="tabpanel" hidden={tab !== 'results'}>
        {toolResult ? <><p>Tool result</p><button type="button" onClick={() => setToolResult(false)}>Back to screening results</button></> : screened ? <p>Screening details</p> : <p>Run a screening from the Map tab to see results here.</p>}
      </section>
    </main>
  );
}

const rootElement = document.getElementById('root');
if (rootElement) createRoot(rootElement).render(<MapTabsFixture />);
