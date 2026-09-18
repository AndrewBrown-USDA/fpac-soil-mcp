"""USDA NASS QuickStats REST API client.

Queries authoritative agricultural demographics (land in farms, cropland, average farm size)
by State and County FIPS/names for FPPA Site Assessment baselines (7 CFR § 658.5).
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

import httpx

from fpac_soil_mcp.authority import Provenance
from fpac_soil_mcp.config import settings
from fpac_soil_mcp.integration_models import CountyAgProfile, IntegrationStatus

logger = logging.getLogger(__name__)


class NassClient:
    """Client for USDA NASS QuickStats REST API (/api_GET/)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.nass_api_key
        self.base_url = (base_url or settings.nass_base_url).rstrip("/")
        self.timeout = timeout or settings.request_timeout_seconds
        self._http_client = http_client

    def get_county_ag_profile(
        self,
        state_fips: str,
        county_fips: str,
        county_name: str,
        state_alpha: str | None = None,
        census_year: int = 2022,
    ) -> CountyAgProfile:
        """Fetch county agricultural demographic baseline from NASS QuickStats.

        Args:
            state_fips: 2-digit state FIPS code (e.g. '19').
            county_fips: 3-digit county FIPS code (e.g. '169').
            county_name: County or parish name (e.g. 'Story').
            state_alpha: Optional 2-letter state postal code (e.g. 'IA').
            census_year: Census of Agriculture year (default 2022).

        Returns:
            CountyAgProfile with land in farms, cropland, farm count, and average farm size.
        """
        now = datetime.now(UTC)
        provenance = Provenance(
            source_name="USDA NASS Census of Agriculture Quick Stats",
            source_reference=self.base_url,
            timestamp_utc=now,
            method_version="1.0.0",
            configuration_version=f"census_{census_year}",
        )

        # Graceful fallback if API key is not configured
        if not (self.api_key and self.api_key.strip()):
            return CountyAgProfile(
                status=IntegrationStatus.UNAVAILABLE,
                state_fips=state_fips,
                county_fips=county_fips,
                county_name=county_name,
                census_year=census_year,
                provenance=provenance,
                error_message="USDA NASS API key (NASS_API_KEY) is not configured.",
            )

        params: dict[str, Any] = {
            "key": self.api_key.strip(),
            "source_desc": "CENSUS",
            "sector_desc": "ECONOMICS",
            "agg_level_desc": "COUNTY",
            "year": census_year,
            "state_fips_code": state_fips.zfill(2),
            "county_code": county_fips.zfill(3),
            "format": "JSON",
        }
        if state_alpha:
            params["state_alpha"] = state_alpha.upper()

        query_url = self.base_url if self.base_url.endswith("/api_GET/") else f"{self.base_url}/"

        try:
            if self._http_client is not None:
                resp = self._http_client.get(query_url, params=params, timeout=self.timeout)
            else:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(query_url, params=params)

            if resp.status_code == 404 or "No results found" in resp.text:
                return CountyAgProfile(
                    status=IntegrationStatus.UNAVAILABLE,
                    state_fips=state_fips,
                    county_fips=county_fips,
                    county_name=county_name,
                    census_year=census_year,
                    provenance=provenance,
                    error_message=f"No NASS agricultural census records found for county {county_name} ({state_fips}{county_fips}) in year {census_year}.",
                )

            resp.raise_for_status()
            data = resp.json().get("data", [])

            land_in_farms: float | None = None
            total_cropland: float | None = None
            farm_count: int | None = None
            avg_farm_size: float | None = None
            unavailable: list[str] = []

            for rec in data:
                desc = rec.get("short_desc", "")
                val_str = str(rec.get("Value", "")).strip()

                if "(D)" in val_str or "(Z)" in val_str:
                    unavailable.append(desc)
                    continue

                clean_num = re.sub(r"[^\d.]", "", val_str)
                if not clean_num:
                    continue

                val = float(clean_num)

                if desc in ("FARM OPERATIONS - ACRES OPERATED", "AG LAND - ACRES"):
                    if land_in_farms is None or desc == "FARM OPERATIONS - ACRES OPERATED":
                        land_in_farms = val
                elif desc in ("AG LAND, CROPLAND, HARVESTED - ACRES", "AG LAND, CROPLAND - ACRES"):
                    if total_cropland is None or "HARVESTED" in desc:
                        total_cropland = val
                elif desc == "FARM OPERATIONS - NUMBER OF OPERATIONS":
                    farm_count = int(val)
                elif desc in (
                    "FARM OPERATIONS - AREA OPERATED, MEASURED IN ACRES / OPERATION",
                    "FARM OPERATIONS - ACRES / OPERATION",
                ):
                    avg_farm_size = val

            return CountyAgProfile(
                status=IntegrationStatus.SUCCESS,
                state_fips=state_fips,
                county_fips=county_fips,
                county_name=county_name,
                census_year=census_year,
                provenance=provenance,
                land_in_farms_acres=land_in_farms,
                total_cropland_acres=total_cropland,
                farm_count=farm_count,
                average_farm_size_acres=avg_farm_size,
                unavailable_fields=unavailable,
            )

        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning(
                "USDA NASS API request failed for %s (%s%s): %s",
                county_name,
                state_fips,
                county_fips,
                exc,
            )
            return CountyAgProfile(
                status=IntegrationStatus.ERROR,
                state_fips=state_fips,
                county_fips=county_fips,
                county_name=county_name,
                census_year=census_year,
                provenance=provenance,
                error_message=f"USDA NASS query error: {exc}",
            )
