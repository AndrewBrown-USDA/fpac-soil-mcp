import assert from 'node:assert/strict';
import { afterEach, before, test } from 'node:test';

// Issue #89 E: the chat stream keeps running after the client disconnects (it is
// teed into the resume cache), so a generateText fallback can run after
// res 'close'. That fallback must still send the map geometry context, so the
// keys are released by the caller when the stream finishes, never on 'close'
// (bindRequestGeometry takes no response object).

const AOI = { aoi_ref: 'aoi-0123abcd', geometry: { type: 'Polygon', coordinates: [] } };
const CORRIDOR = { corridor_ref: 'corridor-0123abcd' };

type Module = typeof import('./chat');
type Provider = typeof import('../../../packages/ai-sdk-providers/src/providers-server');
let chat: Module;
let provider: Provider;
const realFetch = globalThis.fetch;

before(async () => {
  // The provider injects context only for agent endpoints; API_PROXY selects that
  // path and is read once at import.
  process.env.API_PROXY = 'http://127.0.0.1:9/invocations';
  // Not `= undefined`: process.env would store the string "undefined".
  Reflect.deleteProperty(process.env, 'DATABRICKS_SERVING_ENDPOINT');
  provider = await import('../../../packages/ai-sdk-providers/src/providers-server');
  chat = await import('./chat');
});

afterEach(() => {
  globalThis.fetch = realFetch;
});

// Replays the request the generateText fallback makes, through the real provider
// fetch, and returns the custom_inputs it would send to the agent.
async function fallbackCustomInputs(geometryHeaders: Record<string, string>) {
  let sent: Record<string, unknown> | undefined;
  globalThis.fetch = (async (_url: unknown, init?: RequestInit) => {
    sent = JSON.parse(String(init?.body));
    return new Response('{}', { headers: { 'Content-Type': 'application/json' } });
  }) as typeof fetch;
  const log = console.log;
  console.log = () => {}; // databricksFetch logs request bodies
  try {
    await provider.databricksFetch(process.env.API_PROXY as string, {
      method: 'POST',
      body: JSON.stringify({ input: [] }),
      headers: {
        [provider.CONTEXT_HEADER_CONVERSATION_ID]: 'chat-1',
        [provider.CONTEXT_HEADER_USER_ID]: 'user-1',
        ...geometryHeaders,
      },
    });
  } finally {
    console.log = log;
  }
  return (sent?.custom_inputs ?? {}) as Record<string, unknown>;
}

test('a fallback after the client disconnects still sends the AOI and corridor', async () => {
  // Before the fix the keys were released on res 'close'; this replays the
  // fallback at that point, with the stream still running.
  const geometry = chat.bindRequestGeometry({ activeAoi: AOI, activeCorridor: CORRIDOR });

  const inputs = await fallbackCustomInputs(geometry.headers);

  assert.deepEqual(inputs.active_aoi, AOI);
  assert.deepEqual(inputs.active_corridor, CORRIDOR);
  geometry.release();
});

test('release() drops both keys, is idempotent, and the next request sends neither', async () => {
  const geometry = chat.bindRequestGeometry({ activeAoi: AOI, activeCorridor: CORRIDOR });
  assert.deepEqual((await fallbackCustomInputs(geometry.headers)).active_aoi, AOI);

  geometry.release();
  geometry.release();

  assert.deepEqual(await fallbackCustomInputs(geometry.headers), {});
});

test('a request without geometry registers nothing', async () => {
  const geometry = chat.bindRequestGeometry({});
  assert.deepEqual(geometry.headers, {});
  geometry.release();
});
