import { CDL_LEGEND } from './cdlLegend';

export function CDLLegend() {
  return (
    <details>
      <summary className="cursor-pointer font-medium text-sm">CDL code and color key</summary>
      <p className="my-1 text-xs">USDA NASS land-cover context only; not screening evidence. <a className="underline" href="https://nass.usda.gov/research-and-science/cropland/docs/cdl-legend-colors">Official CDL legend</a>.</p>
      <ul className="grid gap-1 text-xs">
        {CDL_LEGEND.map(([code, name, color]) => (
          <li key={code} className="flex items-center gap-2">
            <span aria-hidden="true" className="h-3 w-4 shrink-0 border border-border" style={{ backgroundColor: color }} />
            <span>{code} — {name} ({color})</span>
          </li>
        ))}
      </ul>
    </details>
  );
}
