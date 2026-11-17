import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

// Offline AOI and corridor chat-state coverage (issue #89). Every geo request is
// faked; no SDA, MCP or TIGERweb traffic leaves the browser.

const SQUARE = '{"type":"Polygon","coordinates":[[[-93,42],[-92.99,42],[-92.99,42.01],[-93,42.01],[-93,42]]]}';
const NOTICE = 'Preliminary screening only.';

type FakeOptions = { delayMs?: number; fail?: boolean; notice?: string | null };

// Fakes the map panel's geo routes. `delayMs` holds each response so a spec can
// change chat or AOI first; `fail` returns the server's screening_failed shape
// (or a 502 for routes without one). Returns the requests seen, per route.
async function fakeGeo(page: Page, options: FakeOptions = {}) {
  const { delayMs = 0, fail = false } = options;
  const notice = options.notice === undefined ? NOTICE : options.notice;
  const seen = { screen: 0, corridor: 0, map: 0, outline: 0 };
  const hold = () => (delayMs ? new Promise((resolve) => setTimeout(resolve, delayMs)) : Promise.resolve());
  await page.route('**/api/geo/screen', async (route) => {
    seen.screen += 1;
    const body = route.request().postDataJSON() as { aoi_ref?: string };
    const aoiRef = body.aoi_ref ?? 'aoi-00000000';
    await hold();
    await route.fulfill({ json: fail
      ? {
          aoi_ref: aoiRef,
          display: { error: 'screening_failed', regulatory_notice: null },
          chat_summary: { aoi_ref: aoiRef, status: 'screening_failed' },
          chat_summary_text: 'Map screening result (preliminary)',
        }
      : {
          aoi_ref: aoiRef,
          display: {
            analysis: { map_units: [] },
            map: { bounds: [-93, 42, -92.99, 42.01], layers: [] },
            regulatory_notice: notice,
          },
          chat_summary: { aoi_ref: aoiRef, total_aoi_acres: 1, regulatory_notice: notice },
          chat_summary_text: 'Map screening result (preliminary)',
        } });
  });
  await page.route('**/api/geo/corridor', async (route) => {
    seen.corridor += 1;
    const request = route.request().postDataJSON() as { corridor_ref?: string };
    await hold();
    if (fail) return route.fulfill({ status: 502, json: { error: 'screening_unavailable' } });
    await route.fulfill({ json: {
      display: {
        corridor_ref: request.corridor_ref,
        status: 'preliminary_screening',
        impact_breakdown: { direct_acres: 1, indirect_acres: 0, total_project_acres: 1 },
        composite_relative_rating: null,
        county_segments: [],
        alternatives: [],
      },
      map: { layers: [] },
      regulatory_notice: notice,
      status: 'preliminary_screening',
    } });
  });
  await page.route('**/api/geo/map', async (route) => {
    seen.map += 1;
    await hold();
    if (fail) return route.fulfill({ status: 502, json: { error: 'map_unavailable' } });
    await route.fulfill({ json: {
      map: { bounds: [-93, 42, -92.99, 42.01], layers: [{ id: 'fake', title: 'Fake layer', kind: 'polygon', delivery: 'inline', data: { type: 'FeatureCollection', features: [] } }] },
      regulatory_notice: notice,
    } });
  });
  // Registered after the catch-all abort in beforeEach, so this one wins.
  await page.route('https://tigerweb.geo.census.gov/**', async (route) => {
    seen.outline += 1;
    await hold();
    if (fail) return route.abort();
    await route.fulfill({ json: { type: 'FeatureCollection', features: [] } });
  });
  return seen;
}

function probe(page: Page) {
  return page.getByTestId('fixture-state');
}

async function pasteAoi(page: Page, geojson = SQUARE) {
  await page.getByRole('button', { name: 'Paste' }).click();
  await page.getByLabel('GeoJSON Polygon or MultiPolygon').fill(geojson);
  await page.getByRole('button', { name: 'Use this AOI' }).click();
}

test.beforeEach(async ({ page }) => {
  await page.route('https://**/*', (route) => route.abort());
});

test('fixture loads on chat A and a pasted AOI is attached to it', async ({ page }) => {
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  await expect(probe(page)).toHaveAttribute('data-chat-id', 'fixture-chat-a');
  await expect(probe(page)).toHaveAttribute('data-corridor-chat-id', 'fixture-chat-a');
  await pasteAoi(page);
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', /^aoi-[0-9a-f]{8}$/);
  const geometry = JSON.parse((await probe(page).getAttribute('data-aoi-geometry')) ?? 'null');
  expect(geometry.type).toBe('Polygon');
});

test('a faked screening attaches its summary to the screened AOI', async ({ page }) => {
  const seen = await fakeGeo(page);
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  await pasteAoi(page);
  const ref = await probe(page).getAttribute('data-aoi-ref');
  await page.getByRole('button', { name: 'Run screening' }).click();
  await expect(page.getByRole('tab', { name: 'Results' })).toHaveAttribute('aria-selected', 'true');
  await expect(probe(page)).toHaveAttribute('data-aoi-summary', /total_aoi_acres/);
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', ref ?? '');
  expect(seen.screen).toBe(1);
});

const INVALID = 'Regulatory notice missing - treat this result as invalid.';

test('a screening without an MCP notice is shown as invalid and is not attached', async ({ page }) => {
  await fakeGeo(page, { notice: null });
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  await pasteAoi(page);
  await page.getByRole('button', { name: 'Run screening' }).click();
  await expect(page.getByRole('tab', { name: 'Results' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByText(INVALID).first()).toBeVisible();
  await expect(probe(page)).toHaveAttribute('data-aoi-summary', '');
});

test('a failed screening attaches its screening_failed summary to the screened AOI', async ({ page }) => {
  await fakeGeo(page, { fail: true });
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  await pasteAoi(page);
  const ref = await probe(page).getAttribute('data-aoi-ref');
  await page.getByRole('button', { name: 'Run screening' }).click();
  await expect(probe(page)).toHaveAttribute('data-aoi-summary', /screening_failed/);
  const summary = JSON.parse((await probe(page).getAttribute('data-aoi-summary')) ?? 'null');
  expect(summary.aoi_ref).toBe(ref);
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', ref ?? '');
});

test('a corridor result without an MCP notice is shown as invalid, not as an error', async ({ page }) => {
  await fakeGeo(page, { notice: null });
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  await page.getByRole('button', { name: 'Corridor', exact: true }).click();
  await page.getByText('Corridor options', { exact: true }).click();
  await page.getByRole('button', { name: 'Draw primary line' }).click();
  const map = page.locator('.maplibregl-map');
  await map.click({ position: { x: 120, y: 130 } });
  await map.dblclick({ position: { x: 200, y: 190 } });
  await expect(page.getByText(/Primary ready/)).toBeVisible();
  await page.getByLabel('Required buffer distance').fill('50');
  await page.getByRole('button', { name: 'Screen corridor' }).click();
  await expect(page.getByRole('tab', { name: 'Results' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('region', { name: 'Corridor screening summary' })).toBeVisible();
  await expect(page.getByText(INVALID).first()).toBeVisible();
  await expect(page.getByText('Corridor screening returned an incomplete result.')).toHaveCount(0);
});

function attachedRing(page: Page) {
  return probe(page)
    .getAttribute('data-aoi-geometry')
    .then((value) => (value ? (JSON.parse(value).coordinates[0] as number[][]) : []));
}

test('every Edit change keeps the attached AOI equal to the shape on the map', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(String(error)));
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  const map = page.locator('.maplibregl-map');
  // Drawing does not move the view, so the vertices stay at these pixels.
  await page.getByRole('button', { name: 'Polygon' }).click();
  for (const [x, y] of [[100, 100], [200, 100], [200, 200], [100, 200]]) {
    await map.click({ position: { x, y } });
  }
  await map.dblclick({ position: { x: 100, y: 100 } });
  await expect.poll(async () => (await attachedRing(page)).length).toBe(5);
  const drawn = await attachedRing(page);

  await page.getByRole('button', { name: 'Edit', exact: true }).click();
  await map.click({ position: { x: 150, y: 150 } });
  const box = await map.boundingBox();
  if (!box) throw new Error('map has no box');
  await page.mouse.move(box.x + 200, box.y + 200);
  await page.mouse.down();
  await page.mouse.move(box.x + 220, box.y + 220, { steps: 8 });
  await page.mouse.move(box.x + 240, box.y + 240, { steps: 8 });
  await page.mouse.up();
  await expect.poll(() => attachedRing(page)).not.toEqual(drawn);
  expect(await attachedRing(page)).toHaveLength(5);

  await map.click({ position: { x: 150, y: 100 } }); // midpoint of the top edge
  await expect.poll(async () => (await attachedRing(page)).length).toBe(6);

  await map.click({ button: 'right', position: { x: 100, y: 200 } }); // a vertex
  await expect.poll(async () => (await attachedRing(page)).length).toBe(5);
  expect(errors).toEqual([]);
});

function stored(page: Page, chatId: string) {
  return page.evaluate((id) => ({
    aoi: sessionStorage.getItem(`fpac-map-aoi:${id}`),
    corridor: sessionStorage.getItem(`fpac-map-corridor:${id}`),
  }), chatId);
}

async function drawCorridor(page: Page) {
  await page.getByRole('button', { name: 'Corridor', exact: true }).click();
  await page.getByText('Corridor options', { exact: true }).click();
  await page.getByLabel('Required buffer distance').fill('50');
  await page.getByRole('button', { name: 'Draw primary line' }).click();
  const map = page.locator('.maplibregl-map');
  await map.click({ position: { x: 120, y: 130 } });
  await map.dblclick({ position: { x: 200, y: 190 } });
  await expect(page.getByText(/Primary ready/)).toBeVisible();
}

test('a hung basemap tile does not keep the drawing tools disabled', async ({ page }) => {
  // Registered after the catch-all abort, so it wins: tile requests never answer.
  await page.route('https://basemap.nationalmap.gov/**', () => {});
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  await pasteAoi(page);
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', /^aoi-/);
});

const NO_CHAT = 'Open or start a chat to draw, paste or attach an area or corridor.';

test('without an open chat the map takes no AOI or corridor input', async ({ page }) => {
  await page.goto('/aoi-state-fixture.html?chat=none');
  await expect(page.getByText(NO_CHAT)).toBeVisible();
  for (const name of ['Polygon', 'Rectangle', 'Edit', 'Paste']) {
    await expect(page.getByRole('button', { name, exact: true })).toBeDisabled();
  }
  await page.getByRole('button', { name: 'Corridor', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Draw primary line' })).toBeDisabled();
  await page.getByRole('button', { name: 'Fixture chat A' }).click();
  await expect(page.getByRole('button', { name: 'Draw primary line' })).toBeEnabled();
  await expect(page.getByText(NO_CHAT)).toHaveCount(0);
});

test('closing the chat clears map context without touching its storage; reopening restores it', async ({ page }) => {
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  await pasteAoi(page);
  const ref = await probe(page).getAttribute('data-aoi-ref');
  const before = await stored(page, 'fixture-chat-a');
  expect(before.aoi).toContain(ref ?? 'missing');

  await page.getByRole('button', { name: 'Close fixture chat' }).click();
  await expect(probe(page)).toHaveAttribute('data-chat-id', '');
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', '');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Paste' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Clear', exact: true })).toBeDisabled();
  expect(await stored(page, 'fixture-chat-a')).toEqual(before);

  await page.getByRole('button', { name: 'Fixture chat A' }).click();
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', ref ?? '');
});

test('switching A -> B -> A keeps each chat\'s AOI and corridor in its own storage', async ({ page }) => {
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  await pasteAoi(page);
  const aoiRef = await probe(page).getAttribute('data-aoi-ref');

  await page.getByRole('button', { name: 'Fixture chat B' }).click();
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', '');
  await drawCorridor(page);
  await expect(probe(page)).toHaveAttribute('data-corridor-ref', /.+/);
  const corridorB = (await stored(page, 'fixture-chat-b')).corridor;
  expect(corridorB).toBeTruthy();

  await page.getByRole('button', { name: 'Fixture chat A' }).click();
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', aoiRef ?? '');
  await expect(probe(page)).toHaveAttribute('data-corridor-ref', '');
  const a = await stored(page, 'fixture-chat-a');
  expect(a.aoi).toContain(aoiRef ?? 'missing');
  expect(a.corridor).toBeNull();
  const b = await stored(page, 'fixture-chat-b');
  expect(b.aoi).toBeNull();
  expect(JSON.parse(b.corridor ?? 'null')?.centerline).toEqual(JSON.parse(corridorB ?? 'null')?.centerline);
});

test('each fixture chat keeps its own AOI, and ?chat=none starts without a chat', async ({ page }) => {
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  await pasteAoi(page);
  const ref = await probe(page).getAttribute('data-aoi-ref');
  await page.getByRole('button', { name: 'Fixture chat B' }).click();
  await expect(probe(page)).toHaveAttribute('data-chat-id', 'fixture-chat-b');
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', '');
  await page.getByRole('button', { name: 'Fixture chat A' }).click();
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', ref ?? '');

  await page.goto('/aoi-state-fixture.html?chat=none');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeVisible();
  await expect(probe(page)).toHaveAttribute('data-chat-id', '');
  await expect(probe(page)).toHaveAttribute('data-corridor-chat-id', '');
});
