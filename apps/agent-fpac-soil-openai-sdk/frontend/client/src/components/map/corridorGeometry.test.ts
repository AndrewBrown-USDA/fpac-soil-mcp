import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  BUFFER_SIDE_NOTICE,
  DEFAULT_CORRIDOR_UNIT,
  combineStagingAreas,
  createCorridorInput,
  isCorridorPolygon,
  isLineGeometry,
} from './corridorGeometry';

const line = { type: 'LineString' as const, coordinates: [[-100, 40], [-99, 41]] };
const polygon = {
  type: 'Polygon' as const,
  coordinates: [[[-100, 40], [-99, 40], [-99, 41], [-100, 40]]],
};

test('validates LineString and Polygon/MultiPolygon geometry', () => {
  assert.equal(isLineGeometry(line), true);
  assert.equal(isLineGeometry({ ...line, coordinates: [[0, 0]] }), false);
  assert.equal(isCorridorPolygon(polygon), true);
  assert.equal(isCorridorPolygon(combineStagingAreas([polygon, polygon])), true);
  assert.equal(isCorridorPolygon({ ...polygon, coordinates: [] }), false);
});

test('combines staging areas and preserves alternative labels outside MCP geometry', () => {
  const combined = combineStagingAreas([polygon, polygon]);
  assert.equal(combined?.type, 'MultiPolygon');
  assert.deepEqual(
    createCorridorInput(line, [{ label: 'North route', geometry: line }], [polygon], '100', 'feet'),
    {
      centerline: line,
      buffer_distance: 100,
      buffer_units: 'feet',
      alternatives: [line],
      indirect_geometry: polygon,
    },
  );
  assert.deepEqual(createCorridorInput(line, [], [], '100', 'feet')?.alternatives, []);
});

test('rejects missing/non-positive buffers and incomplete corridor inputs', () => {
  assert.equal(createCorridorInput(line, [], [], '', 'feet'), null);
  assert.equal(createCorridorInput(line, [], [], '0', 'feet'), null);
  assert.equal(createCorridorInput(null, [], [], '10', 'feet'), null);
  assert.equal(createCorridorInput(line, [{ label: '', geometry: line }], [], '10', 'feet'), null);
});

test('defaults buffer units to feet and discloses per-side semantics', () => {
  assert.equal(DEFAULT_CORRIDOR_UNIT, 'feet');
  assert.match(BUFFER_SIDE_NOTICE, /each side/i);
});
