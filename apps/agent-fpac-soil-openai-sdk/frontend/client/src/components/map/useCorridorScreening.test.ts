import assert from 'node:assert/strict';
import { afterEach, test } from 'node:test';
import type { ActiveCorridor } from './corridorSession';
import { requestCorridorScreening } from './useCorridorScreening';

const realFetch = globalThis.fetch;
const CORRIDOR = { corridor_ref: 'corridor-0123abcd' } as unknown as ActiveCorridor;

function respond(status: number, body: unknown) {
  globalThis.fetch = (async () =>
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })) as typeof fetch;
}

function response(notice: string | null) {
  return {
    display: { corridor_ref: 'corridor-0123abcd', status: 'preliminary_screening', impact_breakdown: {}, composite_relative_rating: null, county_segments: [], alternatives: [] },
    map: null,
    regulatory_notice: notice,
    status: 'preliminary_screening',
  };
}

afterEach(() => {
  globalThis.fetch = realFetch;
});

test('a corridor result with its notice is returned', async () => {
  respond(200, response('Preliminary screening only.'));
  const { result, error } = await requestCorridorScreening(CORRIDOR);
  assert.equal(error, null);
  assert.equal(result?.regulatory_notice, 'Preliminary screening only.');
});

test('a corridor result without a notice is kept so it can be shown as invalid', async () => {
  respond(200, response(null));
  const { result, error } = await requestCorridorScreening(CORRIDOR);
  assert.equal(error, null);
  assert.ok(result);
  assert.equal(result.regulatory_notice, null);
});

test('a corridor result without display or the preliminary status is rejected', async () => {
  respond(200, { ...response('n'), display: undefined });
  assert.equal((await requestCorridorScreening(CORRIDOR)).result, null);
  respond(200, { ...response('n'), status: 'final' });
  const { result, error } = await requestCorridorScreening(CORRIDOR);
  assert.equal(result, null);
  assert.equal(error, 'Corridor screening returned an incomplete result.');
});

test('a 502 is reported as unavailable', async () => {
  respond(502, { error: 'corridor_screening_unavailable' });
  const { result, error } = await requestCorridorScreening(CORRIDOR);
  assert.equal(result, null);
  assert.equal(error, 'Corridor screening unavailable. Try again later.');
});
