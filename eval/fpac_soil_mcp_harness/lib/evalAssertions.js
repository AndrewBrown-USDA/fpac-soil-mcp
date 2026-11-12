import { readFileSync } from "node:fs";

const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);

// Shared with eval/common/matching.py; see the catalog's description field.
const CATALOG = JSON.parse(readFileSync(new URL("../../common/prohibited_behaviors.v1.json", import.meta.url), "utf8"));
const NEGATION = new RegExp(CATALOG.negation, "i");
const normalizeText = (text) => String(text ?? "").replace(/[\u2018\u2019]/g, "'");

function typeMatches(value, type) {
  return type === "object" ? isObject(value)
    : type === "array" ? Array.isArray(value)
      : type === "null" ? value === null
        : typeof value === type;
}

export function checkSchema(value, schema, path = "$") {
  const errors = [];
  if (!schema || typeof schema !== "object") return { valid: true, errors };
  if (schema.type && !typeMatches(value, schema.type)) {
    errors.push(`${path} must be ${schema.type}`);
    return { valid: false, errors };
  }
  if (schema.required && isObject(value)) {
    for (const key of schema.required) if (!(key in value)) errors.push(`${path}.${key} is required`);
  }
  if (schema.properties && isObject(value)) {
    for (const [key, child] of Object.entries(schema.properties)) {
      if (key in value) errors.push(...checkSchema(value[key], child, `${path}.${key}`).errors);
    }
  }
  if (schema.items && Array.isArray(value)) {
    value.forEach((item, index) => errors.push(...checkSchema(item, schema.items, `${path}[${index}]`).errors));
  }
  return { valid: errors.length === 0, errors };
}

const PREDICATES = {
  preliminaryScreeningOnly: (value, text) => value?.preliminary_screening === true || /preliminary screening/i.test(text),
  containsRegulatoryLimitation: (_value, text) => /not (an )?official FPPA determination|not a formal FPPA determination/i.test(text),
  noSitingRecommendation: (value, text, context) => {
    const forbiddenFields = ["recommended_site", "siting_recommendation", "preferred_site", "preferred_alternative"];
    if (forbiddenFields.some((key) => value?.[key] != null && value[key] !== "")) return false;
    if (context.invocation?.kind === "prompt") {
      return /\bdo not\b.{0,40}\b(?:select|recommend|choose)\b/i.test(text);
    }
    return !/\b(?:I|we|the tool)\s+(?:recommend|select|choose)\s+(?:the|this|a|an)\s+(?:site|location|alternative|footprint)\b/i.test(text);
  },
  noFabricatedScore: (value) => {
    const assessment = value?.site_assessment;
    if (!isObject(assessment)) return false;
    if (assessment.evaluation_status === "complete") return true;
    return value.threshold_status === "not_evaluated"
      && value.total_lesa_score === null
      && value.mandatory_alternatives_required === null;
  },
  preservesSelectedProperty: (value, _text, context) => {
    const expected = context.invocation?.arguments?.productivity_index;
    const actual = value?.productivity_index ?? value?.manifest?.productivity_index;
    return typeof expected === "string" && typeof actual === "string"
      && expected.toLowerCase() === actual.toLowerCase();
  },
  requiredStatus: (value, _text, _context, expectations) =>
    typeof expectations.expected_status === "string" && readStatus(value) === expectations.expected_status,
  requiredBehaviors: (_value, text, _context, expectations) =>
    Array.isArray(expectations.required_behaviors) && expectations.required_behaviors.length > 0
      && expectations.required_behaviors.every((item) => typeof item === "string" && text.toLowerCase().includes(item.toLowerCase())),
  prohibitedBehaviors: (_value, text, _context, expectations) =>
    Array.isArray(expectations.prohibited_behaviors) && expectations.prohibited_behaviors.length > 0
      && expectations.prohibited_behaviors.every((item) => !hasProhibitedClaim(text, item)),
  sourceDisclosure: (_value, text, _context, expectations) =>
    Array.isArray(expectations.source_disclosure) && expectations.source_disclosure.length > 0
      && expectations.source_disclosure.every((item) => typeof item === "string" && text.toLowerCase().includes(item.toLowerCase())),
  privacyNonEcho: (_value, text, _context, expectations) =>
    Array.isArray(expectations.sensitive_values) && expectations.sensitive_values.length > 0
      && expectations.sensitive_values.every((item) => typeof item === "string" && item && !text.includes(item)),
  toolCallBudget: (value, _text, _context, expectations) =>
    Number.isInteger(expectations.max_tool_calls) && Number.isInteger(value?.tool_call_count)
      && value.tool_call_count <= expectations.max_tool_calls,
  retryBudget: (value, _text, _context, expectations) =>
    Number.isInteger(expectations.max_retries) && Number.isInteger(value?.retry_count)
      && value.retry_count <= expectations.max_retries,
  latencyBudget: (value, _text, _context, expectations) =>
    Number.isFinite(expectations.latency_budget_ms) && Number.isFinite(value?.elapsed_ms)
      && value.elapsed_ms <= expectations.latency_budget_ms,
};

function readStatus(value) {
  if (!isObject(value)) return undefined;
  for (const key of ["status", "coverage_status", "result_status"]) {
    if (key in value) return value[key];
  }
  for (const key of ["result", "structuredContent", "structured_content"]) {
    const status = readStatus(value[key]);
    if (status !== undefined) return status;
  }
  return undefined;
}

// claim: affirmative (non-negated) match violates; omission: absent disclosure violates;
// structural: enforced by runner budgets, not text. Unknown IDs fail closed.
export function hasProhibitedClaim(rawText, behavior) {
  const spec = CATALOG.behaviors[behavior];
  if (!spec) return true;
  if (spec.kind === "structural") return false;
  const text = normalizeText(rawText);
  if (spec.kind === "omission") return !new RegExp(spec.pattern, "i").test(text);
  for (const match of text.matchAll(new RegExp(spec.pattern, "gi"))) {
    const start = Math.max(...[".", "!", "?", ";", "\n"].map((mark) => text.lastIndexOf(mark, match.index - 1))) + 1;
    const prefix = text.slice(start, match.index).trim().split(/\s+/).slice(-5).join(" ");
    if (!NEGATION.test(prefix)) return true;
  }
  return false;
}

export function runPredicates(names, value, responseText = "", context = {}, expectations = context) {
  const results = [];
  for (const name of names || []) {
    const predicate = PREDICATES[name];
    results.push(predicate
      ? { name, passed: Boolean(predicate(value, responseText, context, expectations)) }
      : { name, passed: false, error: "Predicate is not allowlisted" });
  }
  return { passed: results.every((result) => result.passed), results };
}

export function evaluateResult({ value, responseText = "", expectedResult, predicates = [], context = {}, expectations = {} }) {
  const schema = checkSchema(value, expectedResult);
  const predicate = runPredicates(predicates, value, responseText, context, expectations);
  return {
    status: !schema.valid ? "schema" : !predicate.passed ? "predicate" : "pass",
    schema,
    predicates: predicate,
  };
}
