import { createRoot } from 'react-dom/client';
import { Tool, ToolContent, ToolHeader, ToolInput, ToolOutput } from './elements/tool';
import { Button } from './ui/button';

const root = document.getElementById('root');
if (!root) throw new Error('Missing fixture root');

createRoot(root).render(
  <Tool defaultOpen={false}>
    <ToolHeader type="analyze_farmland_by_polygon" state="output-available">
      <Button
        size="sm"
        data-testid="show-on-map"
        aria-label="analyze_farmland_by_polygon: aoi-12345678"
      >
        Show on map · aoi-12345678
      </Button>
    </ToolHeader>
    <ToolContent>
      <ToolInput input={{ aoi_ref: 'aoi-12345678' }} />
      <ToolOutput output="Map result" />
    </ToolContent>
  </Tool>,
);
