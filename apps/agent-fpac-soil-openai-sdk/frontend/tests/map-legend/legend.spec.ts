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
  await expect(page.getByText('Map legend', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Show tool fixture' }).click();
  const summary = page.getByText('Map legend', { exact: true });
  await summary.focus();
  await page.keyboard.press('Enter');
  const legend = page.locator('details').filter({ has: summary });
  await expect(legend.getByLabel('Server custom, code Z9; Code Z9, cross hatch symbol')).toBeVisible();
  await expect(legend.getByText('Test source', { exact: false })).toBeVisible();
  await expect(legend.getByText('Server warning')).toBeVisible();
  await expect(legend.locator('li[aria-label^="Server custom"] span').first()).toHaveCSS('background-color', 'rgb(18, 52, 86)');
  await page.getByRole('button', { name: 'Show CDL fixture' }).click();
  await expect(legend.getByText('Server custom')).toHaveCount(0);
  await legend.getByText('CDL code and color key').click();
  await expect(legend.getByText('1 — Corn (#FFD400)')).toBeVisible();
  await page.getByRole('button', { name: 'Clear fixture' }).click();
  await expect(summary).toHaveCount(0);
});

test('CDL overlay key is keyboard accessible on a narrow map', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 700 });
  await page.getByText('Layers', { exact: true }).click();
  const cdl = page.getByRole('checkbox', { name: /Cropland Data Layer/i });
  await cdl.check();
  const key = page.getByText('CDL code and color key');
  await key.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('81 — Clouds/No Data (#F7F7F7)')).toBeVisible();
  await expect(page.getByText('not screening evidence', { exact: false })).toBeVisible();
});

test('screening and tool result legends follow the active result', async ({ page }) => {
  await page.route('**/api/geo/screen', (route) => route.fulfill({ json: {
    aoi_ref: 'fixture', chat_summary: {}, chat_summary_text: '',
    display: { regulatory_notice: 'Preliminary', analysis: {}, map: { layers: [{
      id: 'screen', title: 'Screening layer', kind: 'polygon', delivery: 'omitted',
      authority: 'machine_estimate', source: 'Screen source', legend: [
        { value: 'screen', label: 'Screen class', code: 'SC', color: '#ABCDEF', pattern: 'solid' },
      ],
    }] } },
  } }));
  await page.getByRole('button', { name: 'Paste GeoJSON' }).click();
  await page.getByLabel('GeoJSON Polygon or MultiPolygon').fill('{"type":"Polygon","coordinates":[[[-93,42],[-92.99,42],[-92.99,42.01],[-93,42.01],[-93,42]]]}');
  await page.getByRole('button', { name: 'Use this AOI' }).click();
  await page.getByRole('button', { name: 'Run screening' }).click();
  await expect(page.getByRole('tab', { name: 'Results' })).toHaveAttribute('aria-selected', 'true');
  await page.getByRole('tab', { name: 'Map', exact: true }).click();
  await page.getByText('Map legend', { exact: true }).click();
  const legend = page.locator('details').filter({ has: page.getByText('Map legend', { exact: true }) });
  await expect(legend.getByLabel('Screen class, code SC; Code SC, solid symbol')).toBeVisible();
  await page.getByRole('button', { name: 'Show tool fixture' }).click();
  await expect(legend.getByLabel('Screen class, code SC; Code SC, solid symbol')).toHaveCount(0);
  await expect(legend.getByLabel('Server custom, code Z9; Code Z9, cross hatch symbol')).toBeVisible();
});
