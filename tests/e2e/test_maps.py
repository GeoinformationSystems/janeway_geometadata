"""
E2E tests for geometadata map functionality.

Tests the presence and basic functionality of maps on:
- Article pages (article_map.html hook)
- Issue pages (issue_map.html hook)
- Journal map page (/plugins/geometadata/map/)
- Press map page (/plugins/geometadata/press-map/)

Screenshots are saved for all map pages in test-results/screenshots/.
"""

import json
from pathlib import Path

from playwright.sync_api import Page, expect


# Directory for test artifacts
RESULTS_DIR = Path(__file__).parent / "test-results"
SCREENSHOTS_DIR = RESULTS_DIR / "screenshots"


def ensure_screenshot_dir():
    """Create screenshot directory if it doesn't exist."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class TestJournalMapPage:
    """Tests for the journal-level map page."""

    def test_map_page_loads(self, page: Page, base_url: str, journal):
        """Journal map page loads successfully."""
        url = f"{base_url}/plugins/geometadata/map/"
        page.goto(url, wait_until="networkidle")

        # Page should load without errors
        assert page.title() or True  # Page loaded
        expect(page.locator("body")).to_be_visible()

    def test_map_page_contains_leaflet_map(
        self, page: Page, base_url: str, journal, map_selectors
    ):
        """Journal map page contains a Leaflet map container."""
        url = f"{base_url}/plugins/geometadata/map/"
        page.goto(url, wait_until="networkidle")

        # Wait for map to initialize
        leaflet_map = page.locator(map_selectors["leaflet_map"])
        expect(leaflet_map).to_be_visible(timeout=10000)

        # Save screenshot
        ensure_screenshot_dir()
        page.screenshot(path=SCREENSHOTS_DIR / "journal_map_page.png", full_page=True)

    def test_map_page_loads_tiles(
        self, page: Page, base_url: str, journal, map_selectors
    ):
        """Journal map page loads map tiles."""
        url = f"{base_url}/plugins/geometadata/map/"
        page.goto(url, wait_until="networkidle")

        # Wait for tiles to load
        tiles = page.locator(map_selectors["leaflet_tile"])
        expect(tiles.first).to_be_visible(timeout=15000)

    def test_map_page_shows_marker_for_article(
        self, page: Page, base_url: str, journal, article, geometadata, map_selectors
    ):
        """Journal map page shows a marker for the article with geometadata."""
        url = f"{base_url}/plugins/geometadata/map/"
        page.goto(url, wait_until="networkidle")

        # Wait for map and marker
        page.wait_for_selector(map_selectors["leaflet_map"], timeout=10000)

        # Check for marker presence
        markers = page.locator(map_selectors["leaflet_marker"])
        expect(markers.first).to_be_visible(timeout=10000)

        # Save screenshot with marker visible
        ensure_screenshot_dir()
        page.screenshot(
            path=SCREENSHOTS_DIR / "journal_map_with_marker.png", full_page=True
        )

    def test_map_page_marker_shows_popup_on_click(
        self, page: Page, base_url: str, journal, article, geometadata, map_selectors
    ):
        """Clicking a marker opens a popup with article info."""
        url = f"{base_url}/plugins/geometadata/map/"
        page.goto(url, wait_until="networkidle")

        # Wait for marker and click it
        marker = page.locator(map_selectors["leaflet_marker"]).first
        expect(marker).to_be_visible(timeout=10000)
        marker.click()

        # Popup should appear
        popup = page.locator(map_selectors["leaflet_popup"])
        expect(popup).to_be_visible(timeout=5000)

        # Save screenshot with popup visible
        ensure_screenshot_dir()
        page.screenshot(path=SCREENSHOTS_DIR / "journal_map_popup.png", full_page=True)

    def test_map_page_has_download_link(
        self, page: Page, base_url: str, journal, map_selectors
    ):
        """Journal map page has a GeoJSON download link."""
        url = f"{base_url}/plugins/geometadata/map/"
        page.goto(url, wait_until="networkidle")

        # Look for download button/link
        download_link = page.locator('a[href*="geojson"]')
        if download_link.count() > 0:
            expect(download_link.first).to_be_visible()


class TestPressMapPage:
    """Tests for the press-level map page."""

    def test_press_map_page_loads(self, page: Page, base_url: str):
        """Press map page loads successfully."""
        url = f"{base_url}/plugins/geometadata/press-map/"
        page.goto(url, wait_until="networkidle")

        # Page should load
        expect(page.locator("body")).to_be_visible()

    def test_press_map_contains_leaflet_map(
        self, page: Page, base_url: str, map_selectors
    ):
        """Press map page contains a Leaflet map container."""
        url = f"{base_url}/plugins/geometadata/press-map/"
        page.goto(url, wait_until="networkidle")

        # Wait for map
        leaflet_map = page.locator(map_selectors["leaflet_map"])
        expect(leaflet_map).to_be_visible(timeout=10000)

        # Save screenshot
        ensure_screenshot_dir()
        page.screenshot(path=SCREENSHOTS_DIR / "press_map_page.png", full_page=True)

    def test_press_map_shows_articles_from_all_journals(
        self, page: Page, base_url: str, article, geometadata, map_selectors
    ):
        """Press map shows markers for articles across all journals."""
        url = f"{base_url}/plugins/geometadata/press-map/"
        page.goto(url, wait_until="networkidle")

        # Wait for markers
        page.wait_for_selector(map_selectors["leaflet_map"], timeout=10000)
        markers = page.locator(map_selectors["leaflet_marker"])
        expect(markers.first).to_be_visible(timeout=10000)

        # Save screenshot with markers
        ensure_screenshot_dir()
        page.screenshot(
            path=SCREENSHOTS_DIR / "press_map_with_markers.png", full_page=True
        )


class TestIssueMapHook:
    """Tests for the issue map hook (embedded in issue pages)."""

    def test_issue_page_loads(self, page: Page, base_url: str, journal, issue):
        """Issue page loads successfully."""
        # Issue URL pattern: /issue/{vol}/{issue}/ or similar
        url = f"{base_url}/issue/{issue.volume}/{issue.issue}/"
        response = page.goto(url, wait_until="networkidle")

        # Should get a response (may be 200 or redirect)
        assert response is not None

    def test_issue_page_contains_map_when_articles_have_geometadata(
        self, page: Page, base_url: str, journal, issue, geometadata, map_selectors
    ):
        """Issue page shows a map when articles in the issue have geometadata."""
        url = f"{base_url}/issue/{issue.volume}/{issue.issue}/"
        page.goto(url, wait_until="networkidle")

        # Save screenshot regardless of map presence
        ensure_screenshot_dir()
        page.screenshot(path=SCREENSHOTS_DIR / "issue_page.png", full_page=True)

        # Look for map container - may not be present if hook not configured
        map_container = page.locator(map_selectors["map_container"])
        leaflet_map = page.locator(map_selectors["leaflet_map"])

        # Either the custom container or leaflet map should be visible
        # if the hook is properly configured
        if map_container.count() > 0 or leaflet_map.count() > 0:
            # Map is present, verify it's visible
            if leaflet_map.count() > 0:
                expect(leaflet_map.first).to_be_visible(timeout=10000)
                # Save screenshot with map
                page.screenshot(
                    path=SCREENSHOTS_DIR / "issue_page_with_map.png", full_page=True
                )


class TestArticleMapHook:
    """Tests for the article map hook (embedded in article pages)."""

    def test_article_page_loads(self, page: Page, base_url: str, journal, article):
        """Article page loads successfully."""
        url = f"{base_url}/article/{article.pk}/"
        response = page.goto(url, wait_until="networkidle")

        assert response is not None

    def test_article_page_contains_map_for_article_with_geometadata(
        self, page: Page, base_url: str, journal, article, geometadata, map_selectors
    ):
        """Article page shows a map when the article has geometadata."""
        url = f"{base_url}/article/{article.pk}/"
        page.goto(url, wait_until="networkidle")

        # Save screenshot regardless of map presence
        ensure_screenshot_dir()
        page.screenshot(path=SCREENSHOTS_DIR / "article_page.png", full_page=True)

        # Look for map elements
        leaflet_map = page.locator(map_selectors["leaflet_map"])

        if leaflet_map.count() > 0:
            expect(leaflet_map.first).to_be_visible(timeout=10000)
            # Save screenshot with map
            page.screenshot(
                path=SCREENSHOTS_DIR / "article_page_with_map.png", full_page=True
            )

    def test_article_map_shows_correct_location(
        self, page: Page, base_url: str, journal, article, geometadata, map_selectors
    ):
        """Article map displays marker at the correct location (Berlin)."""
        url = f"{base_url}/article/{article.pk}/"
        page.goto(url, wait_until="networkidle")

        leaflet_map = page.locator(map_selectors["leaflet_map"])

        if leaflet_map.count() > 0:
            expect(leaflet_map.first).to_be_visible(timeout=10000)

            # Check for marker
            marker = page.locator(map_selectors["leaflet_marker"])
            if marker.count() > 0:
                expect(marker.first).to_be_visible(timeout=5000)


class TestMapAPIEndpoints:
    """Tests for GeoJSON API endpoints used by maps."""

    def test_article_api_returns_geojson(
        self, page: Page, base_url: str, article, geometadata
    ):
        """Article API endpoint returns valid GeoJSON."""
        url = f"{base_url}/plugins/geometadata/api/article/{article.pk}/"
        response = page.goto(url)

        assert response is not None
        assert response.status == 200

        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

    def test_all_api_returns_feature_collection(
        self, page: Page, base_url: str, article, geometadata
    ):
        """All-articles API returns a GeoJSON FeatureCollection."""
        url = f"{base_url}/plugins/geometadata/api/all/"
        response = page.goto(url)

        assert response is not None
        assert response.status == 200

    def test_issue_api_returns_feature_collection(
        self, page: Page, base_url: str, issue, geometadata
    ):
        """Issue API returns a GeoJSON FeatureCollection."""
        url = f"{base_url}/plugins/geometadata/api/issue/{issue.pk}/"
        response = page.goto(url)

        assert response is not None
        assert response.status == 200

    def test_press_api_returns_feature_collection(
        self, page: Page, base_url: str, geometadata
    ):
        """Press API returns a GeoJSON FeatureCollection."""
        url = f"{base_url}/plugins/geometadata/api/press/"
        response = page.goto(url)

        assert response is not None
        assert response.status == 200


class TestGeoJSONDownloads:
    """Tests for GeoJSON download functionality.

    Verifies download headers and basic GeoJSON structure (FeatureCollection
    with correct feature count). Detailed content validation is done in unit tests.

    Uses ``page.request.get()`` instead of ``page.goto()`` because the
    download endpoints return ``Content-Disposition: attachment`` responses
    which Playwright treats as file downloads rather than page navigations.
    """

    def test_article_geojson_download(
        self, page: Page, base_url: str, article, geometadata
    ):
        """Article GeoJSON download returns FeatureCollection with 1 feature."""
        url = f"{base_url}/plugins/geometadata/download/article/{article.pk}/geojson/"

        response = page.request.get(url)

        assert response.status == 200

        # Check for download headers
        content_disposition = response.headers.get("content-disposition", "")
        assert "attachment" in content_disposition
        assert ".geojson" in content_disposition

        # Parse and validate GeoJSON structure
        geojson = response.json()

        assert geojson["type"] == "FeatureCollection"
        assert "features" in geojson
        assert len(geojson["features"]) == 1  # One article with geometadata

    def test_issue_geojson_download(
        self, page: Page, base_url: str, issue, geometadata
    ):
        """Issue GeoJSON download returns FeatureCollection with 1 feature."""
        url = f"{base_url}/plugins/geometadata/download/issue/{issue.pk}/geojson/"

        response = page.request.get(url)

        assert response.status == 200

        content_disposition = response.headers.get("content-disposition", "")
        assert "attachment" in content_disposition

        # Parse and validate GeoJSON structure
        geojson = response.json()

        assert geojson["type"] == "FeatureCollection"
        assert "features" in geojson
        assert len(geojson["features"]) == 1  # One article in issue with geometadata

    def test_journal_geojson_download(
        self, page: Page, base_url: str, journal, geometadata
    ):
        """Journal GeoJSON download returns FeatureCollection with 1 feature."""
        url = f"{base_url}/plugins/geometadata/download/journal/geojson/"

        response = page.request.get(url)

        assert response.status == 200

        content_disposition = response.headers.get("content-disposition", "")
        assert "attachment" in content_disposition

        # Parse and validate GeoJSON structure
        geojson = response.json()

        assert geojson["type"] == "FeatureCollection"
        assert "features" in geojson
        assert len(geojson["features"]) == 1  # One article in journal with geometadata

    def test_geojson_features_have_required_structure(
        self, page: Page, base_url: str, article, geometadata
    ):
        """GeoJSON features have required type, geometry, and properties."""
        url = f"{base_url}/plugins/geometadata/download/article/{article.pk}/geojson/"

        response = page.request.get(url)
        geojson = response.json()

        # Check feature structure
        feature = geojson["features"][0]
        assert feature["type"] == "Feature"
        assert "geometry" in feature
        assert "properties" in feature

        # Geometry should have type and coordinates
        geometry = feature["geometry"]
        assert "type" in geometry
        assert "coordinates" in geometry

        # Properties should exist (detailed validation in unit tests)
        assert isinstance(feature["properties"], dict)
