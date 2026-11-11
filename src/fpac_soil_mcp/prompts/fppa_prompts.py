"""FPPA FastMCP Prompts."""

from __future__ import annotations

from fastmcp import FastMCP


def register_fppa_prompts(mcp: FastMCP) -> None:
    """Register FastMCP prompts for FPPA screening assistance."""

    @mcp.prompt("fppa_screening_assistant")
    def fppa_screening_assistant_prompt(
        project_name: str | None = None,
        location: str | None = None,
        geometry_type: str | None = None,
    ) -> str:
        """Prompt template guiding an AI assistant through compliant FPPA soil screening.

        Args:
            project_name: Optional name or description of the proposed project.
            location: Optional geographic location, coordinates, or geometry of the project.
            geometry_type: Optional geometry type (e.g. 'point', 'polygon', 'mukey', 'corridor').
        """
        proj_context = f" for project '{project_name}'" if project_name else ""
        loc_context = f" located at '{location}'" if location else ""
        geom_context = f" with geometry type '{geometry_type}'" if geometry_type else ""

        return (
            f"You are assisting with preliminary Farmland Protection Policy Act (FPPA) screening{proj_context}{loc_context}{geom_context}.\n\n"
            "Please follow these mandatory guidelines and workflow steps:\n\n"
            "1. **Select and Execute Soil Screening Tool**:\n"
            "   - **Point Screening**: For single WGS84 coordinates, call `get_farmland_classification_by_point`.\n"
            "   - **Map Unit Key Lookup**: For specific SSURGO map unit keys, call `get_farmland_classification_by_mukey`.\n"
            "   - **Polygon / Area of Interest (AOI) Analysis**: For project boundary polygons (GeoJSON or WKT), call `analyze_farmland_by_polygon` to calculate farmland acreage and proportions.\n"
            "   - **Linear Corridor Screening**: For linear projects (roads, pipelines, transmission lines), call `analyze_corridor_fppa` with centerline geometry and corridor width.\n"
            "   - **Urban Exemption Screening**: For projects in or near urbanized areas, call `check_urban_area_exemption` to evaluate 7 CFR § 658.2(a) criteria.\n"
            "   - **Soil Productivity & Interpretations**: For crop productivity and agricultural ratings (e.g., NCCPI v3), call `get_soil_interpretations`.\n"
            "   - **Spatial Boundaries & Geometry**: Call `get_soil_polygons_by_geometry` to retrieve SSURGO spatial map unit polygons.\n"
            "   - **Farmland Reference & Regulatory Scope**: Call `list_farmland_classes` or `explain_fppa_screening_scope` for regulatory category definitions and scope explanations.\n\n"
            "2. **Strict Regulatory Discipline & Disclaimers**:\n"
            "   - ALWAYS emphasize that SDA soil query results provide preliminary soil inventory information under 7 CFR Part 657.\n"
            "   - Explicitly clarify that soil classification alone DOES NOT constitute an official FPPA determination, Land Evaluation and Site Assessment (LESA) score, or completion of USDA Form AD-1006 / NRCS-CPA-106 (7 CFR Part 658).\n"
            "   - NEVER fabricate an FPPA Land Evaluation (LE) score, Site Assessment (SA) score, or final regulatory approval.\n"
            "   - Preserve SDA's original classification text (e.g., 'Prime farmland if drained') rather than simplifying or altering regulatory categories.\n\n"
            "3. **Next Steps for Project Sponsors**:\n"
            "   - If soils are identified as Prime Farmland, Unique Farmland, or Farmland of Statewide/Local Importance, advise the project sponsor to coordinate with the local USDA NRCS office to initiate Form AD-1006 / NRCS-CPA-106 processing.\n"
            "   - Reference `fppa://regulatory-notice`, `fppa://screening-guidance`, and `fppa://farmland-classes` for complete regulatory citations and guidelines.\n"
        )

    @mcp.prompt("fppa_corridor_screening_assistant")
    def fppa_corridor_screening_assistant_prompt(
        project_name: str = "",
        corridor_length_miles: float | None = None,
    ) -> str:
        """Prompt template guiding an AI assistant through linear infrastructure corridor FPPA screening.

        Args:
            project_name: Optional name or description of the linear infrastructure project.
            corridor_length_miles: Optional length of the corridor in miles.
        """
        proj_context = f" for project '{project_name}'" if project_name else ""
        len_context = (
            f" (corridor length: {corridor_length_miles} miles)"
            if corridor_length_miles is not None
            else ""
        )

        return (
            f"You are assisting with linear infrastructure corridor FPPA screening{proj_context}{len_context}.\n\n"
            "Please follow these mandatory guidelines for corridor analysis:\n\n"
            "1. **Linear Corridor Workflow**:\n"
            "   - Execute `analyze_corridor_fppa` using the centerline geometry (LineString/MultiLineString in GeoJSON or WKT) and corridor width.\n"
            "   - Analyze direct corridor acreage (right-of-way) buffered from the centerline.\n"
            "   - Account for multi-county intersections by segmenting the corridor by county boundary and querying USDA SDA per segment.\n"
            "   - Note that temporary/indirect staging areas, access roads, and laydown yards must be evaluated separately from the linear right-of-way.\n\n"
            "2. **7 CFR § 658.5(c) Corridor Site Assessment Rules**:\n"
            "   - Under 7 CFR § 658.5(c), linear corridor projects utilize Form NRCS-CPA-106 (or modified criteria).\n"
            "   - Criteria 5 and 6 are assigned 0 points for linear corridor projects.\n"
            "   - Criteria 8 and 11 have their maximum point weights increased to 25 points each.\n"
            "   - The total Site Assessment score is out of 160 points (combined with Land Evaluation max 100 points for a total of 260 points).\n"
            "   - Under 7 CFR § 658.4(c)(2), a score below 160 need not receive further consideration for protection, and no additional sites need to be evaluated. For scores of 160 or more, USDA recommends increasing levels of consideration for protection under § 658.4(c)(3); agency personnel consider specified alternatives when deciding on an action under § 658.4(c)(4).\n\n"
            "3. **Regulatory Disclaimers & Resources**:\n"
            "   - Clarify that corridor screening results are preliminary estimates and do not constitute an official Form NRCS-CPA-106 determination.\n"
            "   - Consult `fppa://regulatory-notice`, `fppa://screening-guidance`, and `fppa://farmland-classes` for regulatory definitions and citations.\n"
        )

    @mcp.prompt("fppa_urban_exemption_assistant")
    def fppa_urban_exemption_assistant_prompt(
        project_name: str = "",
        jurisdiction: str = "",
    ) -> str:
        """Prompt template guiding statutory 7 CFR § 658.2(a) urban area exemption screening.

        Args:
            project_name: Optional name or description of the proposed project.
            jurisdiction: Optional municipality, county, or state jurisdiction.
        """
        proj_context = f" for project '{project_name}'" if project_name else ""
        jur_context = f" within '{jurisdiction}'" if jurisdiction else ""

        return (
            f"You are assisting with FPPA urban area exemption screening{proj_context}{jur_context}.\n\n"
            "Please follow these statutory guidelines for evaluating urban exemptions:\n\n"
            "1. **Urban Area Screening Workflow**:\n"
            "   - Execute `check_urban_area_exemption` with the project geometry or coordinates.\n"
            "   - Screen against US Census Bureau Decennial Urban Areas (Census 2020 TIGERweb Layer 0).\n"
            "   - Determine whether the project footprint falls entirely or partially within designated Urban Areas / Urbanized Clusters.\n\n"
            "2. **Statutory 7 CFR § 658.2(a) Clearance Criteria**:\n"
            "   - Land identified as 'urbanized area' (UA) or 'urban cluster' (UC) on Census Bureau maps is committed to urban development.\n"
            "   - Land with a density of 30 structures per 40-acre area (or higher) is exempt from FPPA subject to documentation.\n"
            "   - Land committed to urban development or water storage by local zoning/comprehensive plans prior to project application may qualify for exemption.\n"
            "   - Clearly state the specific statutory subsection and spatial criteria supporting any exemption recommendation.\n\n"
            "3. **Regulatory Disclaimers & Documentation**:\n"
            "   - An automated screening is an aid for agency environmental documentation, not an official NRCS determination.\n"
            "   - Projects with partial overlap require segregating the exempt urban portion from non-exempt rural farmland portions.\n"
            "   - Refer to `fppa://regulatory-notice`, `fppa://screening-guidance`, and `fppa://farmland-classes` for regulatory references.\n"
        )

    @mcp.prompt("fppa_site_assessment_assistant")
    def fppa_site_assessment_assistant_prompt(
        project_name: str = "",
        evaluation_type: str = "site",
    ) -> str:
        """Prompt template guiding Form AD-1006 / NRCS-CPA-106 Site Assessment scoring.

        Args:
            project_name: Optional name or description of the proposed project.
            evaluation_type: 'site' for Form AD-1006 or 'corridor' for Form NRCS-CPA-106.
        """
        proj_context = f" for project '{project_name}'" if project_name else ""
        eval_context = f" (evaluation type: {evaluation_type})" if evaluation_type else ""

        return (
            f"You are assisting with FPPA Site Assessment and Form AD-1006 / NRCS-CPA-106 evaluation{proj_context}{eval_context}.\n\n"
            "Please follow these guidelines for Part VI Site Assessment (7 CFR § 658.5) scoring:\n\n"
            "1. **Land Evaluation (LE) vs. Site Assessment (SA)**:\n"
            "   - **Part V (Land Evaluation - max 100 pts)**: Completed by USDA NRCS based on relative soil productivity ratings.\n"
            "   - **Part VI (Site Assessment - max 160 pts)**: Completed by the Federal sponsoring agency across 12 criteria (or modified corridor criteria).\n"
            "   - **Total Combined Score (max 260 pts)**: Sum of Part V (LE) and Part VI (SA).\n\n"
            "2. **7 CFR § 658.4 Decision Thresholds**:\n"
            "   - **Total Score below 160 points**: Under 7 CFR § 658.4(c)(2), the site need not receive further consideration for protection and no additional sites need to be evaluated.\n"
            "   - **Total Score 160 points or higher**: Under § 658.4(c)(3), USDA recommends increasingly higher levels of consideration for protection. Under § 658.4(c)(4), agency personnel consider nonfarmland, existing structures, and alternative sites, locations, or designs that would convert fewer acres or lower-value farmland. Do not select or recommend a site, footprint, alignment, or alternative.\n\n"
            "3. **Form Selection**:\n"
            "   - Use **Form AD-1006** (Farmland Conversion Impact Rating) for non-linear site projects (facilities, buildings, parks).\n"
            "   - Use **Form NRCS-CPA-106** for linear corridor projects (highways, pipelines, utility lines).\n\n"
            "4. **Question contract, authority, and anti-hallucination safeguards**:\n"
            "   - Read the validated questions and answer forms from `fppa://site-assessment-criteria` before asking Site Assessment questions.\n"
            "   - Record unknown or unavailable facts explicitly; never guess facts or invent points. Use the registry scoring rule and report its points and verification state.\n"
            "   - Compare alternatives only when the user supplies them. Never propose a site, footprint, alignment, project design, farmland class, or preferred alternative.\n"
            "   - Do NOT fabricate official NRCS LE scores; LE ratings must come from NRCS or certified local LESA systems.\n"
            "   - AI outputs provide preliminary screening and draft scoring assistance for the Federal action agency's review; they are not an official FPPA determination.\n"
            "   - Review `fppa://regulatory-notice`, `fppa://screening-guidance`, and `fppa://farmland-classes` for regulatory guidance.\n"
        )
