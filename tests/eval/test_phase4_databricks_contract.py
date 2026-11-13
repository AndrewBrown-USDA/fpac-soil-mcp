"""Offline contract checks for Plan 45 model-assisted T1 cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from common.dataset import load_cases, load_gold_set, to_mlflow_records

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPO_ROOT / "eval" / "eval_cases.v1.json"
SA_MA_IDS = ("SA-MA-01", "SA-MA-02", "SA-MA-03", "SA-MA-04")
POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-93.65, 42.02],
            [-93.63, 42.02],
            [-93.63, 42.04],
            [-93.65, 42.04],
            [-93.65, 42.02],
        ]
    ],
}


def test_sa_ma_cases_are_in_t1_records_and_keep_model_evidence_label() -> None:
    cases = load_cases(DATASET_PATH, ids=SA_MA_IDS)
    records = to_mlflow_records(cases)

    assert [case["id"] for case in cases] == list(SA_MA_IDS)
    for case, record in zip(cases, records, strict=True):
        assert case["expected_facts"]
        assert record["expectations"]["case_id"] == case["id"]
        assert record["expectations"]["expected_facts"] == case["expected_facts"]
        assert record["expectations"]["evidence_tier"] == "model_assisted"
    assert all(case.get("evidence_tier") == "model_assisted" for case in cases)


def test_case_catalogs_align_without_unneeded_geometry() -> None:
    cases = load_cases(DATASET_PATH, ids=SA_MA_IDS)

    for case in cases:
        assert case["target_type"] in {"tool", "resource", "prompt"}
        assert case["target_name"].strip()
        assert case["user_prompt"].strip()
        assert isinstance(case["expected_keywords"], list)
        assert case["expected_facts"]
        assert case["evidence_tier"] == "model_assisted"
    assert "sample_geometry" not in cases[0]
    assert "sample_geometry" not in cases[2]


def test_tool_cases_include_matching_geometry_and_intended_arguments() -> None:
    cases = {case["id"]: case for case in load_cases(DATASET_PATH, ids=SA_MA_IDS)}

    for case_id, tool_name, geometry_key in (
        ("SA-MA-02", "calculate_preliminary_lesa", "geometry"),
        ("SA-MA-04", "analyze_farmland_by_polygon", "geojson"),
    ):
        case = cases[case_id]
        call = case["expected_tool_calls"][0]
        assert case["target_name"] == tool_name
        assert case["expected_tools"] == [tool_name]
        assert case["sample_geometry"] == POLYGON
        assert case["invocation"]["name"] == tool_name
        assert case["invocation"]["arguments"][geometry_key] == POLYGON
        assert call["name"] == tool_name
        assert call["arguments"][geometry_key] == POLYGON
        compact_geometry = json.dumps(POLYGON, separators=(",", ":"))
        assert compact_geometry in case["user_prompt"].replace(" ", "")

    lesa_args = cases["SA-MA-02"]["expected_tool_calls"][0]["arguments"]
    assert lesa_args["project_name"] == "Synthetic SA-MA-02"
    assert lesa_args["project_type"] == "site"
    assert "site_assessment_inputs" not in lesa_args
    assert cases["SA-MA-04"]["expected_tool_calls"][0]["arguments"]["productivity_index"] == "csr2"


def test_site_assessment_expectations_do_not_reward_fabrication_or_siting() -> None:
    cases = load_cases(DATASET_PATH, ids=SA_MA_IDS)

    for case in cases:
        assert not case.get("numeric_expectations")
        guidance = " ".join(case.get("guidelines", [])).casefold()
        assert "do not invent" in guidance or "do not fabricate" in guidance
    for case in cases[:3]:
        guidance = " ".join(case.get("guidelines", [])).casefold()
        assert any(term in guidance for term in ("site", "alternative", "footprint"))
    for case_id in ("SA-MA-01", "SA-MA-03"):
        assert "sample_geometry" not in next(case for case in cases if case["id"] == case_id)

    lesa_facts = " ".join(cases[1]["expected_facts"]).casefold()
    assert "rather than being treated as zero" in lesa_facts
    assert "unevaluable total" in lesa_facts
    property_facts = " ".join(cases[3]["expected_facts"]).casefold()
    assert "does not replace csr2" in property_facts
    assert "rather than inferred" in property_facts


def test_contract_and_judge_evidence_remain_distinct() -> None:
    databricks_path = str(REPO_ROOT / "eval" / "databricks")
    sys.path.insert(0, databricks_path)
    try:
        from scorers import DETERMINISTIC_SCORER_NAMES, JUDGE_SCORER_NAMES, evidence_tier
    finally:
        sys.path.remove(databricks_path)

    assert all(
        evidence_tier(name) == "deterministic_contract" for name in DETERMINISTIC_SCORER_NAMES
    )
    assert all(evidence_tier(name) == "model_assisted" for name in JUDGE_SCORER_NAMES)

    gold_cases = load_gold_set()
    assert gold_cases
    assert all(case["deterministic"] is True for case in gold_cases)


def test_missing_expected_facts_omit_judge_expectations_instead_of_failing() -> None:
    source = load_cases(DATASET_PATH, ids=("LESA-01",))[0]
    assert source["expected_facts"]
    case = {
        key: value for key, value in source.items() if key not in ("expected_facts", "guidelines")
    }
    record = to_mlflow_records([case])[0]

    assert "expected_facts" not in record["expectations"]
    assert "guidelines" not in record["expectations"]
