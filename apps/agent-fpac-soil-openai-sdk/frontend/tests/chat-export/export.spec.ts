import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';

test.beforeEach(async ({ page }) => page.goto('/chat-export-fixture.html'));

test('canceling the sensitivity warning does not download', async ({ page }) => {
  await page.getByText('Export chat').click();
  await page.getByRole('button', { name: 'Markdown' }).click();
  await expect(page.getByRole('dialog')).toContainText('sensitive coordinates');
  const downloadPromise = page.waitForEvent('download', { timeout: 500 }).catch(() => null);
  await page.getByRole('button', { name: 'Cancel' }).click();
  expect(await downloadPromise).toBeNull();
});

for (const format of ['Markdown', 'JSON'] as const) {
  test(`confirmed ${format} export contains only visible conversation data`, async ({ page }) => {
    await page.getByText('Export chat').click();
    await page.getByRole('button', { name: format }).click();
    await expect(page.getByRole('dialog')).toContainText('raw tool data and sensitive coordinates');
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download export' }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe(format === 'JSON' ? 'conversation.json' : 'conversation.md');
    const content = await readFile(await download.path()!, 'utf8');
    expect(content).toContain('Screen this location.');
    expect(content).toContain('analyze_farmland_by_polygon');
    expect(content).toContain('-98');
    expect(content).not.toContain('private reasoning');
  });
}
