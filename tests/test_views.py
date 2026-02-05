"""
Tests for geometadata views and API endpoints.

Tests editor access control, form submission, JSON API responses,
and GeoJSON download endpoints.
"""

from django.test import override_settings

from utils.testing import helpers

from plugins.geometadata.models import ArticleGeometadata
from plugins.geometadata.tests.base import GeometadataTestCase


@override_settings(
    URL_CONFIG="domain",
    ROOT_URLCONF="plugins.geometadata.tests.urls",
)
class EditArticleViewTests(GeometadataTestCase):
    """Tests for article geometadata edit view."""

    def _edit_url(self, article_id):
        return f"/plugins/geometadata/edit/article/{article_id}/"

    def test_edit_article_requires_editor(self):
        """Non-editor user cannot access edit view."""
        non_editor = self.article.owner  # Author, not editor
        self.client.force_login(non_editor)

        response = self.client.get(
            self._edit_url(self.article.pk),
            SERVER_NAME=self.journal.domain,
        )
        # Should redirect to login or return 403
        self.assertIn(response.status_code, [302, 403])

    def test_edit_article_get_renders_form(self):
        """Editor can access edit form."""
        self.client.force_login(self.editor)

        response = self.client.get(
            self._edit_url(self.article.pk),
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "geometry_wkt")

    def test_edit_article_post_saves_geometadata(self):
        """Form submission creates/updates geometadata."""
        self.client.force_login(self.editor)

        response = self.client.post(
            self._edit_url(self.article.pk),
            data={
                "geometry_wkt": "POINT(10 50)",
                "place_name": "Test Location",
                "admin_units": "",
                "temporal_periods_json": "[]",
            },
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 302)  # Redirect on success

        geo = ArticleGeometadata.objects.get(article=self.article)
        self.assertEqual(geo.place_name, "Test Location")
        self.assertEqual(geo.bbox_north, 50)


@override_settings(
    URL_CONFIG="domain",
    ROOT_URLCONF="plugins.geometadata.tests.urls",
)
class ArticleAPITests(GeometadataTestCase):
    """Tests for article GeoJSON API endpoint."""

    def test_api_article_geojson(self):
        """API returns valid GeoJSON Feature for article with geometadata."""
        ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10 50)",
            place_name="Test",
        )

        response = self.client.get(
            f"/plugins/geometadata/api/article/{self.article.pk}/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = response.json()
        self.assertEqual(data["type"], "Feature")
        self.assertEqual(data["geometry"]["type"], "Point")

    def test_api_article_not_found(self):
        """API returns 404 for non-existent article."""
        response = self.client.get(
            "/plugins/geometadata/api/article/99999/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 404)

    def test_api_all_returns_feature_collection(self):
        """All-articles API returns GeoJSON FeatureCollection."""
        ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10 50)",
        )

        response = self.client.get(
            "/plugins/geometadata/api/all/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertIn("features", data)


@override_settings(
    URL_CONFIG="domain",
    ROOT_URLCONF="plugins.geometadata.tests.urls",
)
class ArticleDownloadTests(GeometadataTestCase):
    """Tests for article GeoJSON download endpoint."""

    def test_download_article_geojson(self):
        """Download returns GeoJSON with Content-Disposition header."""
        ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10 50)",
            place_name="Berlin",
            admin_units="Berlin, Germany",
        )

        response = self.client.get(
            f"/plugins/geometadata/download/article/{self.article.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(".geojson", response["Content-Disposition"])

        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertEqual(len(data["features"]), 1)

    def test_download_article_includes_rich_properties(self):
        """Downloaded GeoJSON includes all expected article metadata properties."""
        ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10 50)",
            place_name="Berlin",
            admin_units="Berlin, Germany",
            temporal_periods=[["2020", "2021"]],
        )

        response = self.client.get(
            f"/plugins/geometadata/download/article/{self.article.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        data = response.json()
        props = data["features"][0]["properties"]

        # Check presence of all rich properties
        expected_keys = [
            "title",
            "authors",
            "doi",
            "doi_url",
            "url",
            "date_published",
            "date_accepted",
            "abstract",
            "keywords",
            "license",
            "section",
            "language",
            "peer_reviewed",
            "journal",
            "place_name",
            "admin_units",
            "temporal_periods",
        ]
        for key in expected_keys:
            self.assertIn(key, props, f"Missing property: {key}")

        # Check values for title and place_name
        self.assertEqual(props["title"], self.article.title)
        self.assertEqual(props["place_name"], "Berlin")

    def test_download_article_not_found(self):
        """Download returns 404 for article without geometadata."""
        response = self.client.get(
            f"/plugins/geometadata/download/article/{self.article.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 404)

    def test_download_article_filename_uses_id_without_doi(self):
        """Download filename uses article ID when no DOI is set."""
        ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10 50)",
        )

        response = self.client.get(
            f"/plugins/geometadata/download/article/{self.article.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        # Filename should contain the article ID
        content_disposition = response["Content-Disposition"]
        self.assertIn(str(self.article.pk), content_disposition)
        self.assertIn(self.journal.code, content_disposition)
        self.assertIn(".geojson", content_disposition)

    def test_download_article_filename_uses_doi_when_available(self):
        """Download filename uses DOI (sanitized) when available."""
        from identifiers.models import Identifier

        # Create a DOI identifier for the article
        Identifier.objects.create(
            id_type="doi",
            identifier="10.1234/test.article.1",
            article=self.article,
        )

        ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10 50)",
        )

        response = self.client.get(
            f"/plugins/geometadata/download/article/{self.article.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        # Filename should contain the DOI with / replaced by _
        content_disposition = response["Content-Disposition"]
        self.assertIn("10.1234_test.article.1", content_disposition)
        self.assertIn(self.journal.code, content_disposition)
        self.assertIn(".geojson", content_disposition)
        # Should NOT contain "article-{id}" format
        self.assertNotIn(f"article-{self.article.pk}", content_disposition)


@override_settings(
    URL_CONFIG="domain",
    ROOT_URLCONF="plugins.geometadata.tests.urls",
)
class IssueAPITests(GeometadataTestCase):
    """Tests for issue-level GeoJSON API and download."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.issue = helpers.create_issue(
            cls.journal, vol=1, number=1, articles=[cls.article]
        )

    def test_api_issue_returns_feature_collection(self):
        """Issue API returns GeoJSON FeatureCollection."""
        ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10 50)",
        )

        response = self.client.get(
            f"/plugins/geometadata/api/issue/{self.issue.pk}/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertEqual(len(data["features"]), 1)

    def test_api_issue_empty_without_geometadata(self):
        """Issue API returns empty features for issue without geometadata."""
        response = self.client.get(
            f"/plugins/geometadata/api/issue/{self.issue.pk}/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertEqual(len(data["features"]), 0)

    def test_download_issue_geojson(self):
        """Issue download returns GeoJSON with Content-Disposition and rich properties."""
        ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10 50)",
            place_name="Munich",
        )

        response = self.client.get(
            f"/plugins/geometadata/download/issue/{self.issue.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("issue", response["Content-Disposition"])

        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertEqual(len(data["features"]), 1)

        # Check presence of rich properties
        props = data["features"][0]["properties"]
        expected_keys = [
            "title",
            "authors",
            "doi",
            "url",
            "place_name",
            "admin_units",
            "temporal_periods",
        ]
        for key in expected_keys:
            self.assertIn(key, props, f"Missing property: {key}")

        # Check values for title and place_name
        self.assertEqual(props["title"], self.article.title)
        self.assertEqual(props["place_name"], "Munich")

    def test_download_issue_not_found_without_geometadata(self):
        """Issue download returns 404 when no articles have geometadata."""
        response = self.client.get(
            f"/plugins/geometadata/download/issue/{self.issue.pk}/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 404)

    def test_download_journal_geojson(self):
        """Journal download returns GeoJSON with Content-Disposition and rich properties."""
        ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10 50)",
            place_name="Munich",
        )

        response = self.client.get(
            "/plugins/geometadata/download/journal/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(self.journal.code, response["Content-Disposition"])
        self.assertIn("all.geojson", response["Content-Disposition"])

        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertEqual(len(data["features"]), 1)

        # Check presence of rich properties
        props = data["features"][0]["properties"]
        expected_keys = [
            "title",
            "authors",
            "doi",
            "url",
            "place_name",
            "admin_units",
            "temporal_periods",
            "journal",
        ]
        for key in expected_keys:
            self.assertIn(key, props, f"Missing property: {key}")

        # Check values
        self.assertEqual(props["title"], self.article.title)
        self.assertEqual(props["place_name"], "Munich")
        self.assertEqual(props["journal"], self.journal.name)

    def test_download_journal_includes_issue_info(self):
        """Journal download includes issue information when article is in an issue."""
        self.issue.articles.add(self.article)
        ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10 50)",
        )

        response = self.client.get(
            "/plugins/geometadata/download/journal/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        props = data["features"][0]["properties"]

        # Should have issue info
        self.assertIn("issue", props)
        self.assertIn("issue_id", props)
        self.assertEqual(props["issue_id"], self.issue.pk)

    def test_download_journal_not_found_without_geometadata(self):
        """Journal download returns 404 when no articles have geometadata."""
        response = self.client.get(
            "/plugins/geometadata/download/journal/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 404)

    def test_download_journal_multiple_articles(self):
        """Journal download includes only articles with geometadata."""
        from submission.models import Article

        # Create a second article (will have geometadata)
        article2 = Article.objects.create(
            journal=self.journal,
            title="Second Test Article",
            stage="Published",
            date_published="2024-01-01",
        )

        # Create a third article (will NOT have geometadata)
        article3 = Article.objects.create(
            journal=self.journal,
            title="Third Article Without Geometadata",
            stage="Published",
            date_published="2024-01-02",
        )

        # Only create geometadata for first two articles
        ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10 50)",
            place_name="Munich",
        )
        ArticleGeometadata.objects.create(
            article=article2,
            geometry_wkt="POINT(20 60)",
            place_name="Berlin",
        )
        # No geometadata for article3

        response = self.client.get(
            "/plugins/geometadata/download/journal/geojson/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        # Should only include 2 articles (those with geometadata)
        self.assertEqual(len(data["features"]), 2)

        # Check articles with geometadata are included
        titles = [f["properties"]["title"] for f in data["features"]]
        self.assertIn(self.article.title, titles)
        self.assertIn("Second Test Article", titles)

        # Check article without geometadata is NOT included
        self.assertNotIn(article3.title, titles)


@override_settings(
    URL_CONFIG="domain",
    ROOT_URLCONF="plugins.geometadata.tests.urls",
)
class PressAPITests(GeometadataTestCase):
    """Tests for press-wide GeoJSON API."""

    def test_api_press_returns_feature_collection(self):
        """Press API returns GeoJSON FeatureCollection with all articles."""
        ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10 50)",
        )

        response = self.client.get(
            "/plugins/geometadata/api/press/",
            SERVER_NAME=self.journal.domain,
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertGreaterEqual(len(data["features"]), 1)

    def test_api_press_includes_journal_name(self):
        """Press API features include journal name in properties."""
        ArticleGeometadata.objects.create(
            article=self.article,
            geometry_wkt="POINT(10 50)",
        )

        response = self.client.get(
            "/plugins/geometadata/api/press/",
            SERVER_NAME=self.journal.domain,
        )
        data = response.json()

        self.assertGreater(len(data["features"]), 0)
        props = data["features"][0]["properties"]
        self.assertIn("journal", props)
        self.assertIn("type", props)
        self.assertEqual(props["type"], "article")
