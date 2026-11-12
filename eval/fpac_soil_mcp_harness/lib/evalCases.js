// Loads eval/prompt_test_cases.json and derives concrete MCP invocations for each case.
//
// The test-case file describes natural-language prompts for an LLM agent. This harness is
// deterministic (no LLM): it maps each case to a direct tool call, resource read, or prompt
// render, then checks the response for the case's expected_keywords. Case-specific argument
// overrides below encode the parameters described in each user_prompt.

import fs from "node:fs";
import path from "node:path";

// ---------------------------------------------------------------------------
// Explicit per-case arguments for cases whose parameters live only in prose.
// ---------------------------------------------------------------------------
const CASE_ARGUMENTS = {
  "MUKEY-01": { mukey: "412850" },
  "INTERP-01": {
    mukeys: ["412850", "412851", "413100"],
    rule_name: "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)",
    aggregation_method: "Weighted Average",
  },
  "CORR-01": (tc) => ({
    centerline: tc.sample_geometry,
    buffer_distance: 75,
    buffer_units: "feet",
    indirect_geometry: {
      type: "Polygon",
      coordinates: [
        [
          [-93.56, 42.07],
          [-93.54, 42.07],
          [-93.54, 42.09],
          [-93.56, 42.09],
          [-93.56, 42.07],
        ],
      ],
    },
    productivity_index: "nccpi",
    site_assessment_inputs: { project_farm_acres: 350 },
  }),
  "CORR-02": (tc) => ({
    centerline: tc.sample_geometry,
    buffer_distance: 100,
    buffer_units: "feet",
    productivity_index: "nccpi",
    alternatives: [
      {
        alternative_id: "Alternative B",
        centerline: {
          type: "LineString",
          coordinates: [
            [-93.62, 42.0],
            [-93.58, 42.06],
            [-93.5, 42.1],
          ],
        },
        buffer_distance: 100,
        buffer_units: "feet",
      },
    ],
  }),
  "LESA-01": (tc) => ({
    project_name: "Maple Valley Substation",
    geometry: tc.sample_geometry,
    project_type: "site",
    productivity_index: "nccpi",
    site_assessment_inputs: {
      criteria_inputs: Object.fromEntries(
        [12, 8, 18, 15, 12, 12, 4, 6, 3, 16, 6, 8].map((points, i) => [
          String(i + 1),
          { awarded_points: points, justification: "Analyst-proposed score from field review" },
        ]),
      ),
    },
  }),
  "LESA-02": (tc) => ({
    project_name: "Regional Medical Clinic (45 ac)",
    geometry: tc.sample_geometry,
    project_type: "site",
    productivity_index: "nccpi",
  }),
  "PROMPT-01": {
    project_name: "50-acre rural water treatment facility",
    location: "Boone County, IA (-93.88, 42.05)",
    geometry_type: "point",
  },
  "PROMPT-02": { project_name: "Multi-county pipeline right-of-way", corridor_length_miles: "18" },
  "PROMPT-03": { project_name: "Logistics park expansion", jurisdiction: "Cedar Rapids, IA" },
  "PROMPT-04": { project_name: "USDA-funded community health facility", evaluation_type: "site" },
};

// Generic derivation from sample_geometry, keyed by tool name.
const TOOL_DERIVERS = {
  get_farmland_classification_by_point: (tc) => {
    const c = tc.sample_geometry?.coordinates;
    return Array.isArray(c) ? { latitude: c[1], longitude: c[0] } : {};
  },
  analyze_farmland_by_polygon: (tc) => ({ geojson: tc.sample_geometry, include_nccpi: true }),
  get_soil_polygons_by_geometry: (tc) => ({ geojson: tc.sample_geometry, clip: true }),
  check_urban_area_exemption: (tc) => ({ geojson: tc.sample_geometry }),
  analyze_corridor_fppa: (tc) => ({ centerline: tc.sample_geometry, buffer_distance: 100, buffer_units: "feet" }),
  calculate_preliminary_lesa: (tc) => ({ project_name: tc.id, geometry: tc.sample_geometry }),
};

// Additional hand-written presets (including negative / validation cases).
const EXTRA_PRESETS = {
  get_farmland_classification_by_point: [
    { label: "Boone County, IA (-93.88, 42.05)", arguments: { latitude: 42.05, longitude: -93.88 } },
    { label: "Negative: latitude out of range", arguments: { latitude: 123.4, longitude: -93.6 } },
    { label: "Negative: open ocean (no SSURGO coverage)", arguments: { latitude: 30.0, longitude: -60.0 } },
  ],
  get_farmland_classification_by_mukey: [
    { label: "Negative: non-numeric mukey", arguments: { mukey: "abc'; DROP TABLE mapunit;--" } },
  ],
  get_soil_interpretations: [
    {
      label: "Dominant component aggregation",
      arguments: { mukeys: ["412850"], aggregation_method: "Dominant Component" },
    },
    { label: "Negative: rule not in allowlist", arguments: { mukeys: ["412850"], rule_name: "Dwellings With Basements" } },
  ],
  analyze_farmland_by_polygon: [
    {
      label: "Negative: self-intersecting polygon",
      arguments: {
        geojson: {
          type: "Polygon",
          coordinates: [[[-93.65, 42.02], [-93.63, 42.04], [-93.63, 42.02], [-93.65, 42.04], [-93.65, 42.02]]],
        },
      },
    },
  ],
  analyze_corridor_fppa: [
    {
      label: "Negative: polygon passed as centerline",
      arguments: {
        centerline: {
          type: "Polygon",
          coordinates: [[[-93.65, 42.02], [-93.63, 42.02], [-93.63, 42.04], [-93.65, 42.04], [-93.65, 42.02]]],
        },
        buffer_distance: 100,
      },
    },
  ],
};

function resolveArguments(tc) {
  if (tc.harness_arguments && typeof tc.harness_arguments === "object") return structuredClone(tc.harness_arguments);
  const override = CASE_ARGUMENTS[tc.id];
  if (typeof override === "function") return override(tc);
  if (override) return structuredClone(override);
  if (tc.target_type === "tool") {
    const derive = TOOL_DERIVERS[tc.target_name];
    if (derive && tc.sample_geometry) return derive(tc);
  }
  return {};
}

export function buildInvocation(tc) {
  if (tc.target_type === "resource") return { kind: "resource", uri: tc.target_name };
  if (tc.target_type === "prompt") return { kind: "prompt", name: tc.target_name, arguments: resolveArguments(tc) };
  return { kind: "tool", name: tc.target_name, arguments: resolveArguments(tc) };
}

export function loadEvalCases(file) {
  if (!fs.existsSync(file)) {
    return { version: null, description: `Eval case file not found: ${file}`, test_cases: [], source: file };
  }
  const data = JSON.parse(fs.readFileSync(file, "utf-8"));
  const fixturePath = path.resolve(path.dirname(file), "eval_cases.v1.json");
  let executable = [];
  if (fs.existsSync(fixturePath)) {
    const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf-8"));
    executable = fixture.test_cases || [];
  }
  const byId = new Map(executable.map((tc) => [tc.id, tc]));
  const cases = (data.test_cases || []).map((tc) => {
    const central = byId.get(tc.id);
    const merged = central ? { ...tc, ...central } : tc;
    return { ...merged, invocation: merged.invocation || buildInvocation(merged) };
  });
  for (const tc of executable) if (!cases.some((item) => item.id === tc.id)) cases.push({ ...tc, invocation: tc.invocation || buildInvocation(tc) });
  return {
    version: data.version ?? null,
    executable_version: executable.length ? "1.0.0" : null,
    description: data.description ?? "",
    test_cases: cases,
    source: file,
    executable_source: executable.length ? fixturePath : null,
  };
}

export function buildPresets(cases) {
  const presets = {};
  for (const tc of cases) {
    const inv = tc.invocation;
    const key = inv.kind === "resource" ? `resource:${inv.uri}` : `${inv.kind}:${inv.name}`;
    (presets[key] ||= []).push({ label: `${tc.id} - ${tc.category}`, caseId: tc.id, arguments: inv.arguments ?? {} });
  }
  for (const [tool, extras] of Object.entries(EXTRA_PRESETS)) {
    (presets[`tool:${tool}`] ||= []).push(...extras);
  }
  return presets;
}

/** Normalize text for keyword matching (case-insensitive, unify section sign mojibake and whitespace). */
function normalize(text) {
  return String(text).replace(/\u00c2\u00a7/g, "\u00a7").replace(/\s+/g, " ").toLowerCase();
}

export function checkKeywords(expected, responseText) {
  const haystack = normalize(responseText);
  const found = [];
  const missing = [];
  for (const kw of expected || []) {
    (haystack.includes(normalize(kw)) ? found : missing).push(kw);
  }
  return { found, missing };
}
