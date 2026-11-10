const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);

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
};

export function runPredicates(names, value, responseText = "", context = {}) {
  const results = [];
  for (const name of names || []) {
    const predicate = PREDICATES[name];
    results.push(predicate
      ? { name, passed: Boolean(predicate(value, responseText, context)) }
      : { name, passed: false, error: "Predicate is not allowlisted" });
  }
  return { passed: results.every((result) => result.passed), results };
}

export function evaluateResult({ value, responseText = "", expectedResult, predicates = [], context = {} }) {
  const schema = checkSchema(value, expectedResult);
  const predicate = runPredicates(predicates, value, responseText, context);
  return {
    status: !schema.valid ? "schema" : !predicate.passed ? "predicate" : "pass",
    schema,
    predicates: predicate,
  };
}
