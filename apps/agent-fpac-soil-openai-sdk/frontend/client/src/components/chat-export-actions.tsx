import { useState } from 'react';
import {
  CHAT_EXPORT_SENSITIVITY_WARNING,
  serializeChatExportJson,
  serializeChatExportMarkdown,
  type ChatExportMessage,
} from '@/lib/chatExport';

export function ChatExportActions({ messages }: { messages: readonly ChatExportMessage[] }) {
  const [format, setFormat] = useState<'markdown' | 'json' | null>(null);

  function download() {
    if (!format) return;
    const content = format === 'json'
      ? serializeChatExportJson(messages)
      : serializeChatExportMarkdown(messages);
    const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `conversation.${format === 'json' ? 'json' : 'md'}`;
    link.click();
    URL.revokeObjectURL(url);
    setFormat(null);
  }

  return (
    <>
      <details className="relative">
        <summary className="cursor-pointer rounded-md border px-3 py-1.5 text-sm">Export chat</summary>
        <div className="absolute right-0 z-50 mt-1 flex min-w-36 flex-col rounded-md border bg-background p-1 shadow">
          <button type="button" className="p-2 text-left text-sm" onClick={() => setFormat('markdown')}>Markdown</button>
          <button type="button" className="p-2 text-left text-sm" onClick={() => setFormat('json')}>JSON</button>
        </div>
      </details>
      {format && (
        <div role="dialog" aria-modal="true" aria-labelledby="chat-export-title" className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
          <section className="w-full max-w-md rounded-lg bg-background p-5 shadow-xl">
            <h2 id="chat-export-title" className="text-lg font-semibold">Export {format === 'json' ? 'JSON' : 'Markdown'}?</h2>
            <p className="my-4 text-sm">{CHAT_EXPORT_SENSITIVITY_WARNING}</p>
            <div className="flex justify-end gap-2">
              <button type="button" className="rounded-md border px-3 py-2 text-sm" onClick={() => setFormat(null)}>Cancel</button>
              <button type="button" className="rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground" onClick={download}>Download export</button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
