import { useState } from 'react';
import { CLASS_BY_KEY, FARMLAND_CLASSES, classifyFarmland } from './farmlandClasses';
import type { FarmlandClass } from './farmlandClasses';
import { LegendSwatch, Swatch } from './Legend';
import type { MapLegendItem } from './mapLayers';
import type { DisplayAnalysis } from './useScreening';

function num(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function fmt(value: number | null | undefined): string {
  return value == null
    ? 'n/a'
    : value.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

// Server legend entry for a class when the result has one, else the client class.
function ClassMark({
  farmlandClass,
  legend,
}: {
  farmlandClass: FarmlandClass;
  legend: Map<string, MapLegendItem>;
}) {
  const item = legend.get(farmlandClass.key);
  return (
    <>
      {item ? <LegendSwatch item={item} /> : <Swatch farmlandClass={farmlandClass} />}
      <span className="font-mono text-xs">[{item?.code ?? farmlandClass.code}]</span>
    </>
  );
}

// The non-map way to read a screening result: class breakdown and map units.
export function ResultsTable({
  analysis,
  legend,
}: {
  analysis: DisplayAnalysis;
  legend?: MapLegendItem[];
}) {
  const [order, setOrder] = useState<'desc' | 'asc'>('desc');
  const legendByValue = new Map((legend ?? []).map((item) => [item.value, item]));
  const summary = analysis.farmland_summary ?? {};
  const classRows = FARMLAND_CLASSES.map((farmlandClass) => ({
    farmlandClass,
    acres: num(summary[`${farmlandClass.summaryKey}_acres`]),
    pct: num(summary[`${farmlandClass.summaryKey}_pct`]),
  })).filter((row) => row.acres !== null || row.pct !== null);
  const protectedAcres = num(summary.total_fppa_protected_acres);
  const protectedPct = num(summary.total_fppa_protected_pct);
  const units = [...(analysis.map_units ?? [])].sort((a, b) => {
    const difference = (a.acres ?? 0) - (b.acres ?? 0);
    return order === 'asc' ? difference : -difference;
  });

  return (
    <div className="flex flex-col gap-3 text-sm">
      <table className="w-full border-collapse">
        <caption className="text-left font-medium">
          Farmland classes (AOI {fmt(analysis.total_aoi_acres)} acres)
        </caption>
        <thead>
          <tr className="border-border border-b text-left">
            <th scope="col">Class</th>
            <th scope="col" className="text-right">
              Acres
            </th>
            <th scope="col" className="text-right">
              % of AOI
            </th>
          </tr>
        </thead>
        <tbody>
          {classRows.map(({ farmlandClass, acres, pct }) => (
            <tr key={farmlandClass.key} className="border-border border-b">
              <th scope="row" className="py-1 text-left font-normal">
                <span className="flex items-center gap-2">
                  <ClassMark farmlandClass={farmlandClass} legend={legendByValue} />
                  {farmlandClass.label}
                </span>
              </th>
              <td className="text-right">{fmt(acres)}</td>
              <td className="text-right">{fmt(pct)}</td>
            </tr>
          ))}
          {(protectedAcres !== null || protectedPct !== null) && (
            <tr>
              <th scope="row" className="py-1 text-left font-medium">
                Total FPPA-protected farmland
              </th>
              <td className="text-right font-medium">{fmt(protectedAcres)}</td>
              <td className="text-right font-medium">{fmt(protectedPct)}</td>
            </tr>
          )}
        </tbody>
      </table>

      {units.length > 0 && (
        <div className="max-w-full overflow-x-auto">
        <table className="w-full min-w-[40rem] border-collapse">
          <caption className="text-left font-medium">
            Map units ({units.length})
          </caption>
          <thead>
            <tr className="border-border border-b text-left">
              <th scope="col">Symbol</th>
              <th scope="col">Name</th>
              <th scope="col">Farmland class</th>
              <th
                scope="col"
                className="text-right"
                aria-sort={order === 'asc' ? 'ascending' : 'descending'}
              >
                <button
                  type="button"
                  className="underline-offset-2 hover:underline"
                  onClick={() => setOrder(order === 'asc' ? 'desc' : 'asc')}
                >
                  Acres {order === 'asc' ? '(low to high)' : '(high to low)'}
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {units.map((unit, index) => {
              const farmlandClass = CLASS_BY_KEY[classifyFarmland(unit.farmlndcl)];
              return (
                <tr
                  key={`${unit.mukey ?? unit.musym ?? 'unit'}-${index}`}
                  className="border-border border-b align-top"
                >
                  <td className="py-1 font-mono text-xs">{unit.musym ?? 'n/a'}</td>
                  <td className="whitespace-nowrap">{unit.muname ?? 'n/a'}</td>
                  <td>
                    <span className="flex items-center gap-2">
                      <ClassMark farmlandClass={farmlandClass} legend={legendByValue} />
                      {unit.farmlndcl || farmlandClass.label}
                    </span>
                  </td>
                  <td className="text-right">{fmt(unit.acres)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      )}
    </div>
  );
}
