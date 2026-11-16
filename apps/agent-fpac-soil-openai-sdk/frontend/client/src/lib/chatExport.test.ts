import assert from 'node:assert/strict';
import test from 'node:test';
import {
  CHAT_EXPORT_SENSITIVITY_WARNING,
  serializeChatExportJson,
  serializeChatExportMarkdown,
  type ChatExportMessage,
} from './chatExport';

const messages: ChatExportMessage[] = [{
  role: 'user',
  parts: [{ type: 'text', text: 'Screen this location.' }],
}, {
  role: 'assistant',
  parts: [
    { type: 'reasoning', text: 'private reasoning' } as never,
    { type: 'text', text: 'Screening complete.' },
    {
      type: 'tool',
      toolName: 'analyze_farmland_by_polygon',
      input: { geometry: { coordinates: [[-98, 39]], type: 'Point' } },
      output: { geometry: { coordinates: [[-98, 39]], type: 'Point' }, result: 'ok' },
      state: 'output-available',
    },
    { type: 'tool', toolName: 'pending_tool', input: { partial: true } },
  ],
}];

test('JSON export deterministically preserves visible text, raw tool data, and geometry only', () => {
  const json = serializeChatExportJson(messages);
  assert.equal(json, serializeChatExportJson(messages));
  assert.match(json, /Screen this location/);
  assert.match(json, /analyze_farmland_by_polygon/);
  assert.match(json, /"coordinates": \[/);
  assert.match(json, /"partial": true/);
  assert.doesNotMatch(json, /private reasoning|credential|server trace|unrelated/);
});

test('Markdown export deterministically includes visible text and raw tool input/output', () => {
  const markdown = serializeChatExportMarkdown(messages);
  assert.equal(markdown, serializeChatExportMarkdown(messages));
  assert.match(markdown, /## User/);
  assert.match(markdown, /Screening complete/);
  assert.match(markdown, /Input:[\s\S]*"coordinates"/);
  assert.match(markdown, /Output:[\s\S]*"result": "ok"/);
  assert.doesNotMatch(markdown, /private reasoning/);
});

test('empty and absent/partial messages do not fabricate content', () => {
  assert.equal(serializeChatExportJson(), '[]');
  assert.equal(serializeChatExportMarkdown(), '');
  assert.deepEqual(JSON.parse(serializeChatExportJson([
    { role: 'assistant' },
  ])), [{ role: 'assistant' }]);
});

test('export contract warns that tool data may contain sensitive coordinates', () => {
  assert.match(CHAT_EXPORT_SENSITIVITY_WARNING, /sensitive coordinates/);
});
