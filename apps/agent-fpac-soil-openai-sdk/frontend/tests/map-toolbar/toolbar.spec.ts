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
  await expect(page.getByRole('button', { name: 'Clear', exact: true })).toBeDisabled();
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
});

test('drawing and measurement cursors restore and measurement defaults to selectable miles', async ({ page }) => {
  const canvas = page.locator('.maplibregl-canvas');
  const polygon = page.getByRole('button', { name: 'Polygon' });
  const rectangle = page.getByRole('button', { name: 'Rectangle' });
  const measure = page.getByRole('button', { name: 'Measure line' });
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
  await page.getByRole('button', { name: 'Cancel measure' }).click();
  await expect(canvas).not.toHaveCSS('cursor', 'crosshair');
  await measure.click();
  await polygon.click();
  await expect(canvas).toHaveCSS('cursor', 'crosshair');
  await expect(page.getByRole('button', { name: 'Measure line' })).toHaveAttribute('aria-pressed', 'false');
  await polygon.click();
  await expect(canvas).not.toHaveCSS('cursor', 'crosshair');
});

test('measurement shows a concise status and live preview without committing pointer movement', async ({ page }) => {
  const canvas = page.locator('.maplibregl-canvas');
  await page.getByRole('button', { name: 'Measure line' }).click();
  await page.getByRole('combobox', { name: 'Distance unit' }).selectOption('meters');
  await expect(page.getByText('Measuring', { exact: true })).toBeVisible();
  const box = await canvas.boundingBox();
  if (!box) throw new Error('Map canvas is not visible');
  await page.mouse.click(box.x + box.width * 0.3, box.y + box.height * 0.4);
  await page.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.6);
  const measurement = page.getByRole('group', { name: 'Line measurement' });
  await expect(measurement).toHaveAttribute('data-preview-active', 'true');
  const distance = page.getByText(/^\d+\.\d{2} meters$/);
  await expect(distance).toHaveText('0.00 meters');
  await page.mouse.click(box.x + box.width * 0.7, box.y + box.height * 0.6);
  await expect(distance).toBeVisible();
  const committedDistance = await distance.textContent();
  if (!committedDistance) throw new Error('Committed measurement distance is missing');
  await page.mouse.move(box.x + box.width * 0.8, box.y + box.height * 0.5);
  await expect(distance).toHaveText(committedDistance);
  await expect(page.getByText('Measuring', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Cancel measure' })).toBeVisible();
  await page.getByRole('button', { name: 'Cancel measure' }).click();
  await expect(page.getByText('Measuring', { exact: true })).toHaveCount(0);
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
