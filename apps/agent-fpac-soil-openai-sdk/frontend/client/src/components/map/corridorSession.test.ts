import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  loadCorridor,
  saveCorridor,
  type ActiveCorridor,
} from './corridorSession';
import { postRequestBodySchema } from '../../../../packages/core/src/schemas/chat';

const storage = new Map<string, string>();
Object.defineProperty(globalThis, 'sessionStorage', {
  configurable: true,
  value: {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  },
});

const corridor: ActiveCorridor = {
  corridor_ref: 'corridor-0123abcd',
  centerline: {
    type: 'LineString',
    coordinates: [
      [-100, 40],
      [-99, 41],
    ],
  },
  buffer_distance: 50,
  buffer_units: 'feet',
  alternatives: [],
};

test('saves/restores independently by chat and detaches only that chat', () => {
  saveCorridor('chat-a', corridor);
  saveCorridor('chat-b', { ...corridor, corridor_ref: 'corridor-ffffffff' });
  assert.deepEqual(loadCorridor('chat-a'), corridor);
  assert.equal(loadCorridor('chat-b')?.corridor_ref, 'corridor-ffffffff');
  saveCorridor('chat-a', null);
  assert.equal(loadCorridor('chat-a'), null);
  assert.equal(loadCorridor('chat-b')?.corridor_ref, 'corridor-ffffffff');
});

test('drops malformed stored corridor values', () => {
  sessionStorage.setItem('fpac-map-corridor:bad', '{');
  assert.equal(loadCorridor('bad'), null);
  sessionStorage.setItem(
    'fpac-map-corridor:invalid',
    JSON.stringify({ ...corridor, buffer_distance: Number.POSITIVE_INFINITY }),
  );
  assert.equal(loadCorridor('invalid'), null);
});

test('chat schema drops malformed corridor and retains valid AOI plus corridor', () => {
  const base = {
    id: '00000000-0000-4000-8000-000000000001',
    message: {
      id: '00000000-0000-4000-8000-000000000002',
      role: 'user',
      parts: [{ type: 'text', text: 'screen' }],
    },
    selectedChatModel: 'chat-model',
    selectedVisibilityType: 'private',
    activeAoi: {
      aoi_ref: 'aoi-0123abcd',
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 0],
          ],
        ],
      },
    },
  };
  const both = postRequestBodySchema.parse({
    ...base,
    activeCorridor: corridor,
  });
  assert.deepEqual(both.activeAoi, base.activeAoi);
  assert.deepEqual(both.activeCorridor, corridor);
  const malformed = postRequestBodySchema.parse({
    ...base,
    activeCorridor: { ...corridor, corridor_ref: 'bad' },
  });
  assert.equal(malformed.activeCorridor, undefined);
});

test('provider injects corridor into custom_inputs and release drops it', async () => {
  process.env.API_PROXY = '1';
  const provider = await import('@databricks/chatbot-ai-sdk-providers');
  const originalFetch = globalThis.fetch;
  let captured: Record<string, unknown> | undefined;
  globalThis.fetch = async (_input, init) => {
    captured = JSON.parse(String(init?.body));
    return new Response('{}', { status: 200 });
  };
  const key = provider.registerActiveCorridor(corridor);
  const headers = new Headers({
    'x-databricks-conversation-id': 'chat-1',
    'x-databricks-user-id': 'user-1',
    [provider.CONTEXT_HEADER_ACTIVE_CORRIDOR_KEY]: key,
  });
  try {
    await provider.databricksFetch('https://example.test', {
      method: 'POST',
      headers,
      body: '{}',
    });
    assert.deepEqual(
      (captured?.custom_inputs as Record<string, unknown>).active_corridor,
      corridor,
    );
    provider.releaseActiveCorridor(key);
    captured = undefined;
    await provider.databricksFetch('https://example.test', {
      method: 'POST',
      headers,
      body: '{}',
    });
    assert.equal(captured?.custom_inputs, undefined);
  } finally {
    provider.releaseActiveCorridor(key);
    globalThis.fetch = originalFetch;
  }
});
