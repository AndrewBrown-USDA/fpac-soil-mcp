# Guided LESA Site Assessment: Trial Notes and Follow-ups

- **Date:** 2026-10-31.
- **Source:** Plan 42 task 42.6.1 deployed trial and one later trace (section 3, items 12-14), experiment `517983779529169`, one chat session of 19 traces on deployment `01f1d4fd835d1105a6edb990112c5f5b` (commit 171b470). See [`evidence/42.6.1-trial.md`](evidence/42.6.1-trial.md). The AOI and test answers were the user's; no coordinates here.
- **Goal (user):** the agent should guide users through processes like the Form AD-1006 Site Assessment, and the scoring decisions should be formalized so that scoring is consistent.
- **Limits of this record:** MLflow span data does not load from the client, so the tool arguments of the final LESA call (the points awarded per criterion) were not read. Only the total is known.

## 1. What happened

1. **Turn 1, full preliminary workflow.** On request, with the map AOI attached and nothing pasted, the agent ran urban-area screening, farmland classification, NCCPI land evaluation and LESA, and checked the alternatives threshold. With no site-assessment inputs, LESA came back as LE 73.89 + SA 0 = 73.89 / 260 and "alternatives not triggered"; the agent said this depended on the missing Site Assessment.
2. **Turns 2-18, guided Site Assessment.** The user asked to be walked through the 12 criteria. The agent asked one criterion per turn, stating the maximum points, offered answer options, and confirmed each answer ("Recorded") before moving on. It flagged overlap and verification needs. In three places (criteria 1, 8, 9) a free-text answer needed an extra turn to fit the offered categories.
3. **Turn 18, summary.** The agent tabled all 12 answers before scoring.
4. **Turn 19, refined LESA.** The agent called the LESA tool with site-assessment inputs: LE 73.89, SA 121.00 / 160, total 194.89 / 260, above the 160-point threshold, so in-depth consideration of alternatives is indicated (7 CFR § 658.4(c)(2)). The answer listed qualifications but **no per-criterion points**.

## 2. Questions, answers and recording

| # | Criterion (tool name) | Max | Agent's question and options | User answer as recorded | Turns |
|---|---|---:|---|---|---:|
| 1 | Area of non-urban land in 1-mile buffer | 15 | Percent non-urban within about 1 mile, or a description | Predominantly agricultural/open, next to a river; then about 95% | 3 |
| 2 | Perimeter of farmable land surrounding site | 10 | Percent of perimeter bordered by farmable land: 0-25 / 26-50 / 51-75 / 76-100% | 76-100% | 1 |
| 3 | Percentage of site farmed in 5 of last 10 years | 20 | Percent farmed in at least 5 of the past 10 years: same four bands | 76-100% | 1 |
| 4 | Agricultural protection status (easement/zoning) | 20 | Easement, agricultural zoning, protection program, none, unknown; percent affected | 20% adjacent to conservation easements; 30% restrictive agricultural designation; 10% protection program along the river (may overlap) | 1 |
| 5 | Distance to urban built-up area | 15 | Distance and the reference point | About 1.5 miles; reference point not given | 1 |
| 6 | Distance to municipal water/sewer | 15 | Distance, water/sewer/both, service available | None known; distance not given | 1 |
| 7 | Farm size compared to county average | 10 | Affected farm acres; county average if known | 250 ac vs 300 ac county average (83.3%) | 1 |
| 8 | Creation of non-farmable or inaccessible remnant parcels | 10 | None / minor / substantial / unknown, with description | Minor; no description | 2 |
| 9 | Availability of agricultural support services | 5 | Readily / somewhat / limited or unavailable / unknown | Readily available | 2 |
| 10 | On-farm capital investments and conservation measures | 20 | Substantial / moderate / minimal or none / unknown; list | Moderate: irrigation, conservation plans, buffers and wetlands | 1 |
| 11 | Reduction in local agricultural supply/service demand | 10 | Substantial / moderate / little or none / unknown | Moderate; most of the project extent would lose agricultural activity | 1 |
| 12 | Compatibility of site project with existing agricultural uses | 10 | Highly / moderately / not compatible / unknown | Not compatible | 1 |

Total SA 121.00 / 160. How the 121 points were split across criteria is not visible (see the limits above).

## 3. Findings

1. **The model decides the points.** `calculate_preliminary_lesa` takes `site_assessment_inputs.criteria_inputs` as `{criterion: {awarded_points, justification}}` and clamps each value to the criterion maximum (`lesa.py` `StandardCriterionStrategy`). Only criterion 7 is computed from facts (`FarmSizeCriterionStrategy`). For criteria 1-6 and 8-12 the model turned answers such as "Moderate" or "76-100%" into points by its own judgment, so two runs with the same answers can score differently. This is the main obstacle to consistent scoring.
2. **The answer bands are the model's own invention.** The quartile bands (0-25 ... 76-100%) and the qualitative categories (minor/substantial, readily/somewhat) are not the scales in 7 CFR § 658.5(b). The regulation gives point scales per criterion; to confirm against the regulation text before encoding them: for example, criterion 7 appears to deduct points in proportion to how far below the county average the farm is, whereas the tool awards 10, 5 or 0 points.
3. **Criterion names differ from the regulation.** `SITE_CRITERIA_NAMES` paraphrases § 658.5(b). For example, the regulation asks about water lines, sewer lines "and/or other local facilities and services" (criterion 6), the effect of conversion on farm support services (criterion 11), and whether the kind and intensity of conversion is incompatible with agriculture (criterion 12). The questions should follow the regulation.
4. **"Part V" and "Part VI" are mixed up.** On Form AD-1006, Part V is the Land Evaluation and Part VI the Site Assessment. `constants.py` (regulatory notice: "site assessment criteria (Part V)"), `fppa.py` ("Part V: Site Assessment"), `models.py` and the `lesa_tools.py` docstring ("Part V/VI") call the Site Assessment Part V; `fppa_prompts.py` has it right. The agent then said "Part V site-assessment inputs".
5. **An incomplete Site Assessment reads as a result.** With no SA inputs, LESA returns "alternatives not triggered" from LE alone. The agent caveated it, but the tool should report the threshold as not evaluated (and the maximum possible total) until the SA is supplied.
6. **Some answers need rules for unclear input.** Criterion 4 overlapping percentages and "adjacent to" vs "on the site"; criterion 5 distance without a reference point; criterion 6 "none known" without a distance; criterion 8 "minor" without a description. The agent flagged them but the scoring of each is undefined.
7. **Data the server could fill in.** Criterion 7's county average farm size could come from NASS (the server has `nass_client.py`); the user typed it. Criteria 1 and 5 could be estimated from TIGERweb 2020 Urban Areas (already a client), shown to the user as a proposed answer with provenance. Criterion 3 (farmed history) and criterion 4 (easements) would need new sources and are candidates only.
8. **The final answer omits the breakdown.** The refined LESA gave only the SA total. A per-criterion table (answer, rule, points, verification flag) is needed for review and consistency.
9. **No-AOI turns don't mention the map.** In a new chat, "run the FPPA process" got a request for GeoJSON or a centerline; the agent did not suggest drawing or pasting the AOI on the map panel.
10. **Observability.** In later turns the request previews are cut at 10,000 characters, so `custom_inputs` is not visible; span data does not load. The tool arguments and per-criterion points cannot be audited from the client today.
11. **Cost of the guided flow.** 18 turns for 12 criteria (about 10-12k input tokens each, 27k for the final turn). Asking for several closely related criteria in one turn, or a structured form, would cut it.

### Later trace: the agent proposed a siting alternative (2026-10-31)

Trace `tr-c5f8b34c27b` (same deployment, about 624-acre AOI, user: "use the fppa assistant prompt on the selected aoi and guide me thru ranking").

12. **The agent suggested where to build.** Its "preliminary siting preference" was to place the facility on the about 31 acres mapped as not prime farmland and avoid the about 592 acres of prime farmland if irrigated. It then wrote a general ranking scheme for project alternatives. The not-prime acres in that AOI are mostly water, riverwash and loamy alluvial land.
    - **Why this is unsafe (user):** farmland class alone does not make land suitable. Other soil interpretations that keep a map unit out of prime farmland (flooding, wetness, wetlands, riverwash and similar) can preclude development outside FPPA, and the standard FPPA tools do not have the information to evaluate them. Adding that context is possible but long tail.
    - **Rule (user):** the FPPA agent does not suggest alternatives, sites or footprints. It compares alternatives only when the user provides them, and it reports the FPPA consequence of a score (for example, that alternatives must be considered at 160 points or more) without proposing what they should be.
13. **The prompt and tool text push towards alternatives.** `fppa_site_assessment_assistant` adds score bands (160-220 "consider alternative sites if available", over 220 "must consider alternative sites"); 7 CFR § 658.4(c) sets the 160-point line and asks for increasing consideration above it, so the bands need checking against the regulation. `LESA_ACTION_*` texts in `constants.py` and the LESA action list name "alternative project designs", "avoidance of prime/unique farmlands" and reduced footprints. These are regulatory consequences, but the model turned them into a specific siting suggestion.
14. **Chat context from another place.** The AOI was attached in the chat where PROMPT-01 had described a Boone County, Iowa project; the AOI's soil survey areas were in California. The agent noticed and flagged the mismatch, which is the right behaviour. A new AOI in a chat with an earlier project description is a case to cover in instructions and evals.

## 4. Follow-ups

### MCP server tools (owner: server roadmap)

- **Rule-based Site Assessment scoring.** Add a fact-based input mode, for example `criteria_facts: {1: {non_urban_pct: 95}, 5: {distance_mi: 1.5, reference: "boundary"}, ...}`, scored in `lesa.py` with the § 658.5(b) scales (versioned in `constants.py` or a bundled scoring registry like `regional_scoring.v1.json`), returning per criterion the rule applied, the points and a `needs_verification` flag. Keep `awarded_points` as an explicit override with a required justification, reported as an override. Verify every scale against the regulation text before release.
- **Question schema.** A resource or tool (for example `fppa://site-assessment-criteria` or `get_site_assessment_questions(project_type)`) with, per criterion, the regulation's question, the accepted answer form (percent, distance, yes/no, category), the scoring rule and the citation, so every client asks the same questions. Cover the corridor variant (NRCS-CPA-106; criteria 5 and 6 are zero under § 658.5(c)).
- **Threshold when SA is missing.** Report `threshold_status: "not_evaluated"` and the maximum possible total when no SA inputs are given, instead of "not triggered".
- **Prefill with provenance.** Criterion 7 county average from NASS; criteria 1 and 5 estimates from TIGERweb urban areas; returned as proposed answers the user confirms.
- **No siting recommendations in tool output.** Keep the LESA action texts as statements of what the regulation requires ("alternatives must be considered"), not suggestions of which land to use; the tools do not rank land within an AOI as a siting preference.
- **Long tail (optional):** soil interpretations that can preclude development outside FPPA (flooding, ponding, hydric soils, wetlands), only as context with clear limits and never as a siting recommendation.
- **Text fixes.** Use "Part VI" for the Site Assessment in `constants.py`, `fppa.py`, `models.py` and the `lesa_tools.py` docstring; align `SITE_CRITERIA_NAMES` with § 658.5(b) wording; review criterion 7's 10/5/0 steps against the regulation.

### Agent system instructions (owner: agent app)

- When guiding a Site Assessment, get the questions from the server's question schema, ask in the regulation's terms, accept the answer forms the schema defines, and record "unknown" rather than guessing.
- Never pick points yourself: send facts to the tool and report the tool's per-criterion points and rules; use an override only when the user gives a points value and a reason.
- Before scoring, show the collected answers for confirmation (the agent already did this well); after scoring, show a per-criterion table and list items that need verification.
- Say that a LESA without Site Assessment inputs has not evaluated the threshold.
- With no AOI attached, suggest drawing or pasting one on the map before asking for GeoJSON.
- Keep the preliminary-screening language (held in every trial answer).
- Do not suggest alternatives, sites, footprints or which farmland classes to build on. Farmland class alone does not show land is suitable; other soil and site factors outside the FPPA tools can preclude development. Compare alternatives only when the user provides them, and state the regulatory consequence of a score without proposing alternatives.
- If an attached AOI does not match the project described earlier in the chat (place, size, type), say so and ask before screening.

### Agent app and prompts

- An MCP prompt (or an update of `fppa_site_assessment_assistant`) for the guided flow, using the question schema, so the agent app and other MCP clients run the same process.
- Review the FPPA prompts in `fppa_prompts.py` for alternative-siting language and the 160-220 / over-220 bands; apply the no-suggested-alternatives rule there too, so every MCP client gets it.
- Optional later: a structured form in the chat UI for the 12 criteria instead of 12 turns.
- One AOI reference for the map screening and the chat (see the evidence file).

### Evaluation and observability

- A multi-turn eval case: a fixed AOI fixture (synthetic geometry) and a fixed set of 12 answers, expecting the same per-criterion points and total on every run, the per-criterion table, the threshold result and preliminary language.
- A case for LESA without SA inputs expecting "not evaluated".
- A negative case: screening or ranking an AOI with mixed farmland classes must not recommend building on the non-prime part or propose alternatives; a paired case where the user supplies two alternatives expects a comparison.
- Record per-turn trace tags from the agent server (for example the active `aoi_ref` and the LESA tool's SA total and per-criterion points) so they can be audited without span data. Geometry may appear in traces (ADR 0016), but tags should stay small.
