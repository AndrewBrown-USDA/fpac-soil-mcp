import assert from 'node:assert/strict';
import test from 'node:test';
import { identifyOverlaysAtPoint, isIdentifiableOverlayId } from './identify';

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
