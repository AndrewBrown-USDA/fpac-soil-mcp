import assert from 'node:assert/strict';
import test from 'node:test';
import { aoiFeaturesToRemove, aoiViewBounds, INITIAL_MAP_VIEW, measurementModeAfterCancel, setLayerVisibility } from './mapControls';
import type { PolygonGeometry } from './geojson';

const polygon: PolygonGeometry = { type: 'Polygon', coordinates: [[[1, 2], [4, 2], [4, 5], [1, 2]]] };

test('AOI zoom uses geometry bounds and reset view is the initial map extent', () => {
  assert.deepEqual(aoiViewBounds(polygon), [[1, 2], [4, 5]]);
  assert.equal(aoiViewBounds(null), null);
  assert.deepEqual(INITIAL_MAP_VIEW, { center: [-98, 39], zoom: 3 });
});

test('visibility changes only layer layout and does not mutate AOI/result data', () => {
  const aoi = structuredClone(polygon);
  const result = { type: 'FeatureCollection', features: [{ type: 'Feature', geometry: polygon, properties: { id: 'result' } }] };
  const updates: unknown[][] = [];
  setLayerVisibility((...args) => updates.push(args), ['aoi-line', 'result-area-fill'], false);
  assert.deepEqual(updates, [['aoi-line', 'visibility', 'none'], ['result-area-fill', 'visibility', 'none']]);
  assert.deepEqual(aoi, polygon);
  assert.equal(result.features.length, 1);
  assert.deepEqual(result.features[0].properties, { id: 'result' });
});

test('measurement cancellation returns to static mode without modifying AOI', () => {
  assert.equal(measurementModeAfterCancel(), 'static');
  assert.deepEqual(polygon.coordinates[0][0], [1, 2]);
});

const snapshot = [
  { id: 'old-polygon', properties: { mode: 'polygon' } },
  { id: 'old-rectangle', properties: { mode: 'rectangle' } },
  { id: 'new', properties: { mode: 'polygon' } },
  { id: 'selection-point', properties: { mode: 'select', selectionPoint: true } },
  { id: 'midpoint', properties: { mode: 'select', midPoint: true } },
  { properties: { mode: 'polygon' } },
];

test('a newly drawn AOI replaces only the previous AOI shapes', () => {
  assert.deepEqual(aoiFeaturesToRemove(snapshot, 'new', { mode: 'polygon' }), ['old-polygon', 'old-rectangle']);
  assert.deepEqual(aoiFeaturesToRemove(snapshot, 'new', { mode: 'rectangle' }), ['old-polygon', 'old-rectangle']);
});

test('an Edit-mode finish removes nothing, so Terra Draw keeps its selection and midpoint features', () => {
  assert.deepEqual(aoiFeaturesToRemove(snapshot, 'new', { mode: 'select' }), []);
});
