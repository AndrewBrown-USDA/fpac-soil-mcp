import assert from 'node:assert/strict';
import { test } from 'node:test';
import { summaryToAttach, type ScreeningResponse } from './useScreening';

const NOTICE = 'Preliminary screening only.';

function valid(notice: string | null = NOTICE): ScreeningResponse {
  return {
    aoi_ref: 'aoi-0123abcd',
    display: { analysis: {}, map: null, regulatory_notice: notice },
    chat_summary: { aoi_ref: 'aoi-0123abcd', total_aoi_acres: 1, regulatory_notice: notice },
    chat_summary_text: 'Map screening result (preliminary)',
  };
}

function failed(error = 'screening_failed'): ScreeningResponse {
  return {
    aoi_ref: 'aoi-0123abcd',
    display: { error, regulatory_notice: null },
    chat_summary: { aoi_ref: 'aoi-0123abcd', status: 'screening_failed' },
    chat_summary_text: 'Map screening result (preliminary)',
  };
}

test('a valid screening with its notice attaches its summary', () => {
  assert.deepEqual(summaryToAttach('done', valid()), valid().chat_summary);
});

test('a screening without an MCP notice is invalid and is not attached', () => {
  assert.equal(summaryToAttach('done', valid(null)), null);
  assert.equal(summaryToAttach('done', valid('')), null);
});

test('a failed screening attaches its screening_failed summary', () => {
  assert.deepEqual(summaryToAttach('error', failed()), { aoi_ref: 'aoi-0123abcd', status: 'screening_failed' });
});

test('other errors, running, idle and missing results attach nothing', () => {
  assert.equal(summaryToAttach('error', failed('something_else')), null);
  assert.equal(summaryToAttach('error', null), null);
  assert.equal(summaryToAttach('running', valid()), null);
  assert.equal(summaryToAttach('idle', valid()), null);
  assert.equal(summaryToAttach('done', failed()), null);
});
