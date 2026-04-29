"""
Geometadata test factories.

Reusable, opinionated builders for ArticleGeometadata and PreprintGeometadata
records with diverse geospatial and temporal coverage. Tests should prefer
calling these helpers over hand-crafting WKT strings, so that:

- the same canonical samples are exercised across the suite,
- adding a new geometry kind only requires extending one place,
- bbox/GeoJSON conversion is implicitly covered for every kind.

Usage::

    from plugins.geometadata.tests import factories

    geo = factories.make_article_geometadata(
        article, kind="polygon", temporal="multi_period",
    )

    for kind in factories.WKT_SAMPLES:
        ...
"""

__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__license__ = "AGPL v3"


# =============================================================================
# WKT samples — one entry per geometry kind we want to exercise in tests.
# =============================================================================
#
# Coordinates are (lng, lat). Selections aim to cover:
#   - all WKT primitives (Point/LineString/Polygon and their Multi forms,
#     plus GeometryCollection),
#   - both hemispheres and the equator,
#   - small (single feature) and large (continental) extents,
#   - polygons with holes and ones near the antimeridian.
WKT_SAMPLES = {
    # Northern hemisphere city
    "point": "POINT(13.4050 52.5200)",
    # Southern hemisphere city
    "point_southern": "POINT(151.2093 -33.8688)",
    # Equatorial point
    "point_equator": "POINT(-78.4678 -0.1807)",
    # Three-segment route Berlin → Paris → Madrid
    "linestring": (
        "LINESTRING(13.4050 52.5200, 2.3522 48.8566, -3.7038 40.4168)"
    ),
    # Continental rectangle covering Europe
    "polygon": "POLYGON((-10 35, 40 35, 40 70, -10 70, -10 35))",
    # Polygon with an interior ring (hole)
    "polygon_with_hole": (
        "POLYGON("
        "(0 0, 10 0, 10 10, 0 10, 0 0),"
        "(2 2, 4 2, 4 4, 2 4, 2 2)"
        ")"
    ),
    # Several capital cities
    "multipoint": (
        "MULTIPOINT("
        "(2.3522 48.8566),"
        "(13.4050 52.5200),"
        "(-0.1276 51.5074),"
        "(12.4964 41.9028)"
        ")"
    ),
    # Two disjoint river segments
    "multilinestring": (
        "MULTILINESTRING("
        "(-90 30, -85 35, -80 38),"
        "(10 50, 12 51, 14 52)"
        ")"
    ),
    # Two non-contiguous islands
    "multipolygon": (
        "MULTIPOLYGON("
        "((-2 50, 2 50, 2 54, -2 54, -2 50)),"
        "((10 60, 16 60, 16 64, 10 64, 10 60))"
        ")"
    ),
    # Mixed feature collection (a coastline and a study site marker)
    "geometrycollection": (
        "GEOMETRYCOLLECTION("
        "POINT(8.5417 47.3769),"
        "LINESTRING(8.5 47.3, 8.6 47.4, 8.7 47.5)"
        ")"
    ),
    # Polygon hugging the antimeridian (intentionally crosses ±180)
    "polygon_antimeridian": (
        "POLYGON((170 -10, -170 -10, -170 10, 170 10, 170 -10))"
    ),
    # Whole-world extent (used for "global coverage" articles)
    "polygon_global": "POLYGON((-180 -90, 180 -90, 180 90, -180 90, -180 -90))",
}


# =============================================================================
# Temporal period samples — one entry per kind of period structure.
# =============================================================================
#
# Each value follows the model's [[start, end], ...] schema where start/end
# are free-text strings. We cover: closed range, open ends, multi-period
# articles, deep-time, named periods, and single-year.
TEMPORAL_SAMPLES = {
    "modern_closed": [["2020-01-01", "2024-12-31"]],
    "open_start": [["", "1900-12-31"]],
    "open_end": [["2020-01-01", ""]],
    "year_only": [["1969", "1972"]],
    "single_year": [["2024", "2024"]],
    "multi_period": [
        ["1990-01-01", "1995-12-31"],
        ["2010-01-01", "2015-12-31"],
    ],
    "deep_time": [["-12000-01-01", "-9000-12-31"]],
    "named_period": [["Holocene", ""]],
    "named_multi": [["Late Pleistocene", "Holocene"]],
    "none": [],
}


# Place names paired with each WKT kind for realistic property values.
PLACE_NAME_FOR_KIND = {
    "point": "Berlin, Germany",
    "point_southern": "Sydney, Australia",
    "point_equator": "Quito, Ecuador",
    "linestring": "Berlin – Paris – Madrid corridor",
    "polygon": "Europe",
    "polygon_with_hole": "Sample region with enclave",
    "multipoint": "European capital cities",
    "multilinestring": "Two river reaches",
    "multipolygon": "Disjoint islands",
    "geometrycollection": "Lake Zurich and shoreline",
    "polygon_antimeridian": "Pacific antimeridian band",
    "polygon_global": "Global coverage",
}


# =============================================================================
# Builders
# =============================================================================


def get_wkt(kind):
    """Return the WKT string for a sample kind.

    Raises KeyError with a helpful message if the kind is unknown so a typo
    in a test fails loudly.
    """
    try:
        return WKT_SAMPLES[kind]
    except KeyError:
        valid = ", ".join(sorted(WKT_SAMPLES))
        raise KeyError(f"Unknown WKT sample kind '{kind}'. Valid: {valid}")


def get_temporal(kind):
    """Return the temporal period list for a sample kind."""
    try:
        return TEMPORAL_SAMPLES[kind]
    except KeyError:
        valid = ", ".join(sorted(TEMPORAL_SAMPLES))
        raise KeyError(f"Unknown temporal sample kind '{kind}'. Valid: {valid}")


def make_article_geometadata(
    article,
    kind="point",
    temporal="modern_closed",
    place_name=None,
    admin_units="",
    **overrides,
):
    """Create an ArticleGeometadata record from a sample kind.

    :param article: target Article (must not already have a geometadata record)
    :param kind: key into WKT_SAMPLES, or None for no geometry
    :param temporal: key into TEMPORAL_SAMPLES, or None for no temporal data
    :param place_name: human-readable label; defaults to a sample for the kind
    :param admin_units: admin unit string
    :param overrides: any field overrides for ArticleGeometadata
    :return: persisted ArticleGeometadata
    """
    from plugins.geometadata.models import ArticleGeometadata

    if place_name is None and kind is not None:
        place_name = PLACE_NAME_FOR_KIND.get(kind, "")

    fields = {
        "article": article,
        "geometry_wkt": get_wkt(kind) if kind else "",
        "place_name": place_name or "",
        "admin_units": admin_units,
        "temporal_periods": get_temporal(temporal) if temporal else [],
    }
    fields.update(overrides)
    return ArticleGeometadata.objects.create(**fields)


def make_preprint_geometadata(
    preprint,
    kind="point",
    temporal="modern_closed",
    place_name=None,
    admin_units="",
    **overrides,
):
    """Create a PreprintGeometadata record from a sample kind.

    Mirrors :func:`make_article_geometadata` for the Preprint relation.
    """
    from plugins.geometadata.models import PreprintGeometadata

    if place_name is None and kind is not None:
        place_name = PLACE_NAME_FOR_KIND.get(kind, "")

    fields = {
        "preprint": preprint,
        "geometry_wkt": get_wkt(kind) if kind else "",
        "place_name": place_name or "",
        "admin_units": admin_units,
        "temporal_periods": get_temporal(temporal) if temporal else [],
    }
    fields.update(overrides)
    return PreprintGeometadata.objects.create(**fields)


def iter_kinds(exclude=()):
    """Yield (kind, wkt) for every sample, optionally skipping some kinds.

    Useful for parametrised tests that should cover every geometry type::

        for kind, _ in factories.iter_kinds():
            with self.subTest(kind=kind):
                ...
    """
    for kind, wkt in WKT_SAMPLES.items():
        if kind in exclude:
            continue
        yield kind, wkt
