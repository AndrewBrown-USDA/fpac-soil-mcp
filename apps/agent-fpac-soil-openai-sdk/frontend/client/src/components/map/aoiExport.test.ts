import assert from 'node:assert/strict';
import test from 'node:test';
import { parseAoiText } from './geojson';
import type { PolygonGeometry } from './geojson';
import { aoiFilename, serializeAoiGeoJson } from './aoiExport';

const polygon: PolygonGeometry = {
  type: 'Polygon',
  coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]],
};
const multiPolygon: PolygonGeometry = {
  type: 'MultiPolygon',
  coordinates: [polygon.coordinates],
};

test('serializes a labeled polygon as valid importable GeoJSON', () => {
  const text = serializeAoiGeoJson(polygon, '  Project site  ');
  const feature = JSON.parse(text).features[0];
  assert.deepEqual(feature.properties, { label: 'Project site' });
  assert.deepEqual(parseAoiText(text), { ok: true, geometry: polygon });
});

test('serializes a MultiPolygon and omits empty labels', () => {
  const feature = JSON.parse(serializeAoiGeoJson(multiPolygon, ' ')).features[0];
  assert.deepEqual(feature.properties, {});
  assert.deepEqual(parseAoiText(JSON.stringify(feature)), { ok: true, geometry: multiPolygon });
});

test('sanitizes filenames and supplies a default', () => {
  assert.equal(aoiFilename('../North site!'), 'North-site.geojson');
  assert.equal(aoiFilename(''), 'aoi.geojson');
});
