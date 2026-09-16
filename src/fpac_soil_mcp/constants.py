"""FPPA domain constants, regulatory notices, official citations, and SSURGO classification definitions.

References:
- 7 CFR Part 657: Prime and Unique Farmlands
- 7 CFR Part 658: Farmland Protection Policy Act
- USDA NRCS National Soil Survey Handbook (NSSH) Part 622
- USDA Form AD-1006 / NRCS-CPA-106
"""

from typing import Final

# Official Regulatory Disclaimers & Notices
REGULATORY_NOTICE: Final[str] = (
    "PRELIMINARY SCREENING ONLY: This service retrieves soil map unit classifications from "
    "the USDA NRCS Soil Data Access (SDA) SSURGO database. SDA farmland classification attributes "
    "(mapunit.farmlndcl) provide preliminary soil inventory information under 7 CFR Part 657. "
    "This query DOES NOT constitute an official FPPA determination, Land Evaluation and Site Assessment "
    "(LESA) score, or completion of USDA Form AD-1006 / NRCS-CPA-106. Formal FPPA determinations require "
    "coordination with the appropriate USDA NRCS State/Local office and assessment of project footprint, "
    "site assessment criteria (Part V), and local land use conditions."
)

REGULATORY_LIMITATIONS: Final[list[str]] = [
    "SDA soil attributes reflect map unit inventory data (7 CFR Part 657) and do not evaluate site-specific project footprints.",
    "Official FPPA compliance requires completion of Form AD-1006 or NRCS-CPA-106 including Site Assessment criteria (7 CFR Part 658.5).",
    "Areas mapped as 'Not prime farmland' or conditional farmland (e.g., 'if drained', 'if irrigated') require on-site verification of local water management infrastructure.",
    "Urbanized areas and land committed to urban development may be exempt from FPPA provisions under 7 CFR 658.2(a) regardless of underlying soil classification.",
    "Soil Data Access (SDA) data may be subject to survey updates; always verify with current NRCS Web Soil Survey or local NRCS soil conservationist for binding determinations.",
]

# Official Legal and Policy Citations
CITATIONS: Final[dict[str, str]] = {
    "7_CFR_657": "7 CFR Part 657 - Prime and Unique Farmlands (Definitions and Inventory of Prime, Unique, and Other Farmland)",
    "7_CFR_658": "7 CFR Part 658 - Farmland Protection Policy Act (Implementation Regulations, Criteria, and Procedures)",
    "NSSH_622": "USDA NRCS National Soil Survey Handbook (NSSH), Part 622 - Ecological and Interpretive Groups: Farmland Classification",
    "FORM_AD_1006": "USDA Form AD-1006 - Farmland Conversion Impact Rating (for Corridor-Type and Non-Corridor Federal Projects)",
    "FORM_NRCS_CPA_106": "USDA Form NRCS-CPA-106 - Farmland Conversion Impact Rating for Corridor Type Projects",
    "SDA_SERVICE": "USDA NRCS Soil Data Access (SDA) REST Service (https://sdmdataaccess.nrcs.usda.gov/)",
    "WEB_SOIL_SURVEY": "USDA NRCS Web Soil Survey (WSS) (https://websoilsurvey.sc.egov.usda.gov/)",
}

# Standard SSURGO Farmland Classification Categories (mapunit.farmlndcl)
FARMLAND_CLASS_DEFINITIONS: Final[dict[str, dict[str, str]]] = {
    "All areas are prime farmland": {
        "description": "Land that has the best combination of physical and chemical characteristics for producing food, feed, forage, fiber, and oilseed crops and is available for these uses.",
        "fppa_status": "Prime Farmland under 7 CFR 657.5(a)",
        "regulatory_category": "Prime Farmland",
    },
    "Prime farmland if drained": {
        "description": "Soils that meet prime farmland criteria only when adequate artificial drainage systems are installed and maintained.",
        "fppa_status": "Conditional Prime Farmland under 7 CFR 657.5(a)(2)",
        "regulatory_category": "Conditional Prime Farmland",
    },
    "Prime farmland if protected from flooding or not frequently flooded during the growing season": {
        "description": "Soils that meet prime farmland criteria only when protected from flooding by levees, dams, or natural protection during growing season.",
        "fppa_status": "Conditional Prime Farmland under 7 CFR 657.5(a)(2)",
        "regulatory_category": "Conditional Prime Farmland",
    },
    "Prime farmland if irrigated": {
        "description": "Soils that meet prime farmland criteria only when an adequate, dependable supply of irrigation water is available.",
        "fppa_status": "Conditional Prime Farmland under 7 CFR 657.5(a)(2)",
        "regulatory_category": "Conditional Prime Farmland",
    },
    "Prime farmland if drained and either protected from flooding or not frequently flooded during the growing season": {
        "description": "Soils that require both drainage and flood protection to qualify as prime farmland.",
        "fppa_status": "Conditional Prime Farmland under 7 CFR 657.5(a)(2)",
        "regulatory_category": "Conditional Prime Farmland",
    },
    "Prime farmland if irrigated and drained": {
        "description": "Soils that require both irrigation and drainage to qualify as prime farmland.",
        "fppa_status": "Conditional Prime Farmland under 7 CFR 657.5(a)(2)",
        "regulatory_category": "Conditional Prime Farmland",
    },
    "Prime farmland if irrigated and either protected from flooding or not frequently flooded during the growing season": {
        "description": "Soils that require both irrigation and flood protection to qualify as prime farmland.",
        "fppa_status": "Conditional Prime Farmland under 7 CFR 657.5(a)(2)",
        "regulatory_category": "Conditional Prime Farmland",
    },
    "Prime farmland if subsoiled, completely removing the root inhibiting layer": {
        "description": "Soils that meet prime farmland criteria only after deep tillage or subsoiling to break root-restrictive layers.",
        "fppa_status": "Conditional Prime Farmland under 7 CFR 657.5(a)(2)",
        "regulatory_category": "Conditional Prime Farmland",
    },
    "Prime farmland if reclaimed of excess salts and sodium": {
        "description": "Soils that meet prime farmland criteria only when chemical/physical remediation reduces salinity and sodicity.",
        "fppa_status": "Conditional Prime Farmland under 7 CFR 657.5(a)(2)",
        "regulatory_category": "Conditional Prime Farmland",
    },
    "Farmland of statewide importance": {
        "description": "Land criteria defined by state agencies that is of statewide importance for agricultural production but does not meet full national prime farmland criteria.",
        "fppa_status": "Farmland of Statewide Importance under 7 CFR 657.5(c)",
        "regulatory_category": "Statewide Importance",
    },
    "Farmland of local importance": {
        "description": "Land identified by local county or municipal entities as important for local agriculture though not recognized statewide or nationally.",
        "fppa_status": "Farmland of Local Importance under 7 CFR 657.5(d)",
        "regulatory_category": "Local Importance",
    },
    "Farmland of unique importance": {
        "description": "Land other than prime farmland used for the production of specific high-value food and fiber crops (e.g., citrus, cranberries, nuts, fruit).",
        "fppa_status": "Unique Farmland under 7 CFR 657.5(b)",
        "regulatory_category": "Unique Farmland",
    },
    "Not prime farmland": {
        "description": "Soils that do not meet the criteria for Prime, Unique, Statewide, or Locally Important Farmland.",
        "fppa_status": "Not Protected under FPPA baseline soil criteria",
        "regulatory_category": "Not Prime Farmland",
    },
}
