import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => page.goto('/map-tabs-fixture.html'));

test('starts on Map and shows an empty Results state', async ({ page }) => {
  await expect(page.getByRole('tab', { name: 'Map' })).toHaveAttribute('aria-selected', 'true');
  await page.getByRole('tab', { name: 'Results' }).click();
  await expect(page.locator('#panel-results')).toContainText('Run a screening');
  await page.getByRole('tab', { name: 'Map' }).click();
  await expect(page.locator('#panel-map')).toBeVisible();
});

test('selects Results after screening and retains details when viewing a tool result', async ({ page }) => {
  await page.getByRole('button', { name: 'Complete screening' }).click();
  await expect(page.getByRole('tab', { name: 'Results' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#panel-results')).toContainText('Screening details');
  await page.getByRole('button', { name: 'Show tool result' }).click();
  await expect(page.locator('#panel-results')).toContainText('Tool result');
  await page.getByRole('button', { name: 'Back to screening results' }).click();
  await expect(page.locator('#panel-results')).toContainText('Screening details');
});
