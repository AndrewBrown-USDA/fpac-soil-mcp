import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { identifyOverlaysAtPoint, isIdentifiableOverlayId } from './identify';

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
