import type { ExpressionSpecification } from 'maplibre-gl';
import type { SoilFeatureCollection } from './useScreening';

// One mapping from SSURGO `farmlndcl` text to a display class, used by the map
// layer, the legend and the results table. The rules mirror the server's
// `categorize_farmland_class` (src/fpac_soil_mcp/polygon_analysis.py): empty is
// unmapped, any other unrecognised text counts as not prime. Colours and codes
// follow the Phase 8 symbology; the code keeps meaning off colour alone.
export type FarmlandClassKey =
  | 'prime'
  | 'conditional_prime'
  | 'statewide'
  | 'local'
  | 'unique'
  | 'not_prime'
  | 'unmapped';

export type FarmlandClass = {
  key: FarmlandClassKey;
  label: string;
  code: string;
  color: string;
  pattern: 'solid' | 'hatched';
  // Prefix of `<summaryKey>_acres` / `<summaryKey>_pct` in `farmland_summary`.
  summaryKey: string;
};

export const FARMLAND_CLASSES: readonly FarmlandClass[] = [
  {
    key: 'prime',
    label: 'Prime farmland',
    code: 'P',
    color: '#2E7D32',
    pattern: 'solid',
    summaryKey: 'prime_farmland',
  },
  {
    key: 'conditional_prime',
    label: 'Prime farmland if conditions are met',
    code: 'P*',
    color: '#81C784',
    pattern: 'hatched',
    summaryKey: 'conditional_prime',
  },
  {
    key: 'statewide',
    label: 'Farmland of statewide importance',
    code: 'S',
    color: '#F9A825',
    pattern: 'solid',
    summaryKey: 'statewide_importance',
  },
  {
    key: 'local',
    label: 'Farmland of local importance',
    code: 'L',
    color: '#0288D1',
    pattern: 'solid',
    summaryKey: 'local_importance',
  },
  {
    key: 'unique',
    label: 'Unique farmland',
    code: 'U',
    color: '#6A1B9A',
    pattern: 'solid',
    summaryKey: 'unique_farmland',
  },
  {
    key: 'not_prime',
    label: 'Not prime farmland',
    code: 'NP',
    color: '#9E9E9E',
    pattern: 'solid',
    summaryKey: 'not_prime',
  },
  {
    key: 'unmapped',
    label: 'Unmapped',
    code: 'UM',
    color: '#FFFFFF',
    pattern: 'hatched',
    summaryKey: 'unmapped',
  },
];

export const CLASS_BY_KEY = Object.fromEntries(
  FARMLAND_CLASSES.map((farmlandClass) => [farmlandClass.key, farmlandClass]),
) as Record<FarmlandClassKey, FarmlandClass>;

export function classifyFarmland(farmlndcl: unknown): FarmlandClassKey {
  if (typeof farmlndcl !== 'string' || !farmlndcl.trim()) return 'unmapped';
  const desc = farmlndcl.trim().toLowerCase();
  if (desc === 'all areas are prime farmland') return 'prime';
  if (desc.includes('prime farmland if')) return 'conditional_prime';
  if (desc.includes('statewide importance')) return 'statewide';
  if (desc.includes('local importance')) return 'local';
  if (desc.includes('unique importance') || desc.includes('unique farmland')) {
    return 'unique';
  }
  return 'not_prime';
}

// Fill colour keyed on the `farmland_class` property added by withFarmlandClass.
export const FARMLAND_FILL_COLOR = [
  'match',
  ['get', 'farmland_class'],
  ...FARMLAND_CLASSES.flatMap((farmlandClass) => [
    farmlandClass.key,
    farmlandClass.color,
  ]),
  CLASS_BY_KEY.unmapped.color,
] as unknown as ExpressionSpecification;

export function withFarmlandClass(
  collection: SoilFeatureCollection,
): SoilFeatureCollection {
  return {
    ...collection,
    features: collection.features.map((feature) => ({
      ...feature,
      properties: {
        ...(feature.properties ?? {}),
        farmland_class: classifyFarmland(feature.properties?.farmlndcl),
      },
    })),
  };
}
