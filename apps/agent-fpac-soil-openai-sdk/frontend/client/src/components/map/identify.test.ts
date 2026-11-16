import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { fetchOutline, identifyOverlaysAtPoint, isIdentifiableOverlayId } from './identify';

test('identify popup omits the estimate phrase while screening retains its authority notice', async () => {
  const popup = await readFile(new URL('./IdentifyPopup.tsx', import.meta.url), 'utf8');
  const screening = await readFile(new URL('./ScreeningResults.tsx', import.meta.url), 'utf8');

  assert.ok(!popup.includes('Preliminary machine estimate'));
  assert.match(screening, /Regulatory notice/);
  assert.match(screening, /\{notice\}/);
});

test('a click with only the CDL overlay active does not request TIGERweb', () => {
  const requests: string[] = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (input) => {
    requests.push(String(input));
    return new Response('{}');
  };

  try {
    const active = ['cdl'] as const;
    const identifiable = active.filter(isIdentifiableOverlayId);
    const queries = identifyOverlaysAtPoint(
      identifiable,
      -98,
      39,
      new AbortController().signal,
    );

    assert.deepEqual(queries, []);
    assert.deepEqual(requests, []);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('county outline response retains its authoritative GEOID and exact polygon', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (input) => {
    const url = new URL(String(input));
    assert.match(url.searchParams.get('where') ?? '', /GEOID='01001'/);
    return new Response(JSON.stringify({
      features: [{
        properties: { GEOID: '01001', NAME: 'Autauga County' },
        geometry: {
          type: 'Polygon',
          coordinates: [[[-87, 32], [-86, 32], [-86, 33], [-87, 33], [-87, 32]]],
        },
      }],
    }));
  };
  try {
    const result = await fetchOutline('counties', '01001', new AbortController().signal);
    assert.deepEqual(result, {
      geoid: '01001',
      name: 'Autauga County',
      geometry: {
        type: 'Polygon',
        coordinates: [[[-87, 32], [-86, 32], [-86, 33], [-87, 33], [-87, 32]]],
      },
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('popup exposes compact exact and bbox options with vertex-cap semantics', async () => {
  const popup = await readFile(new URL('./IdentifyPopup.tsx', import.meta.url), 'utf8');
  assert.match(popup, /Exact/);
  assert.match(popup, /BBOX/);
  assert.match(popup, /countVertices\(exact\) <= MAX_AOI_VERTICES/);
  assert.match(popup, /Use the exact polygon as the AOI/);
  assert.match(popup, /Use the bounding box as the AOI/);
});
