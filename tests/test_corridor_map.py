"""Map layers on the corridor farmland analysis (ADR 0017). Synthetic geometry only."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from shapely.geometry import box, shape

from fpac_soil_mcp import corridor_analysis
from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.corridor_analysis import CorridorAnalyzer
from fpac_soil_mcp.geometry import buffer_centerline, calculate_acreage
from fpac_soil_mcp.integration_models import (
    CountyAgProfile,
    IntegrationStatus,
    UrbanExemptionRecord,
)
from fpac_soil_mcp.sda_client import SDAClient
from fpac_soil_mcp.tigerweb_client import TigerwebClient

MARKER = "R6-MARKER"
CENTERLINE = "LINESTRING(0.0 0.005, 0.01 0.005)"
ALT_CENTERLINE = "LINESTRING(0.0 0.007, 0.01 0.007)"
INDIRECT = box(0.004, 0.0, 0.006, 0.002)
URBAN = box(0.008, 0.0, 0.03, 0.03)
PROVENANCE = Provenance(
    source_name="synthetic",
    source_reference="synthetic",
    timestamp_utc=datetime(2026, 1, 1, tzinfo=UTC),
    method_version="1.0.0",
    configuration_version="1.0.0",
)


def _row(mukey: str, farmlndcl: str, geom) -> dict:
    return {
        "mukey": mukey,
        "musym": f"{MARKER}{mukey}",
        "muname": f"{MARKER} unit {mukey}",
        "farmlndcl": farmlndcl,
        "areasymbol": "ZZ001",
        "area_ac": "1.5",
        "geom": geom.wkt,
    }


def _segments(footprint) -> list[dict]:
    west, east = box(-1, -1, 0.005, 1), box(0.005, -1, 1, 1)
    out = []
    for fips, name, clip in (("001", f"{MARKER} West", west), ("003", f"{MARKER} East", east)):
        geom = footprint.intersection(clip)
        out.append(
            {
                "state_fips": "99",
                "county_fips": fips,
                "county_name": name,
                "state_name": "ZZ",
                "geometry": geom,
                "calculated_acres": calculate_acreage(geom),
            }
        )
    return out


def _clients(urban_names=(f"{MARKER} Urban",)):
    sda = MagicMock(spec=SDAClient)
    sda.base_url = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"

    def spatial(wkt, clip=True, geom_acres=True, return_geom=False):
        rows = [
            _row("2001", "All areas are prime farmland", box(0.0, 0.004, 0.005, 0.006)),
            _row("2002", "Farmland of statewide importance", box(0.005, 0.004, 0.01, 0.006)),
        ]
        if not return_geom:
            for row in rows:
                row.pop("geom")
        return rows

    sda.get_spatial_intersection.side_effect = spatial
    sda.get_productivity_ratings.return_value = []
    sda.get_interpretations.return_value = [
        {"mukey": "2001", "numeric_rating": "0.8", "rating_class": "High"},
        {"mukey": "2002", "numeric_rating": "0.5", "rating_class": "Moderate"},
    ]
    sda.get_county_max_productivity_rating.return_value = 1.0

    tiger = MagicMock(spec=TigerwebClient)
    record = UrbanExemptionRecord(
        status=IntegrationStatus.SUCCESS,
        geometry_hash="sha256:" + "2" * 64,
        provenance=PROVENANCE,
        is_urban_intersected=bool(urban_names),
        urban_area_names=list(urban_names),
        screened_acreage=0.0,
    )
    tiger.check_urban_exemption_with_geometries.side_effect = lambda geom: (
        record,
        [(name, URBAN) for name in urban_names],
    )
    tiger.get_perimeter_evidence.return_value = {"evidence_status": "synthetic"}
    tiger.get_intersecting_counties.return_value = [
        {"state_fips": "99", "county_fips": "001", "county_name": f"{MARKER} West"},
        {"state_fips": "99", "county_fips": "003", "county_name": f"{MARKER} East"},
    ]
    tiger.partition_geometry_by_counties.side_effect = (
        lambda geometry_input, counties=None, **kwargs: _segments(geometry_input)
    )

    nass = MagicMock()
    nass.get_county_ag_profile.side_effect = lambda county, **kwargs: CountyAgProfile(
        status=IntegrationStatus.SUCCESS,
        state_fips=county.state_fips,
        county_fips=county.county_fips,
        county_name=county.county_name,
        census_year=2022,
        provenance=PROVENANCE,
    )
    return sda, tiger, nass


def _run(include_map: bool, *, alternatives=None, indirect=None, urban_names=None):
    sda, tiger, nass = _clients() if urban_names is None else _clients(urban_names)
    result = CorridorAnalyzer(
        sda_client=sda, tigerweb_client=tiger, nass_client=nass
    ).analyze_corridor(
        centerline_input=CENTERLINE,
        buffer_distance=50.0,
        buffer_units="meters",
        indirect_geometry_input=indirect,
        alternatives=alternatives,
        include_map=include_map,
    )
    return result, sda, tiger


ALTERNATIVES = [{"alternative_id": "B-2", "centerline": ALT_CENTERLINE}]


def _layers(result) -> dict:
    return {layer.id: layer for layer in result.map.layers}


def test_numbers_identical_with_and_without_map():
    plain, _, _ = _run(False, alternatives=ALTERNATIVES, indirect=INDIRECT)
    mapped, _, _ = _run(True, alternatives=ALTERNATIVES, indirect=INDIRECT)
    assert plain.geometry_hash == mapped.geometry_hash
    assert plain.impact_breakdown == mapped.impact_breakdown
    assert plain.county_segments == mapped.county_segments
    assert plain.reconciliation_summary == mapped.reconciliation_summary
    assert plain.alternatives == mapped.alternatives
    assert plain.composite_relative_rating == mapped.composite_relative_rating
    assert plain.tabular_csv == mapped.tabular_csv
    assert len(plain.county_segments) == 2


@pytest.mark.parametrize("include_map", [False, True])
def test_call_counts_and_return_geom(include_map):
    _, sda, tiger = _run(include_map, alternatives=ALTERNATIVES)
    flags = [c.kwargs["return_geom"] for c in sda.get_spatial_intersection.call_args_list]
    # Primary and alternative segments both follow the flag (alternative farmland is drawn).
    assert flags == [include_map, include_map, include_map, include_map]
    assert tiger.check_urban_exemption_with_geometries.call_count == 2
    tiger.check_urban_exemption.assert_not_called()


def test_default_map_is_descriptor_only():
    result, _, _ = _run(False, alternatives=ALTERNATIVES, indirect=INDIRECT)
    assert result.schema_version == "1.0"
    assert result.authority.official_filing is False
    assert [layer.id for layer in result.map.layers] == [
        "corridor_direct",
        "corridor_indirect",
        "corridor_alternative_b_2",
        "farmland_classes",
        "county_segments",
        "urban_context",
    ]
    assert all(layer.delivery == "omitted" for layer in result.map.layers)
    assert result.map.bounds is None
    assert "coordinates" not in json.dumps(result.map.model_dump())


def test_no_indirect_or_alternative_layers_without_inputs():
    result, _, _ = _run(False)
    assert [layer.id for layer in result.map.layers] == [
        "corridor_direct",
        "farmland_classes",
        "county_segments",
        "urban_context",
    ]


def test_inline_layers_when_requested():
    result, _, _ = _run(True, alternatives=ALTERNATIVES, indirect=INDIRECT)
    layers = _layers(result)
    assert all(layer.delivery == "inline_geojson" for layer in layers.values())

    direct = shape(layers["corridor_direct"].feature_collection["features"][0]["geometry"])
    expected = buffer_centerline(CENTERLINE, 50.0, "meters")
    assert direct.equals(expected)
    assert layers["corridor_direct"].simplified is False

    indirect = layers["corridor_indirect"]
    assert indirect.feature_count == 1
    assert (
        shape(indirect.feature_collection["features"][0]["geometry"]).intersection(direct).area
        < 1e-12
    )

    alt = layers["corridor_alternative_b_2"]
    assert alt.title == "Alternative B-2 footprint"
    assert alt.legend[0].color != layers["corridor_direct"].legend[0].color

    farmland = layers["farmland_classes"]
    assert farmland.feature_count == 4  # two rows per primary segment
    classes = {f["properties"]["farmland_class"] for f in farmland.feature_collection["features"]}
    assert classes == {"prime", "statewide"}

    counties = layers["county_segments"]
    props = [f["properties"] for f in counties.feature_collection["features"]]
    assert props == [
        {
            "county_name": f"{MARKER} West",
            "geoid": "99001",
            "state_fips": "99",
            "county_fips": "001",
        },
        {
            "county_name": f"{MARKER} East",
            "geoid": "99003",
            "state_fips": "99",
            "county_fips": "003",
        },
    ]

    urban = layers["urban_context"]
    assert urban.feature_count == 1  # same urban area from both segments, de-duplicated
    assert urban.feature_collection["features"][0]["properties"] == {"name": f"{MARKER} Urban"}

    assert result.map.bounds is not None
    assert result.map.bounds[2] == pytest.approx(0.03)
    assert result.map.warnings == []


def test_inline_without_urban_areas():
    result, _, _ = _run(True, urban_names=())
    urban = _layers(result)["urban_context"]
    assert urban.delivery == "inline_geojson"
    assert urban.feature_count == 0


def test_size_cap_drops_context_layers_first(monkeypatch):
    plain, _, _ = _run(True)
    sizes = {
        layer.id: len(json.dumps(layer.feature_collection, separators=(",", ":")))
        for layer in plain.map.layers
    }
    keep = sizes["corridor_direct"] + sizes["farmland_classes"]
    monkeypatch.setattr(corridor_analysis.map_settings, "map_max_geojson_bytes", keep + 1)
    capped, _, _ = _run(True)
    layers = _layers(capped)
    assert layers["urban_context"].truncated is True
    assert layers["county_segments"].truncated is True
    assert layers["farmland_classes"].delivery == "inline_geojson"
    assert layers["corridor_direct"].delivery == "inline_geojson"
    assert capped.tabular_csv == plain.tabular_csv


def test_centerline_error_returns_descriptor_map():
    sda, tiger, nass = _clients()
    result = CorridorAnalyzer(
        sda_client=sda, tigerweb_client=tiger, nass_client=nass
    ).analyze_corridor(centerline_input="LINESTRING(0 0)", buffer_distance=50.0, include_map=True)
    assert result.reconciliation_summary["status"] == "error"
    assert [layer.id for layer in result.map.layers] == [
        "corridor_direct",
        "farmland_classes",
        "county_segments",
        "urban_context",
    ]
    assert all(layer.delivery == "omitted" for layer in result.map.layers)
    sda.get_spatial_intersection.assert_not_called()


@pytest.mark.parametrize(
    ("alt_id", "suffix"), [("B", "b"), ("Route 9/East", "route_9_east"), ("", "alt")]
)
def test_alternative_layer_suffix(alt_id, suffix):
    assert corridor_analysis._alternative_layer_suffix(alt_id) == suffix


@pytest.mark.parametrize(
    ("alt_ids", "expected"),
    [
        (["B-2", "B 2"], ["corridor_alternative_b_2", "corridor_alternative_b_2_2"]),
        (
            ["B", "b", "B"],
            ["corridor_alternative_b", "corridor_alternative_b_2", "corridor_alternative_b_3"],
        ),
        (
            ["A", "A", "A 2"],
            ["corridor_alternative_a", "corridor_alternative_a_2", "corridor_alternative_a_2_2"],
        ),
        (["", "?"], ["corridor_alternative_alt", "corridor_alternative__"]),
    ],
)
def test_alternative_layer_ids_are_unique(alt_ids, expected):
    ids = corridor_analysis._alternative_layer_ids(alt_ids)
    assert ids == expected
    assert len(set(ids)) == len(ids)


def test_duplicate_alternative_ids_get_distinct_layers():
    alternatives = [
        {"alternative_id": "B-2", "centerline": ALT_CENTERLINE},
        {"alternative_id": "B 2", "centerline": "LINESTRING(0.0 0.003, 0.01 0.003)"},
    ]
    result, _, _ = _run(True, alternatives=alternatives)
    alt_layers = [
        layer for layer in result.map.layers if layer.id.startswith("corridor_alternative_")
    ]
    assert [layer.id for layer in alt_layers] == [
        "corridor_alternative_b_2",
        "corridor_alternative_b_2_2",
    ]
    assert [layer.title for layer in alt_layers] == [
        "Alternative B-2 footprint",
        "Alternative B 2 footprint",
    ]
    assert alt_layers[0].legend[0].color != alt_layers[1].legend[0].color
    assert len({layer.id for layer in result.map.layers}) == len(result.map.layers)


def test_alternative_reports_class_breakdown_like_the_primary():
    result, _, _ = _run(False, alternatives=ALTERNATIVES)
    (alt,) = result.alternatives
    # Each of two alternative county segments returns one prime and one statewide row
    # of 1.5 ac.
    assert alt.prime_farmland_acres == 3.0
    assert alt.statewide_importance_acres == 3.0
    assert alt.conditional_prime_acres == 0.0
    assert alt.local_importance_acres == 0.0
    assert alt.unique_farmland_acres == 0.0
    assert alt.not_prime_acres == 0.0
    assert alt.not_prime_pct == 0.0
    assert alt.total_fppa_protected_acres == 6.0
    parts = (
        alt.prime_farmland_acres
        + alt.conditional_prime_acres
        + alt.statewide_importance_acres
        + alt.local_importance_acres
        + alt.unique_farmland_acres
        + alt.not_prime_acres
        + alt.unmapped_acres
    )
    assert parts == pytest.approx(alt.total_project_acres, abs=0.05)


OVERLAPPING_ALT = [{"alternative_id": "C", "centerline": "LINESTRING(0.0 0.0055, 0.01 0.0055)"}]


def test_alternative_farmland_is_drawn_outside_the_primary_footprint():
    result, _, _ = _run(True, alternatives=OVERLAPPING_ALT)
    layer = _layers(result)["farmland_classes"]
    assert layer.title == "Farmland classification (all alignments)"
    features = layer.feature_collection["features"]
    alt_features = [f for f in features if f["properties"].get("alignment") == "C"]
    primary = [f for f in features if "alignment" not in f["properties"]]
    assert primary and alt_features
    direct = buffer_centerline(
        centerline_input=CENTERLINE, buffer_distance=50.0, distance_unit="meters"
    )
    alt_footprint = buffer_centerline(
        centerline_input=OVERLAPPING_ALT[0]["centerline"],
        buffer_distance=50.0,
        distance_unit="meters",
    )
    for feature in alt_features:
        geom = shape(feature["geometry"])
        assert "area_ac" not in feature["properties"]
        assert feature["properties"]["farmland_class"] in {"prime", "statewide"}
        # Display copies are simplified at about 1 m, so allow a sliver of overlap.
        assert geom.intersection(direct).area <= geom.area * 0.02
        assert geom.difference(alt_footprint.buffer(1e-5)).area <= geom.area * 0.02


def test_alternative_outside_soil_rows_adds_no_features():
    # ALTERNATIVES lies outside every synthetic soil row, so it adds no features.
    result, _, _ = _run(True, alternatives=ALTERNATIVES)
    layer = _layers(result)["farmland_classes"]
    features = layer.feature_collection["features"]
    assert not [f for f in features if "alignment" in f["properties"]]
