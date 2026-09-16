"""FPPA FastMCP Prompts."""

from fastmcp import FastMCP


def register_fppa_prompts(mcp: FastMCP) -> None:
    """Register FastMCP prompts for FPPA screening assistance."""

    @mcp.prompt("fppa_screening_assistant")
    def fppa_screening_assistant_prompt(
        project_name: str | None = None, location: str | None = None
    ) -> str:
        """Prompt template guiding an AI assistant through compliant FPPA soil screening.

        Args:
            project_name: Optional name or description of the proposed project.
            location: Optional geographic location or coordinates of the project.
        """
        proj_context = f" for project '{project_name}'" if project_name else ""
        loc_context = f" located at '{location}'" if location else ""

        return (
            f"You are assisting with preliminary Farmland Protection Policy Act (FPPA) screening{proj_context}{loc_context}.\n\n"
            "Please follow these mandatory guidelines and workflow steps:\n\n"
            "1. **Execute Preliminary Soil Screening**:\n"
            "   - If coordinates (WGS84 latitude and longitude) are provided, call `get_farmland_classification_by_point`.\n"
            "   - If a SSURGO map unit key (mukey) is provided, call `get_farmland_classification_by_mukey`.\n"
            "   - Review the `farmlndcl` attribute in the returned `map_units`.\n\n"
            "2. **Strict Regulatory Discipline & Disclaimers**:\n"
            "   - ALWAYS emphasize that SDA soil query results provide preliminary soil inventory information under 7 CFR Part 657.\n"
            "   - Explicitly clarify that soil classification alone DOES NOT constitute an official FPPA determination, Land Evaluation and Site Assessment (LESA) score, or completion of USDA Form AD-1006 / NRCS-CPA-106 (7 CFR Part 658).\n"
            "   - NEVER fabricate an FPPA Land Evaluation (LE) score, Site Assessment (SA) score, or final regulatory approval.\n"
            "   - Preserve SDA's original classification text (e.g., 'Prime farmland if drained') rather than simplifying or altering regulatory categories.\n\n"
            "3. **Next Steps for Project Sponsors**:\n"
            "   - If soils are identified as Prime Farmland, Unique Farmland, or Farmland of Statewide/Local Importance, advise the project sponsor to coordinate with the local USDA NRCS office to initiate Form AD-1006 / NRCS-CPA-106 processing.\n"
            "   - Reference `fppa://regulatory-notice` and `fppa://screening-guidance` for complete regulatory citations.\n"
        )
