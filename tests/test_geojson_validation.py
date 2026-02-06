"""
Tests for GeoJSON validation using geojson-validator.

Validates that all generated GeoJSON outputs conform to the GeoJSON specification
(RFC 7946) including proper geometry types, coordinate structures, and
FeatureCollection format.

Requires: pip install geojson-validator>=0.6
Tests are skipped if geojson-validator is not installed.
"""

import unittest

from django.test import override_settings

try:
    from geojson_validator import validate_structure

    HAS_GEOJSON_VALIDATOR = True
except ImportError:
    HAS_GEOJSON_VALIDATOR = False
    validate_structure = None

from plugins.geometadata.models import ArticleGeometadata
from plugins.geometadata.tests.base import GeometadataTestCase
from utils.testing import helpers


requires_geojson_validator = unittest.skipUnless(
    HAS_GEOJSON_VALIDATOR,
    "geojson-validator not installed (pip install geojson-validator>=0.6)",
)


@override_settings(
    URL_CONFIG="domain",
    ROOT_URLCONF="plugins.geometadata.tests.urls",
)
class GeoJSONValidationTestCase(GeometadataTestCase):
    """Base test case with geometadata fixtures for GeoJSON validation."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Create geometadata with Point geometry
        cls.geometadata_point = ArticleGeometadata.objects.create(
            article=cls.article,
            geometry_wkt="POINT(13.4 52.5)",
            place_name="Berlin",
            admin_units="Berlin, Germany",
            temporal_periods=[["2020-01-01", "2021-12-31"]],
        )

        # Create second article with Polygon geometry
        cls.article_polygon = helpers.create_article(cls.journal, with_author=True)
        cls.article_polygon.stage = "Published"
        cls.article_polygon.date_published = "2024-01-15"
        cls.article_polygon.save()

        cls.geometadata_polygon = ArticleGeometadata.objects.create(
            article=cls.article_polygon,
            geometry_wkt="POLYGON((10 50, 15 50, 15 55, 10 55, 10 50))",
            place_name="Central Europe",
            admin_units="Germany, Poland, Czech Republic",
        )

        # Create issue with both articles
        cls.issue = helpers.create_issue(
            cls.journal,
            vol=1,
            number=1,
            articles=[cls.article, cls.article_polygon],
        )


@requires_geojson_validator
class ArticleGeoJSONValidationTests(GeoJSONValidationTestCase):
    """Tests for article-level GeoJSON download validation."""

    def test_article_geojson_point_is_valid(self):
        """Article GeoJSON with Point geometry passes validation."""
        response = self.client.get(
            f"/plugins/geometadata/download/article/{self.article.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        geojson = response.json()

        # Validate with geojson-validator
        result = validate_structure(geojson)
        self.assertEqual(
            result,
            {},
            f"GeoJSON validation failed: {result}",
        )

    def test_article_geojson_polygon_is_valid(self):
        """Article GeoJSON with Polygon geometry passes validation."""
        response = self.client.get(
            f"/plugins/geometadata/download/article/{self.article_polygon.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        geojson = response.json()

        result = validate_structure(geojson)
        self.assertEqual(
            result,
            {},
            f"GeoJSON validation failed: {result}",
        )

    def test_article_geojson_is_feature_collection(self):
        """Article GeoJSON download is a FeatureCollection."""
        response = self.client.get(
            f"/plugins/geometadata/download/article/{self.article.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        geojson = response.json()

        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertIn("features", geojson)
        self.assertIsInstance(geojson["features"], list)

    def test_article_geojson_has_correct_feature_count(self):
        """Article GeoJSON contains exactly one feature."""
        response = self.client.get(
            f"/plugins/geometadata/download/article/{self.article.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        geojson = response.json()

        self.assertEqual(len(geojson["features"]), 1)

    def test_article_geojson_feature_has_valid_geometry(self):
        """Article GeoJSON feature has valid geometry structure."""
        response = self.client.get(
            f"/plugins/geometadata/download/article/{self.article.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        geojson = response.json()

        feature = geojson["features"][0]
        self.assertEqual(feature["type"], "Feature")
        self.assertIn("geometry", feature)
        self.assertIn("type", feature["geometry"])
        self.assertIn("coordinates", feature["geometry"])

    def test_article_geojson_point_coordinates(self):
        """Article GeoJSON Point has correct coordinate structure [lon, lat]."""
        response = self.client.get(
            f"/plugins/geometadata/download/article/{self.article.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        geojson = response.json()

        geometry = geojson["features"][0]["geometry"]
        self.assertEqual(geometry["type"], "Point")
        self.assertEqual(len(geometry["coordinates"]), 2)
        # Coordinates are [longitude, latitude]
        self.assertAlmostEqual(geometry["coordinates"][0], 13.4, places=5)
        self.assertAlmostEqual(geometry["coordinates"][1], 52.5, places=5)

    def test_article_geojson_polygon_coordinates(self):
        """Article GeoJSON Polygon has correct coordinate ring structure."""
        response = self.client.get(
            f"/plugins/geometadata/download/article/{self.article_polygon.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        geojson = response.json()

        geometry = geojson["features"][0]["geometry"]
        self.assertEqual(geometry["type"], "Polygon")
        # Polygon has array of rings, each ring is array of positions
        self.assertIsInstance(geometry["coordinates"], list)
        self.assertGreater(len(geometry["coordinates"]), 0)
        # First ring (exterior)
        ring = geometry["coordinates"][0]
        self.assertIsInstance(ring, list)
        # Ring should be closed (first == last point)
        self.assertEqual(ring[0], ring[-1])


@requires_geojson_validator
class IssueGeoJSONValidationTests(GeoJSONValidationTestCase):
    """Tests for issue-level GeoJSON download validation."""

    def test_issue_geojson_is_valid(self):
        """Issue GeoJSON passes validation."""
        response = self.client.get(
            f"/plugins/geometadata/download/issue/{self.issue.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        geojson = response.json()

        result = validate_structure(geojson)
        self.assertEqual(
            result,
            {},
            f"GeoJSON validation failed: {result}",
        )

    def test_issue_geojson_is_feature_collection(self):
        """Issue GeoJSON download is a FeatureCollection."""
        response = self.client.get(
            f"/plugins/geometadata/download/issue/{self.issue.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        geojson = response.json()

        self.assertEqual(geojson["type"], "FeatureCollection")

    def test_issue_geojson_has_correct_feature_count(self):
        """Issue GeoJSON contains features for all articles with geometadata."""
        response = self.client.get(
            f"/plugins/geometadata/download/issue/{self.issue.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        geojson = response.json()

        # Issue has 2 articles with geometadata
        self.assertEqual(len(geojson["features"]), 2)

    def test_issue_geojson_all_features_valid(self):
        """All features in issue GeoJSON have valid structure."""
        response = self.client.get(
            f"/plugins/geometadata/download/issue/{self.issue.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        geojson = response.json()

        for i, feature in enumerate(geojson["features"]):
            self.assertEqual(feature["type"], "Feature", f"Feature {i} has wrong type")
            self.assertIn("geometry", feature, f"Feature {i} missing geometry")
            self.assertIn("properties", feature, f"Feature {i} missing properties")
            self.assertIn(
                "type", feature["geometry"], f"Feature {i} geometry missing type"
            )
            self.assertIn(
                "coordinates",
                feature["geometry"],
                f"Feature {i} geometry missing coordinates",
            )


@requires_geojson_validator
class JournalGeoJSONValidationTests(GeoJSONValidationTestCase):
    """Tests for journal-level GeoJSON download validation."""

    def test_journal_geojson_is_valid(self):
        """Journal GeoJSON passes validation."""
        response = self.client.get(
            "/plugins/geometadata/download/journal/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        geojson = response.json()

        result = validate_structure(geojson)
        self.assertEqual(
            result,
            {},
            f"GeoJSON validation failed: {result}",
        )

    def test_journal_geojson_is_feature_collection(self):
        """Journal GeoJSON download is a FeatureCollection."""
        response = self.client.get(
            "/plugins/geometadata/download/journal/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        geojson = response.json()

        self.assertEqual(geojson["type"], "FeatureCollection")

    def test_journal_geojson_has_correct_feature_count(self):
        """Journal GeoJSON contains features for all articles with geometadata."""
        response = self.client.get(
            "/plugins/geometadata/download/journal/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        geojson = response.json()

        # Journal has 2 articles with geometadata
        self.assertEqual(len(geojson["features"]), 2)

    def test_journal_geojson_mixed_geometry_types(self):
        """Journal GeoJSON can contain multiple geometry types."""
        response = self.client.get(
            "/plugins/geometadata/download/journal/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        geojson = response.json()

        geometry_types = {f["geometry"]["type"] for f in geojson["features"]}

        # Should have both Point and Polygon
        self.assertIn("Point", geometry_types)
        self.assertIn("Polygon", geometry_types)


@requires_geojson_validator
class APIGeoJSONValidationTests(GeoJSONValidationTestCase):
    """Tests for GeoJSON API endpoint validation."""

    def test_article_api_geojson_is_valid(self):
        """Article API returns valid GeoJSON."""
        response = self.client.get(
            f"/plugins/geometadata/api/article/{self.article.pk}/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        geojson = response.json()

        result = validate_structure(geojson)
        self.assertEqual(
            result,
            {},
            f"GeoJSON validation failed: {result}",
        )

    def test_article_api_returns_feature(self):
        """Article API returns a single Feature (not FeatureCollection)."""
        response = self.client.get(
            f"/plugins/geometadata/api/article/{self.article.pk}/",
            SERVER_NAME=self.journal.domain,
        )
        geojson = response.json()

        self.assertEqual(geojson["type"], "Feature")

    def test_all_api_geojson_is_valid(self):
        """All-articles API returns valid GeoJSON."""
        response = self.client.get(
            "/plugins/geometadata/api/all/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        geojson = response.json()

        result = validate_structure(geojson)
        self.assertEqual(
            result,
            {},
            f"GeoJSON validation failed: {result}",
        )

    def test_issue_api_geojson_is_valid(self):
        """Issue API returns valid GeoJSON."""
        response = self.client.get(
            f"/plugins/geometadata/api/issue/{self.issue.pk}/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        geojson = response.json()

        result = validate_structure(geojson)
        self.assertEqual(
            result,
            {},
            f"GeoJSON validation failed: {result}",
        )

    def test_press_api_geojson_is_valid(self):
        """Press API returns valid GeoJSON."""
        response = self.client.get(
            "/plugins/geometadata/api/press/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        geojson = response.json()

        result = validate_structure(geojson)
        self.assertEqual(
            result,
            {},
            f"GeoJSON validation failed: {result}",
        )

    def test_api_feature_collection_has_features_array(self):
        """API FeatureCollections have a features array."""
        response = self.client.get(
            "/plugins/geometadata/api/all/",
            SERVER_NAME=self.journal.domain,
        )
        geojson = response.json()

        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertIn("features", geojson)
        self.assertIsInstance(geojson["features"], list)
