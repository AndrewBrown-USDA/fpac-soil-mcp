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
  await page.getByText('Corridor options', { exact: true }).click();
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

test('retains alternative labels and synchronizes feature removal and clear', async ({ page }) => {
  await page.getByText('Corridor options', { exact: true }).click();
  const map = page.locator('.maplibregl-map');
  await page.getByRole('button', { name: 'Draw primary line' }).click();
  await map.click({ position: { x: 120, y: 130 } });
  await map.dblclick({ position: { x: 200, y: 190 } });
  await expect(page.getByText('Primary: ready')).toBeVisible();
  await page.waitForTimeout(50);

  await page.getByLabel('Alternative label').fill('North route');
  await page.getByRole('button', { name: 'Draw alternative line' }).click();
  await map.click({ position: { x: 150, y: 100 } });
  await map.dblclick({ position: { x: 220, y: 160 } });
  await expect(page.getByRole('button', { name: 'Remove North route' })).toBeVisible();
  await page.getByRole('button', { name: 'Remove North route' }).click();
  await expect(page.getByText(/alternatives: 0/)).toBeVisible();

  await page.getByRole('button', { name: 'Draw staging area' }).click();
  await map.click({ position: { x: 280, y: 160 } });
  await map.click({ position: { x: 330, y: 160 } });
  await map.click({ position: { x: 330, y: 210 } });
  await map.dblclick({ position: { x: 280, y: 160 } });
  await expect(page.getByRole('button', { name: 'Remove staging area 1' })).toBeVisible();
  await page.getByRole('button', { name: 'Remove staging area 1' }).click();
  await expect(page.getByText(/staging areas: 0/)).toBeVisible();
  await page.getByRole('button', { name: 'Remove primary line' }).click();
  await expect(page.getByText('Primary: required; alternatives: 0; staging areas: 0')).toBeVisible();
  await page.getByRole('button', { name: 'Draw primary line' }).click();
  await map.click({ position: { x: 160, y: 110 } });
  await map.dblclick({ position: { x: 220, y: 170 } });
  await expect(page.getByText(/Primary: ready/)).toBeVisible();
  await page.getByRole('button', { name: 'Clear corridor' }).click();
  await expect(page.getByText('Primary: required; alternatives: 0; staging areas: 0')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Clear corridor' })).toBeDisabled();
});

test('corridor auto-attach replaces AOI and the shared chat chip detaches it', async ({ page }) => {
  // Attach an AOI through its public drawing workflow.
  const map = page.locator('.maplibregl-map');
  await page.getByRole('button', { name: 'Polygon' }).click();
  await map.click({ position: { x: 100, y: 100 } });
  await map.click({ position: { x: 180, y: 100 } });
  await map.click({ position: { x: 180, y: 180 } });
  await map.dblclick({ position: { x: 100, y: 100 } });
  await expect(page.getByTestId('active-geometry-chip')).toContainText('Map AOI');
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem('fpac-map-aoi:corridor-fixture'))).not.toBeNull();

  await page.getByText('Corridor options', { exact: true }).click();
  await page.getByLabel('Required buffer distance').fill('50');
  await page.getByRole('button', { name: 'Draw primary line' }).click();
  await map.click({ position: { x: 120, y: 130 } });
  await map.dblclick({ position: { x: 200, y: 190 } });
  const chip = page.getByTestId('active-geometry-chip');
  await expect(chip).toContainText('Corridor');
  await expect(chip).not.toContainText('Map AOI');
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem('fpac-map-aoi:corridor-fixture'))).toBeNull();
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem('fpac-map-corridor:corridor-fixture'))).not.toBeNull();
  await chip.getByRole('button', { name: /Detach corridor/ }).click();
  await expect(chip).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem('fpac-map-corridor:corridor-fixture'))).toBeNull();
});
