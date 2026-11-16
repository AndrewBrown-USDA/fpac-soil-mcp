import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('https://**/*', (route) => route.abort());
  await page.goto('/map-toolbar-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
});

async function completeScreening(page: import('@playwright/test').Page) {
  await page.route('**/api/geo/screen', (route) => route.fulfill({ json: {
    aoi_ref: 'aoi-12345678',
    chat_summary: {},
    chat_summary_text: '',
    display: {
      analysis: { map_units: [] },
      map: {
        bounds: [-93, 42, -92.99, 42.01],
        layers: [],
      },
      regulatory_notice: 'Preliminary screening only.',
    },
  } }));
  await page.getByText('Import or export GeoJSON', { exact: true }).click();
  await page.getByRole('button', { name: 'Paste GeoJSON' }).click();
  await page.getByLabel('GeoJSON Polygon or MultiPolygon').fill('{"type":"Polygon","coordinates":[[[-93,42],[-92.99,42],[-92.99,42.01],[-93,42.01],[-93,42]]]}');
  await page.getByRole('button', { name: 'Use this AOI' }).click();
  await page.getByRole('button', { name: 'Run screening' }).click();
  await expect(page.getByRole('tab', { name: 'Results' })).toHaveAttribute('aria-selected', 'true');
  await page.waitForTimeout(400);
  await page.getByRole('tab', { name: 'Map', exact: true }).click();
  await expect(page.getByRole('tab', { name: 'Map', exact: true })).toHaveAttribute('aria-selected', 'true');
  await page.waitForTimeout(1000);
}

test('toggling result boundaries does not move or zoom the map', async ({ page }) => {
  await completeScreening(page);
  await page.evaluate(async () => {
    const camera = (window as typeof window & { __mapCamera?: { jumpTo: (center: [number, number], zoom: number) => void } }).__mapCamera;
    if (!camera) throw new Error('Map camera probe is unavailable');
    camera.jumpTo([-90, 45], 7);
  });
  await page.waitForTimeout(100);
  const readCamera = () => page.evaluate(() => {
    const camera = (window as typeof window & { __mapCamera?: { read: () => { center: [number, number]; zoom: number } } }).__mapCamera;
    if (!camera) throw new Error('Map camera probe is unavailable');
    return camera.read();
  });
  const before = await readCamera();
  await page.getByRole('button', { name: 'Result boundaries' }).click();
  await page.waitForTimeout(100);
  const after = await readCamera();
  expect(after.center[0]).toBeCloseTo(before.center[0], 6);
  expect(after.center[1]).toBeCloseTo(before.center[1], 6);
  expect(after.zoom).toBeCloseTo(before.zoom, 6);
});

test('returning from Results restores the AOI center', async ({ page }) => {
  await completeScreening(page);
  const camera = await page.evaluate(() => {
    const probe = (window as typeof window & { __mapCamera?: { read: () => { center: [number, number]; zoom: number } } }).__mapCamera;
    if (!probe) throw new Error('Map camera probe is unavailable');
    return probe.read();
  });
  expect(camera.center[0]).toBeCloseTo(-92.995, 0);
  expect(camera.center[1]).toBeCloseTo(42.005, 0);
});

test('CDL toggles and a screening retry keep the Firefox map interactive', async ({ page }, testInfo) => {
  const browserErrors: string[] = [];
  const network: { url: string; status: number }[] = [];
  page.on('pageerror', (error) => browserErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(message.text());
  });
  page.on('response', (response) => {
    if (response.url().includes('/api/geo/screen') || response.url().includes('pdi.scinet.usda.gov')) {
      network.push({ url: response.url().split('?')[0], status: response.status() });
    }
  });
  await page.route('https://pdi.scinet.usda.gov/**', (route) => route.fulfill({
    status: 200,
    contentType: 'image/png',
    body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/2ioAAAAASUVORK5CYII=', 'base64'),
  }));
  let screeningRequests = 0;
  await page.route('**/api/geo/screen', async (route) => {
    screeningRequests += 1;
    if (screeningRequests === 1) return route.fulfill({ status: 502, json: { detail: 'temporary test outage' } });
    await new Promise((resolve) => setTimeout(resolve, 150));
    return route.fulfill({ json: {
      aoi_ref: 'aoi-12345678',
      chat_summary: {},
      chat_summary_text: '',
      display: { analysis: { map_units: [] }, map: { layers: [] }, regulatory_notice: 'Preliminary screening only.' },
    } });
  });
  await page.getByText('Import or export GeoJSON', { exact: true }).click();
  await page.getByRole('button', { name: 'Paste GeoJSON' }).click();
  await page.getByLabel('GeoJSON Polygon or MultiPolygon').fill('{"type":"Polygon","coordinates":[[[-93,42],[-92.99,42],[-92.99,42.01],[-93,42.01],[-93,42]]]}');
  await page.getByRole('button', { name: 'Use this AOI' }).click();
  await page.evaluate(() => {
    const camera = (window as typeof window & { __mapCamera?: { jumpTo: (center: [number, number], zoom: number) => void } }).__mapCamera;
    if (!camera) throw new Error('Map camera probe is unavailable');
    camera.jumpTo([-93, 42], 6);
  });
  await page.waitForTimeout(150);
  const layers = page.locator('details').filter({ has: page.getByText(/^Layers/) });
  await layers.locator('summary').click();
  const cdl = page.locator('#overlay-toggle-cdl');
  for (let attempt = 0; attempt < 12; attempt += 1) {
    await cdl.check();
    await expect(cdl).toBeChecked();
    await cdl.uncheck();
    await expect(cdl).not.toBeChecked();
    await page.getByRole('button', { name: 'Reset map' }).click();
  }
  await page.getByRole('button', { name: 'Run screening' }).click();
  await expect(page.getByText(/Screening unavailable/)).toBeVisible();
  await page.getByRole('button', { name: 'Run screening' }).click();
  await expect(page.getByRole('tab', { name: 'Results' })).toHaveAttribute('aria-selected', 'true');
  await expect.poll(() => screeningRequests).toBe(2);
  await page.getByRole('tab', { name: 'Map', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reset map' })).toBeVisible();
  await expect.poll(() => network.filter(({ url }) => url.includes('pdi.scinet.usda.gov')).length).toBeGreaterThan(0);
  await testInfo.attach('firefox-stress-observations', {
    body: JSON.stringify({ screeningRequests, network, browserErrors }, null, 2),
    contentType: 'application/json',
  });
});

test('geometry transfer panel groups upload, paste, copy, and download workflows', async ({ page }) => {
  const transfer = page.getByText('Import or export GeoJSON');
  await transfer.click();
  const panel = page.getByRole('group', { name: 'AOI input methods' });
  await expect(panel.getByRole('button', { name: 'Upload file' })).toBeVisible();
  await expect(panel.getByRole('button', { name: 'Paste GeoJSON' })).toBeVisible();
  await expect(page.getByRole('group', { name: 'AOI GeoJSON export' }).getByRole('button', { name: 'Copy GeoJSON' })).toBeDisabled();
  await expect(page.getByRole('group', { name: 'AOI GeoJSON export' }).getByRole('button', { name: 'Download GeoJSON' })).toBeDisabled();
});

test('toolbar controls are compact, named, keyboard operable and labelled on hover and focus', async ({ page }) => {
  const polygon = page.getByRole('button', { name: 'Polygon' });
  await expect(polygon).toHaveText('');
  await expect(polygon).toHaveAttribute('aria-pressed', 'false');
  const clear = page.getByRole('button', { name: 'Clear', exact: true });
  await expect(clear).toBeDisabled();
  expect((await polygon.boundingBox())?.width).toBeLessThan(40);
  await polygon.hover();
  await expect(page.getByRole('tooltip')).toContainText('Polygon');
  await page.mouse.move(0, 0);
  await polygon.focus();
  await expect(page.getByRole('tooltip')).toContainText('Polygon');
  await expect(polygon).toBeFocused();
  await expect(polygon).toHaveClass(/focus-visible:ring-2/);
  await page.keyboard.press('Enter');
  await expect(polygon).toHaveAttribute('aria-pressed', 'true');
  await page.keyboard.press('Enter');
  await expect(polygon).toHaveAttribute('aria-pressed', 'false');
  const disabledClearTrigger = page.locator('span[aria-label="Clear"]');
  await disabledClearTrigger.hover();
  await expect(page.getByRole('tooltip')).toContainText('Clear');
  await disabledClearTrigger.focus();
  await expect(page.getByRole('tooltip')).toContainText('Clear');
});

test('Area and Corridor modes scope their drawing workflows while retaining measurement access', async ({ page }) => {
  const corridor = page.getByRole('button', { name: 'Corridor', exact: true });
  const primaryLine = page.getByRole('button', { name: 'Draw primary line' });
  await expect(primaryLine).toBeVisible();
  await expect(primaryLine).toBeDisabled();
  const measurementBox = await page.getByRole('button', { name: 'Measure distance' }).boundingBox();
  const corridorBox = await primaryLine.boundingBox();
  if (!measurementBox || !corridorBox) throw new Error('Toolbar buttons are not visible');
  expect(corridorBox.x).toBeGreaterThan(measurementBox.x);
  expect(Math.abs(corridorBox.y - measurementBox.y)).toBeLessThan(12);
  await corridor.click();
  await expect(corridor).toHaveAttribute('aria-pressed', 'true');
  await expect(primaryLine).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Polygon' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Measure distance' })).toBeVisible();
  await page.getByRole('button', { name: 'Area', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeVisible();
  await expect(primaryLine).toBeVisible();
  await expect(primaryLine).toBeDisabled();
  await page.getByRole('button', { name: 'Polygon' }).click();
  const map = page.locator('.maplibregl-map');
  await map.click({ position: { x: 100, y: 100 } });
  await map.click({ position: { x: 180, y: 100 } });
  await map.click({ position: { x: 180, y: 180 } });
  await map.dblclick({ position: { x: 100, y: 100 } });
  const canvas = page.locator('.maplibregl-canvas');
  await page.waitForTimeout(100);
  const visibleAoi = await canvas.screenshot();
  await page.getByRole('button', { name: 'AOI outline' }).click();
  await page.waitForTimeout(100);
  const hiddenAoi = await canvas.screenshot();
  expect(hiddenAoi.equals(visibleAoi)).toBe(false);
  await page.getByRole('button', { name: 'AOI outline' }).click();
  await page.getByLabel('Area label').fill('Test area');
  await page.getByRole('button', { name: 'Corridor', exact: true }).click();
  await page.getByLabel('Alternative label').fill('Test route');
  await page.getByRole('button', { name: 'Area', exact: true }).click();
  await expect(page.getByLabel('Area label')).toHaveValue('Test area');
  await page.getByRole('button', { name: 'Corridor', exact: true }).click();
  await expect(page.getByLabel('Alternative label')).toHaveValue('Test route');
});

test('drawing and measurement cursors restore and measurement defaults to selectable miles', async ({ page }) => {
  const canvas = page.locator('.maplibregl-canvas');
  const polygon = page.getByRole('button', { name: 'Polygon' });
  const rectangle = page.getByRole('button', { name: 'Rectangle' });
  const measure = page.getByRole('button', { name: 'Measure distance' });
  const units = page.getByRole('combobox', { name: 'Distance unit' });
  await expect(units).toHaveValue('miles');
  await units.selectOption('meters');
  await expect(units).toHaveValue('meters');
  await polygon.click();
  await expect(canvas).toHaveCSS('cursor', 'crosshair');
  await polygon.click();
  await expect(canvas).not.toHaveCSS('cursor', 'crosshair');
  await rectangle.click();
  await expect(canvas).toHaveCSS('cursor', 'crosshair');
  await page.getByRole('button', { name: 'Edit', exact: true }).click();
  await expect(canvas).not.toHaveCSS('cursor', 'crosshair');
  await measure.click();
  await expect(canvas).toHaveCSS('cursor', 'crosshair');
  await page.getByRole('button', { name: 'Stop measuring' }).click();
  await expect(canvas).not.toHaveCSS('cursor', 'crosshair');
  await measure.click();
  await polygon.click();
  await expect(canvas).toHaveCSS('cursor', 'crosshair');
  await expect(page.getByRole('button', { name: 'Measure distance' })).toHaveAttribute('aria-pressed', 'false');
  await polygon.click();
  await expect(canvas).not.toHaveCSS('cursor', 'crosshair');
});

test('double-click completes measurement and retains map tooltip until cleared', async ({ page }) => {
  const canvas = page.locator('.maplibregl-canvas');
  await page.getByRole('button', { name: 'Measure distance' }).click();
  await page.getByRole('combobox', { name: 'Distance unit' }).selectOption('meters');
  await expect(page.getByRole('button', { name: 'Stop measuring' })).toBeVisible();
  const box = await canvas.boundingBox();
  if (!box) throw new Error('Map canvas is not visible');
  await page.mouse.click(box.x + box.width * 0.3, box.y + box.height * 0.4);
  await page.mouse.dblclick(box.x + box.width * 0.7, box.y + box.height * 0.6);
  const distance = page.getByRole('tooltip', { name: 'Measured distance' });
  await expect(distance).toContainText(/meters$/);
  await expect(page.locator('.maplibregl-popup-content')).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
  await expect(page.locator('.maplibregl-popup-tip')).toBeHidden();
  await expect(page.getByText('Measuring', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Stop measuring' })).toHaveCount(0);
  await page.mouse.move(box.x + box.width * 0.8, box.y + box.height * 0.5);
  await expect(distance).toBeVisible();
  await page.getByRole('button', { name: 'Corridor', exact: true }).click();
  await expect(distance).toBeVisible();
  await page.getByRole('button', { name: 'Clear measurement' }).click();
  await expect(distance).toHaveCount(0);
});

test('finishing a rectangle restores the normal map cursor', async ({ page }) => {
  const canvas = page.locator('.maplibregl-canvas');
  await page.getByRole('button', { name: 'Rectangle' }).click();
  await expect(canvas).toHaveCSS('cursor', 'crosshair');
  await canvas.scrollIntoViewIfNeeded();
  const box = await canvas.boundingBox();
  if (!box) throw new Error('Map canvas is not visible');
  await page.mouse.click(box.x + box.width * 0.35, box.y + box.height * 0.35);
  await page.mouse.move(box.x + box.width * 0.65, box.y + box.height * 0.65, { steps: 5 });
  await page.mouse.click(box.x + box.width * 0.65, box.y + box.height * 0.65);
  await expect(page.getByRole('button', { name: 'Rectangle' })).toHaveAttribute('aria-pressed', 'false');
  await expect(canvas).not.toHaveCSS('cursor', 'crosshair');
});
