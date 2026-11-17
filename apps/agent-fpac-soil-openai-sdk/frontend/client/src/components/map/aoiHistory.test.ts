import assert from 'node:assert/strict';
import test from 'node:test';
import { replaceAoi, undoAoi } from './aoiHistory';
import type { AoiHistory } from './aoiHistory';

type Aoi = { aoi_ref: string; summary: Record<string, unknown> | null };

const screened: Aoi = { aoi_ref: 'aoi-00000001', summary: { total_aoi_acres: 12 } };
const next: Aoi = { aoi_ref: 'aoi-00000002', summary: null };
const empty: AoiHistory<Aoi> = { aoi: null, previous: null };

test('a replaced AOI comes back from undo with the same reference and summary', () => {
  const replaced = replaceAoi({ aoi: screened, previous: null }, next);
  assert.deepEqual(replaced, { aoi: next, previous: screened });
  const undone = undoAoi(replaced);
  assert.equal(undone.aoi, screened);
  assert.equal(undone.previous, null);
});

test('clearing or detaching is undoable', () => {
  const cleared = replaceAoi({ aoi: screened, previous: null }, null);
  assert.deepEqual(cleared, { aoi: null, previous: screened });
  assert.equal(undoAoi(cleared).aoi, screened);
});

test('undo with nothing to restore changes nothing', () => {
  assert.equal(undoAoi(empty), empty);
  const first = replaceAoi(empty, next);
  assert.deepEqual(first, { aoi: next, previous: null });
  assert.equal(undoAoi(first), first);
});

test('clearing when there is no AOI keeps the history', () => {
  const cleared: AoiHistory<Aoi> = { aoi: null, previous: screened };
  assert.equal(replaceAoi(cleared, null), cleared);
});
