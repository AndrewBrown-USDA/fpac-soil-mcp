import assert from 'node:assert/strict';
import test from 'node:test';
import { lineDistance } from './distance';

test('measures a synthetic one-degree equatorial line in selectable units', () => {
  const line = [[0, 0], [1, 0]];
  assert.ok(Math.abs(lineDistance(line, 'kilometers') - 111.195) < 0.02);
  assert.ok(Math.abs(lineDistance(line, 'meters') - 111195) < 20);
  assert.ok(Math.abs(lineDistance(line, 'miles') - 69.09) < 0.02);
});

test('empty and single-point lines have zero length; invalid positions are rejected as zero', () => {
  assert.equal(lineDistance([], 'meters'), 0);
  assert.equal(lineDistance([[1, 2]], 'meters'), 0);
  assert.equal(lineDistance([[0, 0], [Number.NaN, 1]], 'meters'), 0);
});
