import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/site-assessment-fixture.html');
});

test('choosing a band only selects it; Record answer emits after the details are filled', async ({ page }) => {
  await expect(page.getByTestId('site-assessment-record')).toBeDisabled();
  await page.getByTestId('site-assessment-band-range_20_90_1').click();
  await expect(page.getByTestId('site-assessment-band-range_20_90_1')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByTestId('emitted-record')).not.toContainText('site_assessment_answer');
  await expect(page.getByTestId('site-assessment-requirements')).toContainText('verification against the cited source');
  await expect(page.getByTestId('site-assessment-missing')).toContainText('submitted as unknown');

  await page.getByTestId('site-assessment-verified').check();
  await expect(page.getByTestId('site-assessment-missing')).toHaveCount(0);
  await page.getByTestId('site-assessment-record').click();
  await expect(page.getByTestId('emitted-record')).toContainText('"is_verified":true');
});

test('selecting a resource band emits answer, evidence, verification, source, justification, and provenance', async ({ page }) => {
  await page.getByTestId('site-assessment-evidence').fill('Observed field evidence');
  await page.getByTestId('site-assessment-comment').fill('Verified during review');
  await page.getByTestId('site-assessment-provenance').selectOption('tool');
  await page.getByTestId('site-assessment-verified').check();
  await page.getByTestId('site-assessment-source-provenance').fill('NRCS field record\nCounty land-use map');
  await page.getByTestId('site-assessment-justification').fill('Both sources support the selected interval.');
  await page.getByTestId('site-assessment-band-range_20_90_1').click();
  await page.getByTestId('site-assessment-record').click();

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
    is_verified: true,
    source_provenance: ['NRCS field record', 'County land-use map'],
    justification: 'Both sources support the selected interval.',
  }));
});

test('unknown and skipped answers are explicit without invented score bands', async ({ page }) => {
  await page.getByRole('button', { name: 'Unknown / unavailable' }).click();
  await expect(page.getByTestId('emitted-record')).toContainText('"answer_state":"unknown"');
  await expect(page.getByTestId('emitted-record')).toContainText('"points":null');
  await expect(page.getByTestId('emitted-record')).toContainText('"is_verified":false');

  await page.getByRole('button', { name: 'Skip this criterion' }).click();
  await expect(page.getByTestId('emitted-record')).toContainText('"answer_state":"skipped"');
  await expect(page.getByTestId('emitted-record')).toContainText('"selected_band":null');
});

test('review summary flags answers that will be submitted as unknown', async ({ page }) => {
  const summary = page.getByTestId('site-assessment-summary');
  await expect(summary.getByTestId('site-assessment-note')).toHaveText(
    'Submitted as unknown: not verified against the cited source.',
  );
  await expect(summary.getByTestId('site-assessment-notes-banner')).toContainText('1 answer(s) will be submitted as unknown');
  await expect(summary).toContainText('Sample justification');
});

test('review summary shows assumptions and Confirm/Edit emit their distinct actions', async ({ page }) => {
  await expect(page.getByTestId('site-assessment-assumptions')).toContainText('assumed (no evidence)');
  await page.getByRole('button', { name: 'Edit' }).click();
  await expect(page.getByTestId('editing')).toBeVisible();

  await page.getByRole('button', { name: 'Confirm' }).click();
  const emitted = JSON.parse((await page.getByTestId('emitted-record').textContent()) ?? '');
  expect(emitted.calculation_notes).toEqual({
    '3': 'Submitted as unknown: not verified against the cited source.',
  });
  expect(emitted.answers[1]).toMatchObject({ criterion_number: 3, is_verified: false });
  await expect(page.getByTestId('emitted-record')).toContainText(JSON.stringify({
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
      is_verified: true,
      source_provenance: ['Sample source'],
      justification: 'Sample justification',
    }],
  }).slice(0, -3));
});

test('a replaced or detached AOI prevents a CDL result from entering map context', async ({ page }) => {
  await page.getByRole('button', { name: 'Attach AOI' }).click();
  const showCdl = page.getByRole('button', { name: /analyze_cdl_context:/ });
  await showCdl.click();
  await expect(page.getByTestId('map-result')).toContainText('"origin":"tool"');

  await page.getByRole('button', { name: 'Replace AOI' }).click();
  await page.getByRole('button', { name: 'Clear map result' }).click();
  await showCdl.click();
  await expect(page.getByTestId('map-result')).toHaveText('empty');
  await expect(page.getByText('This CDL result is stale because its AOI is no longer active.')).toBeVisible();

  await page.getByRole('button', { name: 'Detach AOI' }).click();
  await showCdl.click();
  await expect(page.getByTestId('map-result')).toHaveText('empty');
});
