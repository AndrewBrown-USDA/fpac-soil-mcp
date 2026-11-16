import { expect, test } from '@playwright/test';
import { CDL_LEGEND } from '../../client/src/components/map/cdlLegend';

test('official CDL records preserve representative and edge values', () => {
  expect(CDL_LEGEND).toHaveLength(133);
  for (const record of [
    [1, 'Corn', '#FFD400'], [12, 'Sweet Corn', '#E0A60F'],
    [13, 'Pop or Orn Corn', '#E0A60F'], [81, 'Clouds/No Data', '#F7F7F7'],
    [111, 'Open Water', '#4D70A3'], [254, 'Dbl Crop Barley/Soybeans', '#267300'],
  ]) expect(CDL_LEGEND).toContainEqual(record);
  expect(new Set(CDL_LEGEND.map(([code]) => code)).size).toBe(CDL_LEGEND.length);
});

test.beforeEach(async ({ page }) => {
  await page.route('https://**/*', (route) => route.abort());
  await page.goto('/map-legend-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
});

test('map legend uses active server values unchanged and switches with results', async ({ page }) => {
  const summary = page.getByText('Map legend', { exact: true });
  await expect(summary).toBeVisible();
  await summary.click();
  const initialLegend = page.locator('details').filter({ has: summary });
  await expect(initialLegend.getByText('Prime farmland', { exact: true })).toBeVisible();
  await expect(initialLegend.getByText('Farmland of statewide importance', { exact: true })).toBeVisible();
  await expect(initialLegend.getByText('Map layers', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Show tool fixture' }).click();
  const legend = page.locator('details').filter({ has: summary });
  const farmland = legend.getByLabel('Server farmland, code FC; Code FC, solid symbol');
  await expect(legend.getByLabel('Server custom, code Z9; Code Z9, cross hatch symbol')).toBeVisible();
  await expect(farmland).toBeVisible();
  const serverClasses = await legend.locator('li[aria-label]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('aria-label')));
  expect(serverClasses[0]).toContain('Server farmland');
  expect(serverClasses[1]).toContain('Server custom');
  await expect(legend.getByText('Test source', { exact: false })).toBeVisible();
  await expect(legend.getByText('Server warning')).toBeVisible();
  await expect(legend.locator('li[aria-label^="Server custom"] span').first()).toHaveCSS('background-color', 'rgb(18, 52, 86)');
  const layersSummary = page.locator('summary').filter({ hasText: /^Layers/ });
  await layersSummary.click();
  const cdl = page.locator('#overlay-toggle-cdl');
  await expect(cdl).toBeVisible();
  await cdl.focus();
  await page.keyboard.press('Space');
  await expect(cdl).toBeChecked();
  await cdl.check();
  await expect(cdl).toBeChecked();
  const layers = page.locator('details').filter({ has: layersSummary });
  await expect(layers.getByText('CDL code and color key')).toHaveCount(0);
  await layersSummary.click();
  await expect(legend.getByText('CDL code and color key')).toBeVisible();
  await expect(legend.getByText('Server farmland', { exact: true })).toBeVisible();
  await expect(legend.getByText('CDL code and color key')).toBeVisible();
  await page.getByRole('button', { name: 'Show CDL fixture' }).click();
  await expect(legend.getByText('Server custom')).toHaveCount(0);
  await legend.getByText('CDL code and color key').click();
  await expect(legend.getByText('1 — Corn (#FFD400)')).toBeVisible();
  await page.getByRole('button', { name: 'Clear fixture' }).click();
  await expect(summary).toBeVisible();
  await expect(legend.getByText('Prime farmland', { exact: true })).toBeVisible();
});

test('core farmland legend remains through AOI creation and clearing', async ({ page }) => {
  const legend = page.locator('details').filter({ has: page.getByText('Map legend', { exact: true }) });
  await page.getByText('Map legend', { exact: true }).click();
  await expect(legend.getByText('Prime farmland', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Paste' }).click();
  await page.getByLabel('GeoJSON Polygon or MultiPolygon').fill('{"type":"Polygon","coordinates":[[[-93,42],[-92.99,42],[-92.99,42.01],[-93,42.01],[-93,42]]]}');
  await page.getByRole('button', { name: 'Use this AOI' }).click();
  await expect(legend.getByText('Prime farmland', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Clear', exact: true }).click();
  await expect(legend.getByText('Prime farmland', { exact: true })).toBeVisible();
});

test('farmland hatch swatches match server pattern direction and AOI outline stays distinguishable', async ({ page }) => {
  await page.getByRole('button', { name: 'Show overlap fixture' }).click();
  const legend = page.locator('details').filter({ has: page.getByText('Map legend', { exact: true }) });
  const conditional = legend.locator('li').filter({ hasText: 'Prime farmland if conditions are met' }).locator('span').first();
  const statewide = legend.locator('li').filter({ hasText: 'Farmland of statewide importance' }).locator('span').first();
  await expect(conditional).toHaveCSS('background-image', /repeating-linear-gradient\(135deg/);
  await expect(statewide).toHaveCSS('background-image', /repeating-linear-gradient\(135deg/);
  const aoi = page.locator('.maplibregl-canvas');
  await expect(aoi).toBeVisible();
  await page.getByRole('button', { name: 'Paste' }).click();
  await page.getByLabel('GeoJSON Polygon or MultiPolygon').fill('{"type":"Polygon","coordinates":[[[-93,42],[-92.99,42],[-92.99,42.01],[-93,42.01],[-93,42]]]}');
  await page.getByRole('button', { name: 'Use this AOI' }).click();
  await page.waitForTimeout(100);
  const outlineVisible = await aoi.screenshot();
  await page.getByRole('button', { name: 'AOI outline' }).click();
  await page.waitForTimeout(100);
  const outlineHidden = await aoi.screenshot();
  expect(outlineHidden.equals(outlineVisible)).toBe(false);
  await expect(page.getByRole('button', { name: 'AOI outline' })).toBeEnabled();
});

test('CDL overlay key is keyboard accessible on a narrow map', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 700 });
  const mapLegend = page.getByText('Map legend', { exact: true });
  await page.getByRole('button', { name: 'Show CDL fixture' }).click();
  await expect(mapLegend).toBeVisible();
  await mapLegend.focus();
  await page.keyboard.press('Enter');
  const key = page.getByText('CDL code and color key');
  await key.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('81 — Clouds/No Data (#F7F7F7)')).toBeVisible();
  await expect(page.getByText('not screening evidence', { exact: false })).toBeVisible();
});

test('screening and tool result legends follow the active result', async ({ page }) => {
  await page.route('**/api/geo/screen', (route) => route.fulfill({ json: {
    aoi_ref: 'fixture', chat_summary: {}, chat_summary_text: '',
    display: { regulatory_notice: 'Preliminary', analysis: { map_units: [{
      musym: 'X1', muname: 'A very long soil map unit name that must remain fully readable in the results table',
      farmlndcl: 'Prime farmland', acres: 3,
    }] }, map: { layers: [
      { id: 'screen', title: 'Screening layer', kind: 'polygon', delivery: 'omitted', authority: 'machine_estimate', source: 'Screen source', legend: [{ value: 'screen', label: 'Screen class', code: 'SC', color: '#ABCDEF', pattern: 'solid' }] },
      { id: 'farmland_classes', title: 'Farmland classes', kind: 'polygon', delivery: 'omitted', authority: 'machine_estimate', source: 'Farmland source', legend: [{ value: 'farmland', label: 'Prime farmland', code: 'PF', color: '#123456', pattern: 'solid' }] },
    ] } },
  } }));
  await page.getByRole('button', { name: 'Paste' }).click();
  await page.getByLabel('GeoJSON Polygon or MultiPolygon').fill('{"type":"Polygon","coordinates":[[[-93,42],[-92.99,42],[-92.99,42.01],[-93,42.01],[-93,42]]]}');
  await page.getByRole('button', { name: 'Use this AOI' }).click();
  await page.getByRole('button', { name: 'Run screening' }).click();
  await expect(page.getByRole('tab', { name: 'Results' })).toHaveAttribute('aria-selected', 'true');
  const results = page.locator('#map-panel-panel-results');
  await expect(results.getByText('Farmland classes (AOI n/a acres)')).toBeVisible();
  await expect(results.getByText('A very long soil map unit name that must remain fully readable in the results table')).toBeVisible();
  await expect(results.locator('.overflow-x-auto table')).toHaveCSS('min-width', '640px');
  await expect(page.locator('#map-panel-panel-results').getByText('Map layers', { exact: true })).toHaveCount(0);
  await page.getByRole('tab', { name: 'Map', exact: true }).click();
  await page.getByText('Map legend', { exact: true }).click();
  const legend = page.locator('details').filter({ has: page.getByText('Map legend', { exact: true }) });
  await expect(legend.getByLabel('Screen class, code SC; Code SC, solid symbol')).toBeVisible();
  await page.getByRole('button', { name: 'Show tool fixture' }).click();
  await expect(legend.getByLabel('Screen class, code SC; Code SC, solid symbol')).toHaveCount(0);
  await expect(legend.getByLabel('Server custom, code Z9; Code Z9, cross hatch symbol')).toBeVisible();
});
