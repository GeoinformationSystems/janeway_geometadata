"""
Tests for geometadata models.

Tests WKT parsing, bounding box calculation, GeoJSON conversion,
and temporal display formatting.
"""

from plugins.geometadata.models import ArticleGeometadata
from plugins.geometadata.tests.base import GeometadataTestCase


class ArticleGeometadataTests(GeometadataTestCase):
    """Tests for ArticleGeometadata model functionality."""

    def test_bbox_from_point(self):
        """Point WKT sets bbox to single coordinate."""
        geo = ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10.5 52.3)",
        )
        self.assertEqual(geo.bbox_north, 52.3)
        self.assertEqual(geo.bbox_south, 52.3)
        self.assertEqual(geo.bbox_east, 10.5)
        self.assertEqual(geo.bbox_west, 10.5)

    def test_bbox_from_polygon(self):
        """Polygon WKT sets bbox to geometry extents."""
        geo = ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POLYGON((-10 35, 40 35, 40 70, -10 70, -10 35))",
        )
        self.assertEqual(geo.bbox_north, 70)
        self.assertEqual(geo.bbox_south, 35)
        self.assertEqual(geo.bbox_east, 40)
        self.assertEqual(geo.bbox_west, -10)

    def test_bbox_cleared_when_wkt_empty(self):
        """Empty WKT clears all bbox fields."""
        geo = ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10 50)",
        )
        self.assertIsNotNone(geo.bbox_north)

        geo.geometry_wkt = ""
        geo.save()

        self.assertIsNone(geo.bbox_north)
        self.assertIsNone(geo.bbox_south)
        self.assertIsNone(geo.bbox_east)
        self.assertIsNone(geo.bbox_west)

    def test_bbox_invalid_wkt_handled(self):
        """Malformed WKT sets bbox fields to None without raising."""
        geo = ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="NOT_VALID_WKT",
        )
        self.assertIsNone(geo.bbox_north)
        self.assertIsNone(geo.bbox_south)

    def test_to_geojson_point(self):
        """Point WKT converts to valid GeoJSON Feature."""
        geo = ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10.5 52.3)",
        )
        geojson = geo.to_geojson()

        self.assertEqual(geojson["type"], "Feature")
        self.assertEqual(geojson["geometry"]["type"], "Point")
        self.assertEqual(geojson["geometry"]["coordinates"], [10.5, 52.3])

    def test_to_geojson_polygon_with_properties(self):
        """Polygon WKT converts to GeoJSON with place_name in properties."""
        geo = ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POLYGON((-10 35, 40 35, 40 70, -10 70, -10 35))",
            place_name="Europe",
            temporal_periods=[["2020", "2021"]],
        )
        geojson = geo.to_geojson()

        self.assertEqual(geojson["geometry"]["type"], "Polygon")
        self.assertEqual(geojson["properties"]["place_name"], "Europe")
        self.assertEqual(geojson["properties"]["temporal_periods"], [["2020", "2021"]])

    def test_to_geojson_empty_returns_none(self):
        """Empty geometry returns None instead of invalid GeoJSON."""
        geo = ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="",
        )
        self.assertIsNone(geo.to_geojson())

    def test_temporal_display_single_period(self):
        """Full date range formats as 'start – end'."""
        geo = ArticleGeometadata.objects.create(
            article=self.article,
            temporal_periods=[["2020-01-15", "2021-06-30"]],
        )
        display = geo.get_temporal_display()

        self.assertEqual(len(display), 1)
        self.assertIn("2020-01-15", display[0])
        self.assertIn("2021-06-30", display[0])

    def test_temporal_display_open_ended(self):
        """Open-ended period with only start date."""
        geo = ArticleGeometadata.objects.create(
            article=self.article,
            temporal_periods=[["2020-01", ""]],
        )
        display = geo.get_temporal_display()

        self.assertEqual(len(display), 1)
        self.assertIn("2020-01", display[0])

    def test_has_spatial_data(self):
        """has_spatial_data returns True only when geometry_wkt is set."""
        geo = ArticleGeometadata.objects.create(article=self.article)
        self.assertFalse(geo.has_spatial_data())

        geo.geometry_wkt = "POINT(10 50)"
        geo.save()
        self.assertTrue(geo.has_spatial_data())

    def test_has_temporal_data(self):
        """has_temporal_data returns True only when temporal_periods is set."""
        geo = ArticleGeometadata.objects.create(article=self.article)
        self.assertFalse(geo.has_temporal_data())

        geo.temporal_periods = [["2020", "2021"]]
        geo.save()
        self.assertTrue(geo.has_temporal_data())
