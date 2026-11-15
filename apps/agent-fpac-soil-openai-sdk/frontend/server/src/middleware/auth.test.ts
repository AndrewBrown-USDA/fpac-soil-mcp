import assert from 'node:assert/strict';
import test from 'node:test';
import { localDevSession } from './auth';

test('local development session is available only when enabled on loopback', () => {
  assert.equal(localDevSession(false, '127.0.0.1'), undefined);
  assert.equal(localDevSession(true, '192.0.2.10'), undefined);
  assert.deepEqual(localDevSession(true, '127.0.0.1')?.user, {
    id: 'local-dev-user',
    email: 'local-dev@localhost',
    name: 'Local Development User',
    preferredUsername: 'local-dev',
    type: 'regular',
  });
});
