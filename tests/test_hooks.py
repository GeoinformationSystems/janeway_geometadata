"""
Tests for geometadata template hooks.

Tests HTML metadata embedding (Dublin Core, Schema.org, geo.* meta tags).
Uses HTML parsing to verify content is in the correct elements.
"""

import json
import re
from html.parser import HTMLParser

from django.template import Context, Template

from plugins.geometadata.models import ArticleGeometadata
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
        cls.geometadata = ArticleGeometadata.objects.create(
            article=cls.article,
            geometry_wkt="POLYGON((-10 35, 40 35, 40 70, -10 70, -10 35))",
            place_name="Europe",
            temporal_periods=[["2020-01-01", "2021-12-31"]],
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
