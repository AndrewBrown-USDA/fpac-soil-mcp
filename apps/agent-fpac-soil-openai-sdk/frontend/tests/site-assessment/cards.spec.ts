import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/site-assessment-fixture.html');
});

test('selecting a resource band emits its exact answer, evidence, comment, and provenance', async ({ page }) => {
  await page.getByTestId('site-assessment-evidence').fill('Observed field evidence');
  await page.getByTestId('site-assessment-comment').fill('Verified during review');
  await page.getByTestId('site-assessment-provenance').selectOption('tool');
  await page.getByTestId('site-assessment-band-range_20_90_1').click();

  await expect(page.getByTestId('emitted-record')).toHaveText(JSON.stringify({
    type: 'site_assessment_answer',
    criterion_number: 1,
    answer_state: 'answered',
    answer: 'range_20_90_1',
    selected_band: {
      id: 'range_20_90_1',
      label: '20% to 25% representative interval',
      min: 20,
      max: 25,
      points: 1,
    },
    points: 1,
    evidence: 'Observed field evidence',
    comment: 'Verified during review',
    provenance: 'tool',
  }));
});

test('unknown and skipped answers are explicit without invented score bands', async ({ page }) => {
  await page.getByRole('button', { name: 'Unknown / unavailable' }).click();
  await expect(page.getByTestId('emitted-record')).toContainText('"answer_state":"unknown"');
  await expect(page.getByTestId('emitted-record')).toContainText('"points":null');

  await page.getByRole('button', { name: 'Skip this criterion' }).click();
  await expect(page.getByTestId('emitted-record')).toContainText('"answer_state":"skipped"');
  await expect(page.getByTestId('emitted-record')).toContainText('"selected_band":null');
});

test('review summary shows assumptions and Confirm/Edit emit their distinct actions', async ({ page }) => {
  await expect(page.getByTestId('site-assessment-assumptions')).toContainText('assumed (no evidence)');
  await page.getByRole('button', { name: 'Edit' }).click();
  await expect(page.getByTestId('editing')).toBeVisible();

  await page.getByRole('button', { name: 'Confirm' }).click();
  await expect(page.getByTestId('emitted-record')).toHaveText(JSON.stringify({
    type: 'site_assessment_confirmed_summary',
    confirmed: true,
    answers: [{
      type: 'site_assessment_answer',
      criterion_number: 1,
      answer_state: 'answered',
      answer: 'range_20_90_1',
      selected_band: {
        id: 'range_20_90_1',
        label: '20% to 25% representative interval',
        min: 20,
        max: 25,
        points: 1,
      },
      points: 1,
      evidence: 'Sample evidence',
      comment: 'Sample comment',
      provenance: 'user',
    }],
    assumptions: ['Criterion 2: assumed (no evidence)'],
  }));
});

test('a replaced or detached AOI prevents a CDL result from entering map context', async ({ page }) => {
  await page.getByRole('button', { name: 'Attach AOI' }).click();
  await page.getByRole('button', { name: 'Show CDL on map' }).click();
  await expect(page.getByTestId('map-result')).toContainText('"origin":"tool"');

  await page.getByRole('button', { name: 'Replace AOI' }).click();
  await page.getByRole('button', { name: 'Clear map result' }).click();
  await page.getByRole('button', { name: 'Show CDL on map' }).click();
  await expect(page.getByTestId('map-result')).toHaveText('empty');
  await expect(page.getByText('This CDL result is stale because its AOI is no longer active.')).toBeVisible();

  await page.getByRole('button', { name: 'Detach AOI' }).click();
  await page.getByRole('button', { name: 'Show CDL on map' }).click();
  await expect(page.getByTestId('map-result')).toHaveText('empty');
});
