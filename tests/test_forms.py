"""
Tests for geometadata forms.

Tests WKT validation and temporal period format validation.
"""

from django.test import TestCase

from plugins.geometadata.forms import ArticleGeometadataForm


class ArticleGeometadataFormTests(TestCase):
    """Tests for ArticleGeometadataForm validation."""

    def test_valid_wkt_accepted(self):
        """Valid WKT geometry passes validation."""
        form = ArticleGeometadataForm(
            data={
                "geometry_wkt": "POLYGON((-10 35, 40 35, 40 70, -10 70, -10 35))",
                "place_name": "",
                "admin_units": "",
                "temporal_periods_json": "[]",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_wkt_rejected(self):
        """Malformed WKT raises validation error."""
        form = ArticleGeometadataForm(
            data={
                "geometry_wkt": "NOT_VALID_WKT(abc)",
                "place_name": "",
                "admin_units": "",
                "temporal_periods_json": "[]",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("geometry_wkt", form.errors)

    def test_temporal_periods_valid_json(self):
        """Valid JSON array for temporal periods accepted."""
        form = ArticleGeometadataForm(
            data={
                "geometry_wkt": "",
                "place_name": "",
                "admin_units": "",
                "temporal_periods_json": '[["2020-01", "2021-06"]]',
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_temporal_periods_invalid_format(self):
        """Non-array JSON for temporal periods rejected."""
        form = ArticleGeometadataForm(
            data={
                "geometry_wkt": "",
                "place_name": "",
                "admin_units": "",
                "temporal_periods_json": '{"not": "array"}',
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("temporal_periods_json", form.errors)

    def test_empty_form_valid(self):
        """Empty form is valid (all fields optional)."""
        form = ArticleGeometadataForm(
            data={
                "geometry_wkt": "",
                "place_name": "",
                "admin_units": "",
                "temporal_periods_json": "[]",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
