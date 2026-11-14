"""FPPA (Farmland Protection Policy Act) scope breakdown and explanation helpers.

Provides authoritative explanations distinguishing preliminary soil screening from
formal Land Evaluation and Site Assessment (LESA) determinations under 7 CFR Parts 657 & 658.
"""

from typing import Any

from fpac_soil_mcp.core.constants import (
    CITATIONS,
    FARMLAND_CLASS_DEFINITIONS,
    REGULATORY_LIMITATIONS,
    REGULATORY_NOTICE,
)


def get_fppa_scope_explanation() -> dict[str, Any]:
    """Return a comprehensive, structured explanation of FPPA screening vs. full determination.

    Returns:
        dict containing title, summary, sda_screening_scope, lesa_process_scope,
        citations, limitations, and regulatory_notice.
    """
    return {
        "title": "Farmland Protection Policy Act (FPPA) Screening Scope vs. Full Determination",
        "summary": (
            "This MCP service provides preliminary soil inventory screening based on USDA NRCS "
            "SSURGO soil map unit classifications (7 CFR Part 657). It does NOT perform formal "
            "Land Evaluation and Site Assessment (LESA) scoring or issue official FPPA findings (7 CFR Part 658)."
        ),
        "sda_screening_scope": {
            "what_is_provided": [
                "SSURGO map unit key (mukey), symbol (musym), and map unit name (muname)",
                "Official NRCS Farmland Classification attribute (mapunit.farmlndcl)",
                "Soil survey area symbol (areasymbol)",
                "Citation of relevant federal regulations (7 CFR Part 657)",
            ],
            "purpose": (
                "Identify whether soils within the queried area are categorized as Prime Farmland, "
                "Unique Farmland, or Farmland of Statewide/Local Importance to determine if further "
                "FPPA evaluation is triggered."
            ),
        },
        "lesa_determination_scope": {
            "what_is_required_for_official_fppa": [
                "Part V: Land Evaluation (LE) score assigned by USDA NRCS (0-100 points, based on soil capability/productivity).",
                "Part VI: Site Assessment (SA) score assigned by the Federal agency or grant recipient (0-160 points, based on non-soil factors: surrounding land use, urban infrastructure, zoning, farm size, investment).",
                "Total LESA Score calculation (0-260 points). Under 7 CFR § 658.4(c)(2), sites scoring below 160 need not receive further consideration for protection and no additional sites need to be evaluated. Under § 658.4(c)(3)-(4), USDA recommends increasing levels of consideration for protection at 160 points or more, and agency personnel consider alternatives when deciding on a proposed action; this service does not recommend an alternative.",
                "Submission and processing of USDA Form AD-1006 (or Form NRCS-CPA-106 for corridor projects).",
            ],
            "agency_responsibilities": (
                "Federal agencies proposing projects that may convert farmland must consult with NRCS State/Local offices "
                "and complete Form AD-1006 / NRCS-CPA-106 before finalizing project commitments."
            ),
        },
        "regulatory_notice": REGULATORY_NOTICE,
        "limitations": REGULATORY_LIMITATIONS,
        "citations": CITATIONS,
    }


def get_farmland_class_list() -> dict[str, Any]:
    """Return the documented reference listing of standard SDA farmland classification categories.

    Returns:
        dict containing standard farmland classes, their descriptions, and regulatory categories.
    """
    return {
        "source": "USDA NRCS Soil Data Access (SDA) / SSURGO mapunit.farmlndcl",
        "authority": CITATIONS["NSSH_622"],
        "classes": FARMLAND_CLASS_DEFINITIONS,
    }
