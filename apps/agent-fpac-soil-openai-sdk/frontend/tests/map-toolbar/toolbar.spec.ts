import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('https://**/*', (route) => route.abort());
  await page.goto('/map-toolbar-fixture.html');
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeEnabled();
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
  await corridor.click();
  await expect(corridor).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: 'Draw primary line' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Polygon' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Measure distance' })).toBeVisible();
  await page.getByRole('button', { name: 'Area', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Polygon' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Draw primary line' })).toHaveCount(0);
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
