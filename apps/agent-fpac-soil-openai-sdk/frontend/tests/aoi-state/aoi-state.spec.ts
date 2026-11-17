import { expect, test } from '@playwright/test';
import type { Page, Route } from '@playwright/test';

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
      map: { bounds: [-93, 42, -92.99, 42.01], layers: [{ id: 'fake', title: 'Fake layer', kind: 'polygon', delivery: 'inline_geojson', authority: 'reference_data', source: 'Fixture', legend: [], feature_collection: { type: 'FeatureCollection', features: [] } }] },
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
  const input = page.getByLabel('GeoJSON Polygon or MultiPolygon');
  // The Paste button toggles the panel; open it only when it is closed.
  if (!(await input.isVisible())) await page.getByRole('button', { name: 'Paste' }).click();
  await input.fill(geojson);
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

const SQUARE_2 = '{"type":"Polygon","coordinates":[[[-93.1,42],[-93.09,42],[-93.09,42.01],[-93.1,42.01],[-93.1,42]]]}';
const DELAY = 1500;
const showOnMap = (page: Page) => page.getByRole('button', { name: /^analyze_farmland_by_polygon:/ });

async function startOnChatA(page: Page) {
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  await pasteAoi(page);
}

test('Show on map shows a result that arrives while the chat and AOI are unchanged', async ({ page }) => {
  await fakeGeo(page);
  await startOnChatA(page);
  await showOnMap(page).click();
  await expect(probe(page)).toHaveAttribute('data-shown', 'tool');
});

test('Show on map drops a result that arrives after the AOI was replaced', async ({ page }) => {
  await fakeGeo(page, { delayMs: DELAY });
  await startOnChatA(page);
  const response = page.waitForResponse('**/api/geo/map');
  await showOnMap(page).click();
  await pasteAoi(page, SQUARE_2);
  await response;
  await expect(page.getByText('This map result is stale because the chat or AOI changed while it loaded.')).toBeVisible();
  await expect(probe(page)).toHaveAttribute('data-shown', '');
});

test('Show on map drops a result that arrives after the chat changed', async ({ page }) => {
  await fakeGeo(page, { delayMs: DELAY });
  await startOnChatA(page);
  const response = page.waitForResponse('**/api/geo/map');
  await showOnMap(page).click();
  await page.getByRole('button', { name: 'Fixture chat B' }).click();
  await response;
  await page.waitForTimeout(300);
  await expect(probe(page)).toHaveAttribute('data-shown', '');
});

test('a Show on map result without an MCP notice is shown as invalid', async ({ page }) => {
  await fakeGeo(page, { notice: null });
  await startOnChatA(page);
  await showOnMap(page).click();
  await expect(probe(page)).toHaveAttribute('data-shown', 'tool');
  await page.getByRole('tab', { name: 'Results' }).click();
  await expect(page.getByText(INVALID).first()).toBeVisible();
});

test('a corridor screening that returns after a chat switch is not shown', async ({ page }) => {
  await fakeGeo(page, { delayMs: DELAY });
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  await drawCorridor(page);
  const response = page.waitForResponse('**/api/geo/corridor');
  await page.getByRole('button', { name: 'Screen corridor' }).click();
  await page.getByRole('button', { name: 'Fixture chat B' }).click();
  await response;
  await page.waitForTimeout(300);
  await expect(page.getByRole('region', { name: 'Corridor screening summary' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Fixture chat A' }).click();
  await expect(page.getByRole('region', { name: 'Corridor screening summary' })).toHaveCount(0);
});

test('an AOI screening that returns after a chat switch attaches nothing (regression)', async ({ page }) => {
  await fakeGeo(page, { delayMs: DELAY });
  await startOnChatA(page);
  const response = page.waitForResponse('**/api/geo/screen');
  await page.getByRole('button', { name: 'Run screening' }).click();
  await page.getByRole('button', { name: 'Fixture chat B' }).click();
  await response;
  await page.waitForTimeout(300);
  await expect(probe(page)).toHaveAttribute('data-aoi-summary', '');
  await page.getByRole('button', { name: 'Fixture chat A' }).click();
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', /^aoi-/);
  await expect(probe(page)).toHaveAttribute('data-aoi-summary', '');
});

const HAMILTON = {
  type: 'FeatureCollection',
  features: [{
    type: 'Feature',
    properties: { GEOID: '20075', NAME: 'Hamilton County' },
    geometry: { type: 'Polygon', coordinates: [[[-102.05, 38.25], [-101.9, 38.25], [-101.9, 38.4], [-102.05, 38.4], [-102.05, 38.25]]] },
  }],
};

// Opens the Hamilton County identify popup with the identify-time outline failed,
// so "Use exact polygon" fetches the outline itself. Returns the held request.
async function openCountyPopup(page: Page) {
  const held: { route: Route | null; outlines: number } = { route: null, outlines: 0 };
  await page.route('https://tigerweb.geo.census.gov/**', async (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.has('geometry')) {
      return route.fulfill({ contentType: 'application/geo+json', json: { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { GEOID: '20075', NAME: 'Hamilton County' }, geometry: null }] } });
    }
    if (!url.searchParams.get('where')?.startsWith('GEOID')) return route.abort();
    held.outlines += 1;
    if (held.outlines === 1) return route.abort();
    held.route = route;
  });
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  await page.evaluate(() => {
    (window as unknown as { __mapJumpTo: (center: [number, number], zoom: number) => void }).__mapJumpTo([-101.975, 38.325], 7);
  });
  const layers = page.locator('details').filter({ has: page.getByText(/^Layers/) });
  await layers.locator('summary').click();
  await page.locator('#overlay-toggle-counties').check();
  const box = await page.locator('.maplibregl-canvas').boundingBox();
  if (!box) throw new Error('Map canvas is not visible');
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  const popup = page.locator('.maplibregl-popup-content');
  await expect(popup).toContainText('Hamilton County', { timeout: 15000 });
  await expect.poll(() => held.outlines).toBe(1);
  await popup.getByRole('button', { name: /Use exact polygon/ }).click();
  await expect.poll(() => held.route !== null).toBe(true);
  return { popup, held };
}

test('closing the identify popup aborts its outline request and attaches nothing', async ({ page }) => {
  const { popup } = await openCountyPopup(page);
  const failed: string[] = [];
  page.on('requestfailed', (request) => {
    if (request.url().includes('where=GEOID')) failed.push(request.failure()?.errorText ?? '');
  });
  await popup.locator('xpath=..').locator('.maplibregl-popup-close-button').click();
  await expect(popup).toHaveCount(0);
  await expect.poll(() => failed.length).toBeGreaterThan(0);
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', '');
});

test('an outline that returns after a chat switch attaches nothing', async ({ page }) => {
  const { held } = await openCountyPopup(page);
  await page.getByRole('button', { name: 'Fixture chat B' }).click();
  await expect(probe(page)).toHaveAttribute('data-chat-id', 'fixture-chat-b');
  await held.route?.fulfill({ contentType: 'application/geo+json', json: HAMILTON }).catch(() => {});
  await page.waitForTimeout(500);
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', '');
  await page.getByRole('button', { name: 'Fixture chat A' }).click();
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', '');
});

const undoButton = (page: Page) => page.getByRole('button', { name: 'Undo', exact: true });

test('Undo restores the replaced AOI with its reference and summary', async ({ page }) => {
  await fakeGeo(page);
  await startOnChatA(page);
  const ref = await probe(page).getAttribute('data-aoi-ref');
  await page.getByRole('button', { name: 'Run screening' }).click();
  await expect(probe(page)).toHaveAttribute('data-aoi-summary', /total_aoi_acres/);
  const summary = await probe(page).getAttribute('data-aoi-summary');
  await page.getByRole('tab', { name: 'Map', exact: true }).click();
  await pasteAoi(page, SQUARE_2);
  await expect(probe(page)).not.toHaveAttribute('data-aoi-ref', ref ?? '');
  await expect(probe(page)).toHaveAttribute('data-aoi-summary', '');
  await undoButton(page).click();
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', ref ?? '');
  await expect(probe(page)).toHaveAttribute('data-aoi-summary', summary ?? '');
  await expect(undoButton(page)).toBeDisabled();
});

test('Clear and the chip Detach can be undone to the same AOI', async ({ page }) => {
  await startOnChatA(page);
  const ref = await probe(page).getAttribute('data-aoi-ref');
  await page.getByRole('button', { name: 'Clear', exact: true }).click();
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', '');
  await undoButton(page).click();
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', ref ?? '');
  await page.getByRole('button', { name: /Detach map AOI/ }).click();
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', '');
  await undoButton(page).click();
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', ref ?? '');
  await expect(page.getByRole('button', { name: 'Clear', exact: true })).toBeEnabled();
});

test('Undo is disabled when there is nothing to restore', async ({ page }) => {
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  await expect(undoButton(page)).toBeDisabled();
  await pasteAoi(page);
  await expect(probe(page)).toHaveAttribute('data-aoi-ref', /^aoi-/);
  await expect(undoButton(page)).toBeDisabled();
});

test('the chip Detach clears the drawn corridor', async ({ page }) => {
  await page.goto('/aoi-state-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
  await drawCorridor(page);
  await expect(probe(page)).toHaveAttribute('data-corridor-ref', /.+/);
  await page.getByRole('button', { name: /Detach corridor/ }).click();
  await expect(probe(page)).toHaveAttribute('data-corridor-ref', '');
  await expect(page.getByText(/Primary ready/)).toHaveCount(0);
  await expect(page.getByTestId('active-geometry-chip')).toHaveCount(0);
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
