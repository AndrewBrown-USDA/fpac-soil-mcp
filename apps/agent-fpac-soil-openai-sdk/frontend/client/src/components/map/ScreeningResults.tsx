import { useMemo } from 'react';
import { classifyFarmland } from './farmlandClasses';
import type { FarmlandClassKey } from './farmlandClasses';
import { Legend } from './Legend';
import { ResultsTable } from './ResultsTable';
import type { ScreeningResponse } from './useScreening';

function presentClasses(result: ScreeningResponse): Set<FarmlandClassKey> {
  const present = new Set<FarmlandClassKey>();
  for (const unit of result.display.analysis?.map_units ?? []) {
    present.add(classifyFarmland(unit.farmlndcl));
  }
  for (const feature of result.display.soil_polygons?.features ?? []) {
    present.add(classifyFarmland(feature.properties?.farmlndcl));
  }
  return present;
}

// Notice first (verbatim, ADR 0003), then legend and table.
export function ScreeningResults({ result }: { result: ScreeningResponse }) {
  const present = useMemo(() => presentClasses(result), [result]);
  const notice = result.display.regulatory_notice;
  const analysis = result.display.analysis;
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
      <Legend present={present} />
      {analysis && <ResultsTable analysis={analysis} />}
    </div>
  );
}
