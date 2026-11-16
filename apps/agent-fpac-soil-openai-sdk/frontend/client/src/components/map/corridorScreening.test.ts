import assert from 'node:assert/strict';
import { afterEach, test } from 'node:test';
import { requestCorridorScreening } from './useCorridorScreening';

const corridor = {
  corridor_ref: 'corridor-0123abcd',
  centerline: { type: 'LineString', coordinates: [[-93, 42], [-92.9, 42.1]] },
  buffer_distance: 50,
  buffer_units: 'feet',
  alternatives: [],
};
const responseBody = {
  display: {
    corridor_ref: corridor.corridor_ref,
    status: 'preliminary_screening',
    buffer_distance: 50,
    buffer_units: 'feet',
    impact_breakdown: { direct_acres: 12.3, indirect_acres: 0, total_project_acres: 12.3 },
    composite_relative_rating: null,
    county_segments: [],
    alternatives: [],
  },
  map: { layers: [] },
  regulatory_notice: 'Preliminary screening only.',
  status: 'preliminary_screening',
};

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });

test('direct corridor request posts validated corridor and returns server result', async () => {
  let captured: RequestInit | undefined;
  globalThis.fetch = (async (input, init) => {
    assert.equal(input, '/api/geo/corridor');
    captured = init;
    return new Response(JSON.stringify(responseBody), { status: 200 });
  }) as typeof fetch;
  const outcome = await requestCorridorScreening(corridor);
  assert.equal(captured?.method, 'POST');
  assert.deepEqual(JSON.parse(String(captured?.body)), corridor);
  assert.equal(outcome.error, null);
  assert.deepEqual(outcome.result, responseBody);
});

test('corridor request reports bounded HTTP and connection errors', async () => {
  globalThis.fetch = (async () => new Response('', { status: 502 })) as typeof fetch;
  const unavailable = await requestCorridorScreening(corridor);
  assert.equal(unavailable.result, null);
  assert.match(unavailable.error ?? '', /unavailable/);

  globalThis.fetch = (async () => { throw new Error('private details'); }) as typeof fetch;
  const disconnected = await requestCorridorScreening(corridor);
  assert.equal(disconnected.result, null);
  assert.doesNotMatch(disconnected.error ?? '', /private details/);
});
