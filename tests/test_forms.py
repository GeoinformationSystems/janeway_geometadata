"""
Tests for geometadata forms.

Tests WKT validation and temporal period format validation.

Inherits from :class:`GeometadataTestCase` for consistency with the rest of
the suite, and exercises the form against the full WKT and temporal sample
palette so every supported geometry type and period structure is covered.
"""

import json

from plugins.geometadata.forms import ArticleGeometadataForm
from plugins.geometadata.tests import factories
from plugins.geometadata.tests.base import GeometadataTestCase


def _empty_form_data(**overrides):
    data = {
        "geometry_wkt": "",
        "place_name": "",
        "admin_units": "",
        "temporal_periods_json": "[]",
    }
    data.update(overrides)
    return data


class ArticleGeometadataFormTests(GeometadataTestCase):
    """Targeted unit checks on ArticleGeometadataForm validation."""

    def test_valid_wkt_accepted(self):
        """A canonical polygon passes validation."""
        form = ArticleGeometadataForm(
            data=_empty_form_data(geometry_wkt=factories.get_wkt("polygon"))
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_wkt_rejected(self):
        """Malformed WKT raises validation error."""
        form = ArticleGeometadataForm(
            data=_empty_form_data(geometry_wkt="NOT_VALID_WKT(abc)")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("geometry_wkt", form.errors)

    def test_temporal_periods_valid_json(self):
        """Valid JSON array for temporal periods accepted."""
        form = ArticleGeometadataForm(
            data=_empty_form_data(
                temporal_periods_json='[["2020-01", "2021-06"]]'
            )
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_temporal_periods_invalid_format(self):
        """Non-array JSON for temporal periods rejected."""
        form = ArticleGeometadataForm(
            data=_empty_form_data(
                temporal_periods_json='{"not": "array"}'
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("temporal_periods_json", form.errors)

    def test_empty_form_valid(self):
        """Empty form is valid (all fields optional)."""
        form = ArticleGeometadataForm(data=_empty_form_data())
        self.assertTrue(form.is_valid(), form.errors)


class ArticleGeometadataFormDiversityTests(GeometadataTestCase):
    """Run the form against every WKT and temporal sample.

    Adding a new entry to ``factories.WKT_SAMPLES`` or
    ``factories.TEMPORAL_SAMPLES`` automatically widens form coverage.
    """

    def test_every_wkt_sample_validates(self):
        for kind, wkt in factories.iter_kinds():
            with self.subTest(kind=kind):
                form = ArticleGeometadataForm(
                    data=_empty_form_data(geometry_wkt=wkt)
                )
                self.assertTrue(
                    form.is_valid(),
                    f"Form rejected sample '{kind}' (WKT={wkt!r}): {form.errors}",
                )

    def test_every_temporal_sample_validates(self):
        for name, periods in factories.TEMPORAL_SAMPLES.items():
            with self.subTest(periods=name):
                form = ArticleGeometadataForm(
                    data=_empty_form_data(
                        temporal_periods_json=json.dumps(periods)
                    )
                )
                self.assertTrue(
                    form.is_valid(),
                    f"Form rejected temporal sample '{name}' "
                    f"(periods={periods!r}): {form.errors}",
                )
