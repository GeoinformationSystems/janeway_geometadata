__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__author__ = "Daniel Nüst & KOMET Team"
__license__ = "AGPL v3"

import re

from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import GeoNames, Nominatim, Photon

from utils.logger import get_logger

logger = get_logger(__name__)

PROVIDERS = {
    "nominatim": Nominatim,
    "geonames": GeoNames,
    "photon": Photon,
}


class GeocodingService:
    """Reverse-geocodes WKT geometries via geopy."""

    def __init__(
        self,
        provider="nominatim",
        user_agent="janeway-geometadata",
        geonames_username="",
    ):
        provider = provider.lower()
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown geocoding provider: {provider}")

        kwargs = {}
        if provider == "nominatim":
            kwargs["user_agent"] = user_agent
        elif provider == "geonames":
            if not geonames_username:
                raise ValueError(
                    "GeoNames requires a username. "
                    "Register at https://www.geonames.org/login"
                )
            kwargs["username"] = geonames_username
        elif provider == "photon":
            kwargs["user_agent"] = user_agent

        self.geocoder = PROVIDERS[provider](**kwargs)
        self.reverse = RateLimiter(self.geocoder.reverse, min_delay_seconds=1.1)

    def extract_coordinates_from_wkt(self, wkt):
        """Extract deduplicated (lat, lng) pairs from a WKT string.

        WKT uses lng-lat order; this method flips to lat-lng for geopy.
        """
        pairs = re.findall(r"(-?\d+\.?\d*)\s+(-?\d+\.?\d*)", wkt)
        seen = set()
        coords = []
        for lng_str, lat_str in pairs:
            lng = float(lng_str)
            lat = float(lat_str)
            key = (lat, lng)
            if key not in seen:
                seen.add(key)
                coords.append((lat, lng))
        return coords

    def reverse_geocode_coordinates(self, coords, max_points=10):
        """Reverse-geocode a list of (lat, lng) pairs.

        Samples evenly if more than *max_points* coordinates.
        Returns a list of geopy Location objects (None entries filtered out).
        """
        if len(coords) > max_points:
            coords = self._sample_coordinates(coords, max_points)

        results = []
        for lat, lng in coords:
            try:
                result = self.reverse((lat, lng), exactly_one=True, language="en")
                if result:
                    results.append(result)
            except Exception:
                logger.debug("Reverse geocoding failed for (%s, %s)", lat, lng)
        return results

    def find_common_location_description(self, results):
        """Derive a common place_name and admin_units from geocoded results.

        Returns ``{"place_name": "...", "admin_units": "..."}``.
        """
        if not results:
            return {"place_name": "", "admin_units": ""}

        hierarchies = []
        for result in results:
            hierarchy = self._extract_admin_hierarchy(result)
            if hierarchy:
                hierarchies.append(hierarchy)

        if not hierarchies:
            return {"place_name": "", "admin_units": ""}

        if len(hierarchies) == 1:
            h = hierarchies[0]
            return {
                "place_name": ", ".join(h),
                "admin_units": ", ".join(h),
            }

        common = self._find_common_suffix(hierarchies)
        place_name = ", ".join(common) if common else ""
        admin_units = ", ".join(common) if common else ""
        return {"place_name": place_name, "admin_units": admin_units}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sample_coordinates(coords, max_points):
        """Return an evenly-spaced sample including first and last."""
        if len(coords) <= max_points:
            return coords
        indices = set()
        indices.add(0)
        indices.add(len(coords) - 1)
        step = (len(coords) - 1) / (max_points - 1)
        for i in range(1, max_points - 1):
            indices.add(round(i * step))
        return [coords[i] for i in sorted(indices)]

    @staticmethod
    def _extract_admin_hierarchy(result):
        """Extract [city, state, country] from a geopy Location's raw dict."""
        raw = getattr(result, "raw", {}) or {}

        # Nominatim / Photon store address info under "address"
        address = raw.get("address", {})
        if not address:
            # GeoNames uses a flat structure
            parts = []
            for key in ("name", "adminName1", "countryName"):
                val = raw.get(key)
                if val:
                    parts.append(val)
            return parts if parts else None

        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("county")
        )
        state = address.get("state") or address.get("region") or address.get("province")
        country = address.get("country")

        parts = [p for p in [city, state, country] if p]
        return parts if parts else None

    @staticmethod
    def _find_common_suffix(hierarchies):
        """Find the longest common suffix across lists of strings."""
        if not hierarchies:
            return []
        reversed_lists = [list(reversed(h)) for h in hierarchies]
        common = []
        for items in zip(*reversed_lists):
            if len(set(items)) == 1:
                common.append(items[0])
            else:
                break
        return list(reversed(common))


def reverse_geocode_wkt(
    wkt,
    provider="nominatim",
    user_agent="janeway-geometadata",
    geonames_username="",
    max_points=10,
):
    """Convenience function: reverse-geocode a WKT string.

    Returns ``{"place_name": "...", "admin_units": "..."}``.
    """
    service = GeocodingService(
        provider=provider,
        user_agent=user_agent,
        geonames_username=geonames_username,
    )
    coords = service.extract_coordinates_from_wkt(wkt)
    if not coords:
        return {"place_name": "", "admin_units": ""}
    results = service.reverse_geocode_coordinates(coords, max_points=max_points)
    return service.find_common_location_description(results)
