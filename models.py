__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__author__ = "Daniel Nüst & KOMET Team"
__license__ = "AGPL v3"

from django.db import models
from django.utils.translation import gettext_lazy as _

from geomet import wkt as geomet_wkt


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
        Parse WKT and update bounding box fields using the geomet library.
        """
        if not self.geometry_wkt:
            self.bbox_north = None
            self.bbox_south = None
            self.bbox_east = None
            self.bbox_west = None
            return

        try:
            geometry = geomet_wkt.loads(self.geometry_wkt)
            coords = self._extract_all_coordinates(geometry)

            if coords:
                lngs = [c[0] for c in coords if -180 <= c[0] <= 180]
                lats = [c[1] for c in coords if -90 <= c[1] <= 90]

                if lngs and lats:
                    self.bbox_north = max(lats)
                    self.bbox_south = min(lats)
                    self.bbox_east = max(lngs)
                    self.bbox_west = min(lngs)
        except Exception:
            # If parsing fails, clear bbox fields
            self.bbox_north = None
            self.bbox_south = None
            self.bbox_east = None
            self.bbox_west = None

    def _extract_all_coordinates(self, geometry):
        """
        Recursively extract all coordinate pairs from a GeoJSON geometry.
        Returns a flat list of [lng, lat] pairs.
        """
        coords = []
        geom_type = geometry.get("type")

        if geom_type == "Point":
            coords.append(geometry["coordinates"][:2])
        elif geom_type in ("LineString", "MultiPoint"):
            for coord in geometry["coordinates"]:
                coords.append(coord[:2])
        elif geom_type in ("Polygon", "MultiLineString"):
            for ring in geometry["coordinates"]:
                for coord in ring:
                    coords.append(coord[:2])
        elif geom_type == "MultiPolygon":
            for polygon in geometry["coordinates"]:
                for ring in polygon:
                    for coord in ring:
                        coords.append(coord[:2])
        elif geom_type == "GeometryCollection":
            for geom in geometry.get("geometries", []):
                coords.extend(self._extract_all_coordinates(geom))

        return coords

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
            geometry = geomet_wkt.loads(self.geometry_wkt)
            return {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "place_name": self.place_name or "",
                    "temporal_periods": self.temporal_periods or [],
                },
            }
        except Exception:
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
