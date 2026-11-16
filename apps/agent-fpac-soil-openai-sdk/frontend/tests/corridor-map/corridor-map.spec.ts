import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('https://**/*', (route) => route.abort());
  await page.goto('/corridor-map-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
});

test('submits drawn corridor directly and displays returned summary, notice and server legend', async ({ page }) => {
  await page.route('**/api/geo/corridor', async (route) => {
    const request = route.request().postDataJSON();
    expect(request.centerline.type).toBe('LineString');
    await route.fulfill({ json: {
      display: {
        corridor_ref: request.corridor_ref,
        status: 'preliminary_screening',
        buffer_distance: request.buffer_distance,
        buffer_units: request.buffer_units,
        impact_breakdown: { direct_acres: 12.3, indirect_acres: 2, total_project_acres: 14.3 },
        composite_relative_rating: null,
        county_segments: [{ county_name: 'Example', state_name: 'XY', total_segment_acres: 14.3 }],
        alternatives: [],
      },
      map: { layers: [{ id: 'corridor', title: 'Corridor layer', kind: 'polygon', delivery: 'omitted', authority: 'machine_estimate', source: 'Server source', legend: [{ value: 'x', label: 'Server corridor class', color: '#123456' }] }] },
      regulatory_notice: 'Preliminary screening only. Not an official determination.',
      status: 'preliminary_screening',
    } });
  });
  await page.getByRole('button', { name: 'Draw primary line' }).click();
  const map = page.locator('.maplibregl-map');
  await map.click({ position: { x: 120, y: 130 } });
  await map.dblclick({ position: { x: 200, y: 190 } });
  await expect(page.getByText('Primary: ready')).toBeVisible();
  await page.getByLabel('Required buffer distance').fill('50');
  await page.getByRole('button', { name: 'Screen corridor' }).click();
  await expect(page.getByRole('tab', { name: 'Results' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('region', { name: 'Corridor screening summary' })).toContainText('12.3 ac');
  await expect(page.getByText('Preliminary screening only. Not an official determination.')).toBeVisible();
  await page.getByRole('tab', { name: 'Map', exact: true }).click();
  await page.getByText('Map legend', { exact: true }).click();
  await expect(page.getByText('Server corridor class')).toBeVisible();
});
