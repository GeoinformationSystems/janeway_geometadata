"""
Tests for geometadata template hooks.

Tests HTML metadata embedding (Dublin Core, Schema.org, geo.* meta tags).
Uses HTML parsing to verify content is in the correct elements.
"""

import json
from html.parser import HTMLParser

from django.template import Context, Template

from plugins.geometadata.tests import factories
from plugins.geometadata.tests.base import GeometadataTestCase


class MetaTagParser(HTMLParser):
    """Parser to extract meta tag content by name attribute."""

    def __init__(self):
        super().__init__()
        self.meta_tags = {}  # name -> {content, scheme, ...}
        self.link_tags = []  # list of {rel, type, href, ...}
        self.scripts = {}  # type -> content
        self._current_script_type = None
        self._current_script_content = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "meta" and "name" in attrs_dict:
            self.meta_tags[attrs_dict["name"]] = attrs_dict
        elif tag == "link":
            self.link_tags.append(attrs_dict)
        elif tag == "script" and attrs_dict.get("type"):
            self._current_script_type = attrs_dict["type"]
            self._current_script_content = []

    def handle_endtag(self, tag):
        if tag == "script" and self._current_script_type:
            content = "".join(self._current_script_content).strip()
            self.scripts[self._current_script_type] = content
            self._current_script_type = None

    def handle_data(self, data):
        if self._current_script_type:
            self._current_script_content.append(data)


def parse_html_meta(html):
    """Parse HTML and return structured meta tag data."""
    parser = MetaTagParser()
    parser.feed(html)
    return parser


class MetaTagsTemplateTests(GeometadataTestCase):
    """Tests for meta_tags.html template rendering."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Same record as before (Europe polygon, 2020–2021), now via factory
        # so the canonical WKT/temporal samples stay co-located in one place.
        cls.geometadata = factories.make_article_geometadata(
            cls.article, kind="polygon", temporal="modern_closed"
        )

    def _render_meta_tags(self, **context_overrides):
        """Render meta_tags.html with test context."""
        context = {
            "geometadata": self.geometadata,
            "geojson_str": '{"type":"Feature","geometry":{"type":"Point","coordinates":[10,50]}}',
            "geojson_geometry_str": '{"type":"Point","coordinates":[10,50]}',
            "temporal_intervals": ["2020-01-01/2021-12-31"],
            "temporal_interval": "2020-01-01/2021-12-31",
            "spatial_enabled": True,
            "temporal_enabled": True,
            "embed_dc": True,
            "embed_geo": True,
            "embed_schema": True,
            "embed_geojson": True,
            "embed_wkt": True,
            "embed_iso19139": True,
            "iso19139_xml": (
                '<gmd:EX_Extent xmlns:gmd="http://www.isotc211.org/2005/gmd"'
                ' xmlns:gco="http://www.isotc211.org/2005/gco"'
                ' xmlns:gml="http://www.opengis.net/gml/3.2">'
                "<gmd:geographicElement><gmd:EX_GeographicBoundingBox>"
                "<gmd:westBoundLongitude><gco:Decimal>-10</gco:Decimal>"
                "</gmd:westBoundLongitude>"
                "<gmd:eastBoundLongitude><gco:Decimal>40</gco:Decimal>"
                "</gmd:eastBoundLongitude>"
                "<gmd:southBoundLatitude><gco:Decimal>35</gco:Decimal>"
                "</gmd:southBoundLatitude>"
                "<gmd:northBoundLatitude><gco:Decimal>70</gco:Decimal>"
                "</gmd:northBoundLatitude>"
                "</gmd:EX_GeographicBoundingBox></gmd:geographicElement>"
                "</gmd:EX_Extent>"
            ),
            "geojson_download_url": "/download/article/1/geojson/",
        }
        context.update(context_overrides)

        template = Template("{% include 'geometadata/meta_tags.html' %}")
        return template.render(Context(context))

    def test_dc_spatial_coverage_contains_geojson(self):
        """DC.SpatialCoverage meta tag content attribute contains GeoJSON geometry."""
        html = self._render_meta_tags()
        parsed = parse_html_meta(html)

        self.assertIn("DC.SpatialCoverage", parsed.meta_tags)
        meta = parsed.meta_tags["DC.SpatialCoverage"]

        self.assertEqual(meta.get("scheme"), "GeoJSON")
        self.assertIn("content", meta)

        # Parse the content as JSON to verify it's valid GeoJSON
        content = meta["content"]
        geojson = json.loads(content)

        # DC.SpatialCoverage contains a full GeoJSON Feature
        self.assertEqual(geojson["type"], "Feature")
        self.assertIn("geometry", geojson)
        self.assertEqual(geojson["geometry"]["type"], "Point")
        self.assertEqual(geojson["geometry"]["coordinates"], [10, 50])

    def test_dc_box_contains_bbox(self):
        """DC.box meta tag content attribute contains bounding box coordinates."""
        html = self._render_meta_tags()
        parsed = parse_html_meta(html)

        self.assertIn("DC.box", parsed.meta_tags)
        meta = parsed.meta_tags["DC.box"]

        content = meta.get("content", "")
        self.assertIn("northlimit=70", content)
        self.assertIn("southlimit=35", content)
        self.assertIn("westlimit=-10", content)
        self.assertIn("eastlimit=40", content)

    def test_dc_temporal_rendered(self):
        """DC.temporal meta tag content attribute contains ISO8601 interval."""
        html = self._render_meta_tags()
        parsed = parse_html_meta(html)

        self.assertIn("DC.temporal", parsed.meta_tags)
        meta = parsed.meta_tags["DC.temporal"]

        self.assertEqual(meta.get("scheme"), "ISO8601")
        self.assertEqual(meta.get("content"), "2020-01-01/2021-12-31")

    def test_geo_placename_rendered(self):
        """geo.placename meta tag content attribute contains place name."""
        html = self._render_meta_tags()
        parsed = parse_html_meta(html)

        self.assertIn("geo.placename", parsed.meta_tags)
        meta = parsed.meta_tags["geo.placename"]

        self.assertEqual(meta.get("content"), "Europe")

    def test_schema_org_jsonld_rendered(self):
        """Schema.org JSON-LD script contains valid spatialCoverage."""
        html = self._render_meta_tags()
        parsed = parse_html_meta(html)

        self.assertIn("application/ld+json", parsed.scripts)
        script_content = parsed.scripts["application/ld+json"]

        # Parse the JSON-LD
        jsonld = json.loads(script_content)
        self.assertEqual(jsonld.get("@context"), "https://schema.org")
        self.assertIn("spatialCoverage", jsonld)

        # Verify spatialCoverage structure
        spatial = jsonld["spatialCoverage"]
        self.assertEqual(spatial.get("@type"), "Place")
        self.assertIn("geo", spatial)

    def test_geojson_link_rendered(self):
        """GeoJSON alternate link element has correct href attribute."""
        html = self._render_meta_tags()
        parsed = parse_html_meta(html)

        # Find link with rel="alternate" and type="application/geo+json"
        geojson_link = None
        for link in parsed.link_tags:
            if (
                link.get("rel") == "alternate"
                and link.get("type") == "application/geo+json"
            ):
                geojson_link = link
                break

        self.assertIsNotNone(geojson_link, "GeoJSON alternate link not found")
        self.assertEqual(geojson_link.get("href"), "/download/article/1/geojson/")

    def test_meta_tags_respect_disabled_settings(self):
        """Disabled embed settings suppress corresponding output."""
        html = self._render_meta_tags(
            embed_dc=False,
            embed_geo=False,
            embed_schema=False,
            embed_geojson=False,
            embed_wkt=False,
            embed_iso19139=False,
        )
        parsed = parse_html_meta(html)

        # DC tags should be absent
        self.assertNotIn("DC.SpatialCoverage", parsed.meta_tags)
        self.assertNotIn("DC.box", parsed.meta_tags)
        self.assertNotIn("DC.temporal", parsed.meta_tags)

        # geo tags should be absent
        self.assertNotIn("geo.placename", parsed.meta_tags)

        # JSON-LD script should be absent
        self.assertNotIn("application/ld+json", parsed.scripts)

        # GeoJSON link should be absent
        geojson_links = [
            link
            for link in parsed.link_tags
            if link.get("type") == "application/geo+json"
        ]
        self.assertEqual(len(geojson_links), 0)

        # ISO 19139 script should be absent
        self.assertNotIn("application/xml", parsed.scripts)

        # No DC.SpatialCoverage WKT scheme either
        self.assertNotIn('scheme="WKT"', html)

    def test_wkt_meta_tag_emitted_with_raw_geometry(self):
        """When embed_wkt is on, raw WKT appears as DC.SpatialCoverage WKT."""
        html = self._render_meta_tags()

        # Both schemes coexist on the same name
        self.assertIn(
            f'scheme="WKT" content="{self.geometadata.geometry_wkt}"',
            html,
        )
        self.assertIn('scheme="GeoJSON"', html)

    def test_wkt_disabled_suppresses_only_wkt_meta(self):
        """Toggling embed_wkt off keeps the GeoJSON variant intact."""
        html = self._render_meta_tags(embed_wkt=False)

        self.assertNotIn('scheme="WKT"', html)
        # GeoJSON DC.SpatialCoverage is still there
        self.assertIn('scheme="GeoJSON"', html)

    def test_wkt_meta_skipped_when_spatial_disabled(self):
        """When enable_spatial is off, no WKT tag even if embed_wkt is on."""
        html = self._render_meta_tags(spatial_enabled=False)
        self.assertNotIn('scheme="WKT"', html)

    def test_dc_schema_link_present_when_only_wkt_enabled(self):
        """Schema.DC link still emitted when only the WKT variant is on."""
        html = self._render_meta_tags(
            embed_dc=False,
            embed_geo=False,
            embed_schema=False,
            embed_geojson=False,
            embed_iso19139=False,
        )
        self.assertIn('rel="schema.DC"', html)
        self.assertIn('scheme="WKT"', html)


class WKTEmbeddingDiversityTests(GeometadataTestCase):
    """Verify the WKT meta tag round-trips every WKT_SAMPLES kind verbatim."""

    def test_every_sample_kind_appears_verbatim(self):
        from django.template import Context, Template

        from plugins.geometadata.tests import factories
        from utils.testing import helpers

        template = Template("{% include 'geometadata/meta_tags.html' %}")

        for kind, wkt in factories.iter_kinds():
            with self.subTest(kind=kind):
                # Fresh article per kind because of the OneToOne constraint.
                article = helpers.create_article(self.journal, with_author=True)
                geo = factories.make_article_geometadata(article, kind=kind)

                context = {
                    "geometadata": geo,
                    "geojson_str": "",
                    "geojson_geometry_str": "",
                    "temporal_intervals": [],
                    "temporal_interval": "",
                    "spatial_enabled": True,
                    "temporal_enabled": True,
                    "embed_dc": False,
                    "embed_geo": False,
                    "embed_schema": False,
                    "embed_geojson": False,
                    "embed_wkt": True,
                    "embed_iso19139": False,
                    "iso19139_xml": "",
                    "geojson_download_url": "",
                }
                html = template.render(Context(context))

                self.assertIn('scheme="WKT"', html, f"{kind}: WKT tag missing")
                self.assertIn(
                    wkt,
                    html,
                    f"{kind}: stored WKT not echoed verbatim into the meta tag",
                )


class ISO19139BuilderTests(GeometadataTestCase):
    """Direct unit tests for :func:`hooks._build_iso19139_extent`."""

    def _build(self, **kwargs):
        from plugins.geometadata.hooks import _build_iso19139_extent
        from plugins.geometadata.tests import factories

        defaults = dict(kind="polygon", temporal="modern_closed")
        defaults.update(kwargs.pop("geo_kwargs", {}))
        geo = factories.make_article_geometadata(self.article, **defaults)
        return _build_iso19139_extent(geo, **kwargs)

    def test_builds_well_formed_extent_with_all_components(self):
        """Default polygon + temporal record produces parseable XML."""
        from xml.etree import ElementTree as ET

        xml = self._build()

        ns = {
            "gmd": "http://www.isotc211.org/2005/gmd",
            "gco": "http://www.isotc211.org/2005/gco",
            "gml": "http://www.opengis.net/gml/3.2",
        }
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, f"{{{ns['gmd']}}}EX_Extent")

        bbox = root.find(".//gmd:EX_GeographicBoundingBox", ns)
        self.assertIsNotNone(bbox)
        north = bbox.find("gmd:northBoundLatitude/gco:Decimal", ns).text
        self.assertEqual(float(north), 70.0)

        time_period = root.find(".//gml:TimePeriod", ns)
        self.assertIsNotNone(time_period)
        self.assertEqual(
            time_period.find("gml:beginPosition", ns).text, "2020-01-01"
        )

    def test_omits_spatial_when_disabled(self):
        xml = self._build(include_spatial=False)
        # No bbox / geographic description survives
        self.assertNotIn("EX_GeographicBoundingBox", xml)
        self.assertNotIn("EX_GeographicDescription", xml)
        # Temporal stays
        self.assertIn("EX_TemporalExtent", xml)

    def test_omits_temporal_when_disabled(self):
        xml = self._build(include_temporal=False)
        self.assertNotIn("EX_TemporalExtent", xml)
        self.assertIn("EX_GeographicBoundingBox", xml)

    def test_returns_empty_when_nothing_to_embed(self):
        from plugins.geometadata.hooks import _build_iso19139_extent
        from plugins.geometadata.tests import factories

        geo = factories.make_article_geometadata(
            self.article, kind=None, temporal=None
        )
        self.assertEqual(_build_iso19139_extent(geo), "")

    def test_open_period_uses_indeterminate_position(self):
        """Open-end period emits gml indeterminatePosition marker."""
        xml = self._build(geo_kwargs={"temporal": "open_end"})
        self.assertIn('indeterminatePosition="unknown"', xml)

    def test_emits_one_temporal_element_per_period(self):
        """Multi-period record produces multiple gml:TimePeriod elements."""
        xml = self._build(geo_kwargs={"temporal": "multi_period"})
        # multi_period has 2 ranges
        self.assertEqual(xml.count("<gml:TimePeriod"), 2)

    def test_place_name_escaped_for_xml(self):
        """Place names with reserved XML characters are escaped."""
        xml = self._build(
            geo_kwargs={"kind": "point", "place_name": "Foo & <bar>"}
        )
        self.assertIn("Foo &amp; &lt;bar&gt;", xml)
        self.assertNotIn("<bar>", xml)


class ISO19139EmbeddingIntegrationTests(GeometadataTestCase):
    """Integration test: end-to-end ISO 19139 emission via the hook."""

    def test_iso19139_appears_when_embed_setting_on(self):
        """With factory-made geometadata, the rendered head contains the
        ISO 19139 script with bbox, place name and temporal extent."""
        from plugins.geometadata.hooks import _build_iso19139_extent
        from plugins.geometadata.tests import factories

        geo = factories.make_article_geometadata(
            self.article, kind="polygon", temporal="modern_closed"
        )
        xml = _build_iso19139_extent(geo)

        # bbox derived from the canonical Europe polygon (floats stored)
        self.assertIn("EX_GeographicBoundingBox", xml)
        self.assertIn(">35.0</gco:Decimal>", xml)  # southBoundLatitude
        self.assertIn(">70.0</gco:Decimal>", xml)  # northBoundLatitude

        # Place name from PLACE_NAME_FOR_KIND["polygon"] == "Europe"
        self.assertIn("EX_GeographicDescription", xml)
        self.assertIn("Europe", xml)

        # Temporal periods
        self.assertIn("EX_TemporalExtent", xml)
        self.assertIn("2020-01-01", xml)
        self.assertIn("2024-12-31", xml)

    def test_template_emits_application_xml_script_block(self):
        """meta_tags.html wraps the fragment in <script type='application/xml'>."""
        from plugins.geometadata.hooks import _build_iso19139_extent
        from plugins.geometadata.tests import factories

        geo = factories.make_article_geometadata(
            self.article, kind="polygon", temporal="modern_closed"
        )
        context = {
            "geometadata": geo,
            "geojson_str": "",
            "geojson_geometry_str": "",
            "temporal_intervals": ["2020-01-01/2024-12-31"],
            "temporal_interval": "2020-01-01/2024-12-31",
            "spatial_enabled": True,
            "temporal_enabled": True,
            "embed_dc": False,
            "embed_geo": False,
            "embed_schema": False,
            "embed_geojson": False,
            "embed_wkt": False,
            "embed_iso19139": True,
            "iso19139_xml": _build_iso19139_extent(geo),
            "geojson_download_url": "",
        }
        template = Template("{% include 'geometadata/meta_tags.html' %}")
        html = template.render(Context(context))
        parsed = parse_html_meta(html)

        self.assertIn("application/xml", parsed.scripts)
        content = parsed.scripts["application/xml"]
        self.assertIn("EX_Extent", content)
        self.assertIn("EX_GeographicBoundingBox", content)
