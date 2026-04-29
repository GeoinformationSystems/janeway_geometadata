"""
Tests for the geometadata test factories.

Exercises every WKT sample through the model's bbox calculation and GeoJSON
serialisation, so that adding a new kind to ``WKT_SAMPLES`` automatically
gets coverage and any breakage in the WKT pipeline shows up here.
"""

from utils.testing import helpers

from plugins.geometadata.models import ArticleGeometadata
from plugins.geometadata.tests import factories
from plugins.geometadata.tests.base import GeometadataTestCase


class WKTSampleDiversityTests(GeometadataTestCase):
    """Sanity checks over the full WKT_SAMPLES set."""

    def test_all_kinds_have_a_place_name_label(self):
        """Every WKT kind should have a paired place_name for property output."""
        missing = [k for k in factories.WKT_SAMPLES if k not in factories.PLACE_NAME_FOR_KIND]
        self.assertEqual(missing, [], f"PLACE_NAME_FOR_KIND missing: {missing}")

    def test_each_kind_round_trips_through_bbox_and_geojson(self):
        """Every WKT sample parses, sets a bbox, and serialises to GeoJSON.

        We use a fresh article per kind (the model is OneToOne with article).
        """
        # Antimeridian polygon intentionally has coords beyond ±180 / range,
        # which the bbox extractor filters out — so we don't assert bbox for it.
        no_bbox_kinds = {"polygon_antimeridian"}

        for kind, wkt in factories.iter_kinds():
            with self.subTest(kind=kind):
                article = helpers.create_article(self.journal, with_author=True)
                geo = factories.make_article_geometadata(article, kind=kind)

                self.assertEqual(geo.geometry_wkt, wkt)
                # to_geojson always returns a Feature for non-empty WKT
                gj = geo.to_geojson()
                self.assertIsNotNone(gj, f"to_geojson returned None for {kind}")
                self.assertEqual(gj["type"], "Feature")
                self.assertIn("geometry", gj)
                self.assertIn("type", gj["geometry"])

                if kind not in no_bbox_kinds:
                    self.assertIsNotNone(
                        geo.bbox_north, f"bbox not derived for {kind}"
                    )

    def test_geometry_types_cover_the_full_wkt_palette(self):
        """The factory set covers every primitive plus GeometryCollection."""
        types = set()
        for kind in factories.WKT_SAMPLES:
            article = helpers.create_article(self.journal, with_author=True)
            geo = factories.make_article_geometadata(article, kind=kind)
            t = geo.get_geometry_type()
            self.assertIsNotNone(t, f"Could not detect geometry type for {kind}")
            types.add(t)

        expected = {
            "POINT",
            "LINESTRING",
            "POLYGON",
            "MULTIPOINT",
            "MULTILINESTRING",
            "MULTIPOLYGON",
            "GEOMETRYCOLLECTION",
        }
        self.assertEqual(types, expected, f"Unexpected coverage: {types}")


class TemporalSampleTests(GeometadataTestCase):
    """Sanity checks over the TEMPORAL_SAMPLES set."""

    def test_each_temporal_kind_renders_a_display_string(self):
        """Every non-empty temporal sample produces at least one display row."""
        for kind, periods in factories.TEMPORAL_SAMPLES.items():
            with self.subTest(kind=kind):
                article = helpers.create_article(self.journal, with_author=True)
                geo = factories.make_article_geometadata(
                    article, kind=None, temporal=kind
                )
                display = geo.get_temporal_display()
                if not periods:
                    self.assertEqual(display, [])
                else:
                    self.assertEqual(len(display), len(periods))

    def test_multi_period_preserved_round_trip(self):
        """Multi-period entries survive the .save() pipeline intact."""
        geo = factories.make_article_geometadata(
            self.article, kind="point", temporal="multi_period"
        )
        geo.refresh_from_db()
        self.assertEqual(len(geo.temporal_periods), 2)


class BuilderBehaviourTests(GeometadataTestCase):
    """Targeted checks on builder helpers themselves."""

    def test_unknown_kind_raises(self):
        with self.assertRaises(KeyError):
            factories.get_wkt("not-a-real-kind")

    def test_unknown_temporal_raises(self):
        with self.assertRaises(KeyError):
            factories.get_temporal("not-a-real-period")

    def test_overrides_take_precedence(self):
        geo = factories.make_article_geometadata(
            self.article,
            kind="point",
            place_name="Custom Override",
            admin_units="OVR-1",
        )
        self.assertEqual(geo.place_name, "Custom Override")
        self.assertEqual(geo.admin_units, "OVR-1")

    def test_iter_kinds_excludes(self):
        kinds = [k for k, _ in factories.iter_kinds(exclude={"point"})]
        self.assertNotIn("point", kinds)
        self.assertIn("polygon", kinds)

    def test_attach_geometadata_classmethod(self):
        """The base class's attach_geometadata wraps the factory."""
        geo = self.attach_geometadata(self.article, kind="multipoint")
        self.assertIsInstance(geo, ArticleGeometadata)
        self.assertEqual(geo.get_geometry_type(), "MULTIPOINT")
