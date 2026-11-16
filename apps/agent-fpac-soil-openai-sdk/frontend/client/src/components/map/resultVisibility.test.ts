import assert from 'node:assert/strict';
import test from 'node:test';
import { renderMapBlock } from './mapLayers';
import type { MapBlock } from './mapLayers';
import { setLayerVisibility } from './mapControls';
import { NO_OVERLAYS } from './OverlayControl';
import { showNewScreeningResult } from './resultVisibility';

const block: MapBlock = {
  layers: [{
    id: 'farmland_classes', title: 'Farmland', kind: 'polygon',
    delivery: 'inline_geojson', authority: 'machine_estimate', source: 'SDA',
    feature_collection: {
      type: 'FeatureCollection',
      features: [{ type: 'Feature', geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] }, properties: {} }],
    },
  }],
};

test('new screening restores result layers without enabling SSURGO context', () => {
  const layers: Array<{ id: string; layout?: { visibility?: string } }> = [{ id: 'aoi-line' }];
  const sources: Record<string, unknown> = {};
  const map = {
    getStyle: () => ({ layers, sources }),
    getLayer: (id: string) => layers.find((layer) => layer.id === id),
    addLayer: (layer: { id: string }) => layers.push(layer),
    removeLayer: (id: string) => layers.splice(layers.findIndex((layer) => layer.id === id), 1),
    addSource: (id: string, source: unknown) => { sources[id] = source; },
    removeSource: (id: string) => { delete sources[id]; },
    hasImage: () => true,
    setLayoutProperty: (id: string, _property: 'visibility', value: 'visible' | 'none') => {
      const layer = layers.find((item) => item.id === id);
      assert.ok(layer);
      layer.layout = { visibility: value };
    },
  };
  const overlays = { ...NO_OVERLAYS };
  let visible = false; // User hid the previous result.
  const setVisible = (next: boolean) => { visible = next; };
  const applyVisibility = () => setLayerVisibility(map.setLayoutProperty, layers.map((layer) => layer.id).filter((id) => id.startsWith('result-')), visible);

  // This is the old behavior: rendering a fresh block preserves the hidden state.
  renderMapBlock(map as never, block, 'aoi-line');
  applyVisibility();
  assert.equal(layers.find((layer) => layer.id === 'result-farmland_classes-fill')?.layout?.visibility, 'none');

  showNewScreeningResult('running', 'done', setVisible);
  applyVisibility(); // The panel keeps these layers when switching Results → Map.
  const results = () => layers.filter((layer) => layer.id.startsWith('result-'));
  assert.ok(results().length >= 3);
  assert.ok(results().every((layer) => layer.layout?.visibility === 'visible'));
  assert.equal(overlays.ssurgo, false);

  setVisible(false); // Explicit hide after return, followed by tab/old-result selection.
  applyVisibility();
  showNewScreeningResult('done', 'done', setVisible);
  assert.ok(results().every((layer) => layer.layout?.visibility === 'none'));
  assert.equal(visible, false);
  showNewScreeningResult('running', 'error', setVisible);
  assert.equal(visible, false);

  overlays.ssurgo = true; // A separately enabled context overlay stays enabled.
  showNewScreeningResult('running', 'done', setVisible);
  renderMapBlock(map as never, block, 'aoi-line');
  applyVisibility();
  assert.ok(results().every((layer) => layer.layout?.visibility === 'visible'));
  assert.equal(overlays.ssurgo, true);
});
