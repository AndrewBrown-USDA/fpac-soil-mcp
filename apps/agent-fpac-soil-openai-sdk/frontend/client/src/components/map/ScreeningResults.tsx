import { MapLegend } from './Legend';
import { ResultsTable } from './ResultsTable';
import type { ScreeningResponse } from './useScreening';

const FARMLAND_LAYER_ID = 'farmland_classes';

// Notice first (verbatim, ADR 0003), then the server's map legends and the table.
export function ScreeningResults({ result }: { result: ScreeningResponse }) {
  const notice = result.display.regulatory_notice;
  const analysis = result.display.analysis;
  const block = result.display.map;
  const farmlandLegend = block?.layers.find((layer) => layer.id === FARMLAND_LAYER_ID)?.legend;
  return (
    <div className="flex flex-col gap-3">
      {notice ? (
        <div className="rounded-md border border-border bg-muted p-2 text-sm">
          <h3 className="font-medium">Regulatory notice</h3>
          <p className="whitespace-pre-line">{notice}</p>
        </div>
      ) : (
        <p role="alert" className="text-destructive text-sm">
          Regulatory notice missing - treat this result as invalid.
        </p>
      )}
      {block && <MapLegend block={block} />}
      {analysis && <ResultsTable analysis={analysis} legend={farmlandLegend} />}
    </div>
  );
}
