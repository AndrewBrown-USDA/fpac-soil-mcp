import { createRoot } from 'react-dom/client';
import { ChatExportActions } from './chat-export-actions';

const messages = [{
  role: 'user' as const,
  parts: [{ type: 'text', text: 'Screen this location.' }],
}, {
  role: 'assistant' as const,
  parts: [
    { type: 'text', text: 'Screening complete.' },
    {
      type: 'tool',
      toolName: 'analyze_farmland_by_polygon',
      input: { geometry: { type: 'Point', coordinates: [-98, 39] } },
      output: { status: 'ok', geometry: { type: 'Point', coordinates: [-98, 39] } },
      state: 'output-available',
    },
    { type: 'reasoning', text: 'private reasoning' },
  ],
}];

createRoot(document.getElementById('root')!).render(<ChatExportActions messages={messages as never} />);
