__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__author__ = "Daniel Nüst & KOMET Team"
__license__ = "AGPL v3"

from django.db import models
from django.utils.translation import gettext_lazy as _


class AbstractGeometadata(models.Model):
    """
    Abstract base model for geospatial and temporal metadata.

    Geometry is stored as Well-Known Text (WKT) format, which is a standard
    text representation of geometry objects. This allows storage without
    requiring GeoDjango/PostGIS while remaining interoperable.

    Supported WKT geometry types:
    - POINT(lng lat)
    - LINESTRING(lng1 lat1, lng2 lat2, ...)
    - POLYGON((lng1 lat1, lng2 lat2, ..., lng1 lat1))
    - MULTIPOINT, MULTILINESTRING, MULTIPOLYGON
    - GEOMETRYCOLLECTION

    Example: POLYGON((-10 35, 40 35, 40 70, -10 70, -10 35))
    """

    # Spatial metadata
    geometry_wkt = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Geometry (WKT)"),
        help_text=_(
            "Geographic coverage in Well-Known Text (WKT) format. "
            "Example: POLYGON((-10 35, 40 35, 40 70, -10 70, -10 35))"
        ),
    )

    # Bounding box for quick spatial queries (extracted from geometry)
    bbox_north = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_("Bounding Box North"),
        help_text=_("Northern latitude boundary (-90 to 90)"),
    )
    bbox_south = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_("Bounding Box South"),
        help_text=_("Southern latitude boundary (-90 to 90)"),
    )
    bbox_east = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_("Bounding Box East"),
        help_text=_("Eastern longitude boundary (-180 to 180)"),
    )
    bbox_west = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_("Bounding Box West"),
        help_text=_("Western longitude boundary (-180 to 180)"),
    )

    # Human-readable place name(s)
    place_name = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("Place Name"),
        help_text=_(
            "Human-readable name(s) of the location(s), e.g., "
            "'Vienna, Austria' or 'North Atlantic Ocean'"
        ),
    )

    # Administrative units for machine-readable coverage
    # Comma-separated list of standardized names
    admin_units = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Administrative Units"),
        help_text=_(
            "Comma-separated list of administrative units covering this geometry, "
            "e.g., 'Austria, Vienna, Wien Stadt'"
        ),
    )

    # Temporal metadata — list of [start, end] text pairs stored as JSON
    temporal_periods = models.JSONField(
        blank=True,
        default=list,
        verbose_name=_("Temporal Periods"),
        help_text=_(
            "List of time periods, each as [start, end] text pairs. "
            'Example: [["2020-01", "2021-06"], ["Holocene", ""]]'
        ),
    )

    # Metadata about the metadata
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        indexes = [
            # Composite index for spatial bounding box overlap queries
            models.Index(
                fields=["bbox_south", "bbox_north", "bbox_west", "bbox_east"],
                name="%(class)s_bbox_idx",
            ),
        ]

    def has_spatial_data(self):
        """Return True if this record has spatial metadata."""
        return bool(self.geometry_wkt or self.place_name)

    def has_temporal_data(self):
        """Return True if this record has temporal metadata."""
        return bool(self.temporal_periods)

    def get_temporal_display(self):
        """Return a list of formatted period strings for display.

        Each period is rendered as "start – end", or just "start" / "end"
        when one bound is empty.
        """
        result = []
        for period in self.temporal_periods or []:
            start = period[0].strip() if period[0] else ""
            end = period[1].strip() if period[1] else ""
            if start and end:
                result.append(f"{start} – {end}")
            elif start:
                result.append(start)
            elif end:
                result.append(end)
        return result

    def get_geometry_type(self):
        """Extract geometry type from WKT string."""
        if not self.geometry_wkt:
            return None
        wkt = self.geometry_wkt.strip().upper()
        for gtype in [
            "GEOMETRYCOLLECTION",
            "MULTIPOLYGON",
            "MULTILINESTRING",
            "MULTIPOINT",
            "POLYGON",
            "LINESTRING",
            "POINT",
        ]:
            if wkt.startswith(gtype):
                return gtype
        return None

    def get_centroid(self):
        """
        Calculate approximate centroid from bounding box.
        Returns (lat, lng) tuple or None.
        """
        if all(
            v is not None
            for v in [self.bbox_north, self.bbox_south, self.bbox_east, self.bbox_west]
        ):
            lat = (self.bbox_north + self.bbox_south) / 2
            lng = (self.bbox_east + self.bbox_west) / 2
            return (lat, lng)
        return None

    def update_bbox_from_wkt(self):
        """
        Parse WKT and update bounding box fields.
        This is a simple parser that extracts coordinates from WKT.
        """
        if not self.geometry_wkt:
            self.bbox_north = None
            self.bbox_south = None
            self.bbox_east = None
            self.bbox_west = None
            return

        import re

        # Extract all coordinate pairs (lng lat) from WKT
        # Match patterns like: -10.5 35.2 or -10 35
        coord_pattern = r"(-?\d+\.?\d*)\s+(-?\d+\.?\d*)"
        matches = re.findall(coord_pattern, self.geometry_wkt)

        if not matches:
            return

        lngs = []
        lats = []
        for lng_str, lat_str in matches:
            try:
                lng = float(lng_str)
                lat = float(lat_str)
                # Validate coordinate ranges
                if -180 <= lng <= 180 and -90 <= lat <= 90:
                    lngs.append(lng)
                    lats.append(lat)
            except ValueError:
                continue

        if lngs and lats:
            self.bbox_north = max(lats)
            self.bbox_south = min(lats)
            self.bbox_east = max(lngs)
            self.bbox_west = min(lngs)

    def save(self, *args, **kwargs):
        """Update bounding box before saving."""
        self.update_bbox_from_wkt()
        super().save(*args, **kwargs)

    def to_geojson(self):
        """
        Convert geometry to GeoJSON format for use with Leaflet.
        Returns a GeoJSON Feature dict or None.
        """
        if not self.geometry_wkt:
            return None

        try:
            geometry = self._wkt_to_geojson_geometry()
            if geometry:
                return {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "place_name": self.place_name or "",
                        "temporal_periods": self.temporal_periods or [],
                    },
                }
        except Exception:
            pass
        return None

    def _wkt_to_geojson_geometry(self):
        """
        Convert WKT string to GeoJSON geometry object.
        This is a simplified parser for common geometry types.
        """
        import re

        if not self.geometry_wkt:
            return None

        wkt = self.geometry_wkt.strip()
        gtype = self.get_geometry_type()

        if not gtype:
            return None

        # Extract coordinates part (everything in parentheses)
        coord_match = re.search(r"\((.+)\)$", wkt, re.DOTALL)
        if not coord_match:
            return None

        coords_str = coord_match.group(1)

        if gtype == "POINT":
            # POINT(lng lat)
            parts = coords_str.strip().split()
            if len(parts) >= 2:
                return {
                    "type": "Point",
                    "coordinates": [float(parts[0]), float(parts[1])],
                }

        elif gtype == "LINESTRING":
            # LINESTRING(lng1 lat1, lng2 lat2, ...)
            coords = self._parse_coord_sequence(coords_str)
            if coords:
                return {"type": "LineString", "coordinates": coords}

        elif gtype == "POLYGON":
            # POLYGON((lng1 lat1, lng2 lat2, ..., lng1 lat1))
            # Can have multiple rings (outer + holes)
            rings = self._parse_polygon_rings(coords_str)
            if rings:
                return {"type": "Polygon", "coordinates": rings}

        elif gtype == "MULTIPOINT":
            coords = self._parse_coord_sequence(coords_str)
            if coords:
                return {"type": "MultiPoint", "coordinates": coords}

        elif gtype == "MULTILINESTRING":
            lines = self._parse_multi_sequence(coords_str)
            if lines:
                return {"type": "MultiLineString", "coordinates": lines}

        elif gtype == "MULTIPOLYGON":
            polygons = self._parse_multipolygon(coords_str)
            if polygons:
                return {"type": "MultiPolygon", "coordinates": polygons}

        elif gtype == "GEOMETRYCOLLECTION":
            geometries = self._parse_geometry_collection(coords_str)
            if geometries:
                return {"type": "GeometryCollection", "geometries": geometries}

        return None

    def _parse_coord_sequence(self, coords_str):
        """Parse a sequence of coordinates like 'lng1 lat1, lng2 lat2'."""
        coords = []
        for pair in coords_str.split(","):
            parts = pair.strip().split()
            if len(parts) >= 2:
                try:
                    coords.append([float(parts[0]), float(parts[1])])
                except ValueError:
                    continue
        return coords if coords else None

    def _parse_polygon_rings(self, coords_str):
        """Parse polygon rings from WKT format."""
        import re

        rings = []
        # Match each ring: (lng1 lat1, lng2 lat2, ...)
        ring_pattern = r"\(([^()]+)\)"
        for match in re.finditer(ring_pattern, coords_str):
            ring_coords = self._parse_coord_sequence(match.group(1))
            if ring_coords:
                rings.append(ring_coords)
        return rings if rings else None

    def _parse_multi_sequence(self, coords_str):
        """Parse multiple coordinate sequences."""
        import re

        sequences = []
        # Match each sequence in parentheses
        seq_pattern = r"\(([^()]+)\)"
        for match in re.finditer(seq_pattern, coords_str):
            seq = self._parse_coord_sequence(match.group(1))
            if seq:
                sequences.append(seq)
        return sequences if sequences else None

    def _parse_multipolygon(self, coords_str):
        """Parse multipolygon from WKT format."""
        import re

        polygons = []
        # Match each polygon: ((ring1), (ring2), ...)
        # This is a simplified approach
        poly_pattern = r"\(\(([^)]+(?:\),[^)]+)*)\)\)"
        for match in re.finditer(poly_pattern, coords_str):
            rings = self._parse_polygon_rings("(" + match.group(1) + ")")
            if rings:
                polygons.append(rings)
        return polygons if polygons else None

    def _parse_geometry_collection(self, coords_str):
        """
        Parse a GEOMETRYCOLLECTION from WKT format.

        GEOMETRYCOLLECTION contains multiple geometries of different types.
        We parse each sub-geometry and convert it to GeoJSON.
        """
        import re

        geometries = []
        # Pattern to match each geometry type with its content
        # Handles nested parentheses by matching balanced groups
        geometry_types = [
            "MULTIPOLYGON",
            "MULTILINESTRING",
            "MULTIPOINT",
            "POLYGON",
            "LINESTRING",
            "POINT",
        ]
        pattern = (
            r"(" + "|".join(geometry_types) + r")\s*(\([^()]*(?:\([^()]*\)[^()]*)*\))"
        )

        for match in re.finditer(pattern, coords_str, re.IGNORECASE):
            gtype = match.group(1).upper()
            content = match.group(2)

            # Create a temporary WKT string and parse it
            temp_wkt = f"{gtype}{content}"
            geom = self._parse_single_geometry(temp_wkt)
            if geom:
                geometries.append(geom)

        return geometries if geometries else None

    def _parse_single_geometry(self, wkt_str):
        """
        Parse a single geometry WKT string to GeoJSON.
        Helper for GEOMETRYCOLLECTION parsing.
        """
        import re

        wkt = wkt_str.strip().upper()

        for gtype in [
            "MULTIPOLYGON",
            "MULTILINESTRING",
            "MULTIPOINT",
            "POLYGON",
            "LINESTRING",
            "POINT",
        ]:
            if wkt.startswith(gtype):
                coord_match = re.search(r"\((.+)\)$", wkt_str, re.DOTALL)
                if not coord_match:
                    return None
                coords_str = coord_match.group(1)

                if gtype == "POINT":
                    parts = coords_str.strip().split()
                    if len(parts) >= 2:
                        return {
                            "type": "Point",
                            "coordinates": [float(parts[0]), float(parts[1])],
                        }

                elif gtype == "LINESTRING":
                    coords = self._parse_coord_sequence(coords_str)
                    if coords:
                        return {"type": "LineString", "coordinates": coords}

                elif gtype == "POLYGON":
                    rings = self._parse_polygon_rings(coords_str)
                    if rings:
                        return {"type": "Polygon", "coordinates": rings}

                elif gtype == "MULTIPOINT":
                    coords = self._parse_coord_sequence(coords_str)
                    if coords:
                        return {"type": "MultiPoint", "coordinates": coords}

                elif gtype == "MULTILINESTRING":
                    lines = self._parse_multi_sequence(coords_str)
                    if lines:
                        return {"type": "MultiLineString", "coordinates": lines}

                elif gtype == "MULTIPOLYGON":
                    polygons = self._parse_multipolygon(coords_str)
                    if polygons:
                        return {"type": "MultiPolygon", "coordinates": polygons}

        return None


class ArticleGeometadata(AbstractGeometadata):
    """
    Geospatial and temporal metadata for journal articles.
    """

    article = models.OneToOneField(
        "submission.Article",
        on_delete=models.CASCADE,
        related_name="geometadata",
        verbose_name=_("Article"),
    )

    class Meta:
        verbose_name = _("Article Geometadata")
        verbose_name_plural = _("Article Geometadata")

    def __str__(self):
        return f"Geometadata for Article {self.article.pk}"


class PreprintGeometadata(AbstractGeometadata):
    """
    Geospatial and temporal metadata for repository preprints.
    """

    preprint = models.OneToOneField(
        "repository.Preprint",
        on_delete=models.CASCADE,
        related_name="geometadata",
        verbose_name=_("Preprint"),
    )

    class Meta:
        verbose_name = _("Preprint Geometadata")
        verbose_name_plural = _("Preprint Geometadata")

    def __str__(self):
        return f"Geometadata for Preprint {self.preprint.pk}"
