"""FPPA FastMCP Resources."""

import json

from fastmcp import FastMCP

from fpac_soil_mcp.core.constants import CITATIONS, REGULATORY_LIMITATIONS, REGULATORY_NOTICE
from fpac_soil_mcp.domain.fppa import get_farmland_class_list, get_fppa_scope_explanation
from fpac_soil_mcp.domain.site_assessment import SITE_ASSESSMENT_REGISTRY


def register_fppa_resources(mcp: FastMCP) -> None:
    """Register FastMCP resources for FPPA screening guidance and notices."""

    @mcp.resource("fppa://regulatory-notice")
    def get_regulatory_notice_resource() -> str:
        """Official regulatory notice and legal limitations for FPPA preliminary screening."""
        notice_data = {
            "title": "USDA FPPA Regulatory Notice & Legal Disclaimer",
            "regulatory_notice": REGULATORY_NOTICE,
            "limitations": REGULATORY_LIMITATIONS,
            "citations": CITATIONS,
        }
        return json.dumps(notice_data, indent=2)

    @mcp.resource("fppa://screening-guidance")
    def get_screening_guidance_resource() -> str:
        """Comprehensive guidance distinguishing preliminary soil screening from full LESA scoring."""
        explanation = get_fppa_scope_explanation()
        return json.dumps(explanation, indent=2)

    @mcp.resource("fppa://farmland-classes")
    def get_farmland_classes_resource() -> str:
        """Reference listing of SSURGO farmland classification categories and criteria."""
        class_list = get_farmland_class_list()
        return json.dumps(class_list, indent=2)

    @mcp.resource("fppa://site-assessment-criteria")
    def get_site_assessment_criteria_resource() -> str:
        """Validated Site Assessment questions, answer forms, and scoring rules."""
        payload = SITE_ASSESSMENT_REGISTRY.model_dump(mode="json", by_alias=True)
        # Serve each band exactly as the registry specifies it: defaulted null bounds
        # and inclusivity flags make strict clients reject the whole criteria payload.
        for criterion, dumped in zip(
            SITE_ASSESSMENT_REGISTRY.criteria, payload["criteria"], strict=True
        ):
            dumped["bands"] = [
                band.model_dump(mode="json", by_alias=True, exclude_unset=True)
                for band in criterion.bands
            ]
        return json.dumps(payload, indent=2)
