import { expect, test } from '@playwright/test';

test('map-capable tool details start collapsed while map action stays in the top bar', async ({ page }) => {
  await page.goto('/tool-card-fixture.html');
  const action = page.getByText('Show on map · aoi-12345678');
  await expect(action).toBeVisible();
  await expect(action).toHaveAttribute('aria-label', 'analyze_farmland_by_polygon: aoi-12345678');
  await expect(action).toContainText('aoi-12345678');
  await expect(page.getByText('Parameters')).toBeHidden();
  await page.getByRole('button', { name: 'analyze_farmland_by_polygon Completed' }).click();
  await expect(page.getByText('Parameters')).toBeVisible();
});
