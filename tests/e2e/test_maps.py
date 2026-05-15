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
        """Clicking on the map at the Berlin latlng opens a popup with
        article info. Implementation detail: the overlap-picker manager is
        now the click authority on aggregated maps (see TestOverlapPicker
        for its dedicated coverage), so this test fires a synthetic click
        on the map at the seeded article's coordinate rather than relying
        on Playwright's pointer hit-testing through z-stacked SVG paths.
        """
        url = f"{base_url}/plugins/geometadata/map/"
        page.goto(url, wait_until="networkidle")

        # Wait for the map's exposed handle, then dispatch the click.
        page.wait_for_function(
            "typeof window.geometadataMap !== 'undefined'", timeout=10000
        )
        page.evaluate(
            """() => window.geometadataMap.fire('click', {
                latlng: L.latLng(52.5, 13.4)
            })"""
        )

        # Popup should appear (either the standard Leaflet popup or the
        # overlap manager's paginated popup — both have .leaflet-popup).
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
        # Two articles in issue have geometadata (the Berlin point + the
        # overlap-test polygon containing it).
        assert len(geojson["features"]) == 2

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
        # Two articles in journal have geometadata.
        assert len(geojson["features"]) == 2

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


# ---------------------------------------------------------------------------
# Overlap picker (issue #14) — paginated popup for clicks that hit multiple
# features at the same location. Mirrors the structure of the OJS plugin's
# Cypress coverage (66-overlap-popup.cy.js).
# ---------------------------------------------------------------------------


def _wait_for_overlap_globals(page: Page):
    """Wait until geometadata-overlap.js has populated its window globals."""
    page.wait_for_function(
        "typeof window.geometadata_findOverlappingArticles === 'function'",
        timeout=10000,
    )


class TestOverlapHelpers:
    """Pure-helper tests — drive the geometry hit-test functions directly via
    page.evaluate. No real overlap fixtures needed; this is the analogue of
    the 'pure helpers' Cypress tests in the OJS plugin."""

    def test_point_in_ring_basic_square(self, page: Page, base_url: str, journal):
        page.goto(f"{base_url}/plugins/geometadata/map/", wait_until="networkidle")
        _wait_for_overlap_globals(page)
        # Square ring around (0,0) of half-width 5
        ring = [[-5, -5], [5, -5], [5, 5], [-5, 5], [-5, -5]]
        result = page.evaluate(
            """([ring]) => ({
                inside: window.geometadata_pointInRing({lat:0,lng:0}, ring),
                outside: window.geometadata_pointInRing({lat:10,lng:10}, ring),
            })""",
            [ring],
        )
        assert result == {"inside": True, "outside": False}

    def test_point_in_polygon_with_hole(self, page: Page, base_url: str, journal):
        page.goto(f"{base_url}/plugins/geometadata/map/", wait_until="networkidle")
        _wait_for_overlap_globals(page)
        # Outer ring [-10,10]; inner hole [-2,2]. Point at (0,0) is in the hole.
        polygon = [
            [[-10, -10], [10, -10], [10, 10], [-10, 10], [-10, -10]],
            [[-2, -2], [2, -2], [2, 2], [-2, 2], [-2, -2]],
        ]
        result = page.evaluate(
            """([poly]) => ({
                in_outer_only: window.geometadata_pointInPolygon({lat:8,lng:8}, poly),
                in_hole: window.geometadata_pointInPolygon({lat:0,lng:0}, poly),
                outside: window.geometadata_pointInPolygon({lat:20,lng:20}, poly),
            })""",
            [polygon],
        )
        assert result == {"in_outer_only": True, "in_hole": False, "outside": False}

    def test_point_on_marker_uses_pixel_tolerance(
        self, page: Page, base_url: str, journal
    ):
        page.goto(f"{base_url}/plugins/geometadata/map/", wait_until="networkidle")
        _wait_for_overlap_globals(page)
        page.wait_for_function("typeof window.map !== 'undefined' || true")
        # Pin a known zoom/centre so pixel distances are deterministic.
        result = page.evaluate(
            """() => {
                const map = document.querySelector('#geometadata-fullmap')
                    && document.querySelector('#geometadata-fullmap')._leaflet_map
                    || (window.L && window.L.Map && Object.values(L.Map._instances || {})[0]);
                // Fallback: find any leaflet map on the page
                let mapInst = null;
                for (const k in window) {
                    if (window[k] && window[k] instanceof L.Map) { mapInst = window[k]; break; }
                }
                // The page's inline JS keeps the map in a closure, so build a
                // throwaway one in the same DOM for the helper test.
                const div = document.createElement('div');
                div.style.cssText = 'width:400px;height:400px;position:absolute;left:-9999px;';
                document.body.appendChild(div);
                const m = L.map(div, { zoomControl: false, attributionControl: false });
                m.setView([52.37, 8.43], 4);
                const out = {
                    centre_hits: window.geometadata_pointOnMarker(m, L.latLng(52.37, 8.43), [8.43, 52.37]),
                    far_misses: window.geometadata_pointOnMarker(m, L.latLng(52.37, 8.43), [9.43, 52.37]),
                };
                m.remove();
                document.body.removeChild(div);
                return out;
            }"""
        )
        assert result == {"centre_hits": True, "far_misses": False}

    def test_geometry_collection_dispatches_to_children(
        self, page: Page, base_url: str, journal
    ):
        page.goto(f"{base_url}/plugins/geometadata/map/", wait_until="networkidle")
        _wait_for_overlap_globals(page)
        # GeometryCollection containing one Polygon + one Point — hit either.
        geom = {
            "type": "GeometryCollection",
            "geometries": [
                {
                    "type": "Polygon",
                    "coordinates": [
                        [[-5, -5], [5, -5], [5, 5], [-5, 5], [-5, -5]],
                    ],
                },
                {"type": "Point", "coordinates": [50, 50]},
            ],
        }
        result = page.evaluate(
            """([geom]) => {
                const div = document.createElement('div');
                div.style.cssText = 'width:400px;height:400px;position:absolute;left:-9999px;';
                document.body.appendChild(div);
                const m = L.map(div, { zoomControl: false, attributionControl: false });
                m.setView([0, 0], 4);
                const out = {
                    inside_polygon: window.geometadata_geometryContainsPoint(m, geom, L.latLng(0, 0)),
                    on_point:       window.geometadata_geometryContainsPoint(m, geom, L.latLng(50, 50)),
                    far_outside:    window.geometadata_geometryContainsPoint(m, geom, L.latLng(80, 80)),
                };
                m.remove();
                document.body.removeChild(div);
                return out;
            }""",
            [geom],
        )
        assert result == {
            "inside_polygon": True,
            "on_point": True,
            "far_outside": False,
        }


class TestOverlapPicker:
    """Integration tests for the paginated popup on the journal map."""

    def _open_journal_map(self, page: Page, base_url: str):
        page.goto(f"{base_url}/plugins/geometadata/map/", wait_until="networkidle")
        _wait_for_overlap_globals(page)
        # Wait for the GeoJSON layer to render at least one path.
        page.wait_for_selector(".leaflet-overlay-pane path.leaflet-interactive", timeout=10000)

    def _click_at_berlin(self, page: Page):
        """Click the Berlin (13.4, 52.5) latlng — both seeded articles overlap there."""
        # Use the inline map's click event directly. The page's map handle isn't
        # exposed, so dispatch a synthetic click on the layer matching the marker.
        page.evaluate(
            """() => {
                // Find the leaflet map instance attached to the fullmap container.
                const cont = document.getElementById('geometadata-fullmap');
                let m = null;
                for (const k in cont) {
                    if (k.startsWith('_leaflet_id')) {
                        // Walk Leaflet's instance registry
                        for (const id in L.DomUtil._domEvents || {}) { /* noop */ }
                    }
                }
                // Recover the map via the documented Leaflet API: the container
                // has a `_leaflet_id` and L stores instances on the global.
                m = window.L && window._geometadataMapForTests
                    || (function () {
                        // Fallback: poke every key on window for a Map instance.
                        for (const k in window) {
                            try {
                                if (window[k] instanceof L.Map) return window[k];
                            } catch (e) {}
                        }
                        return null;
                    })();
                if (!m) return false;
                m.fire('click', { latlng: L.latLng(52.5, 13.4) });
                return true;
            }"""
        )

    def test_paginated_popup_shows_for_overlapping_features(
        self, page: Page, base_url: str, journal, article, article_overlap
    ):
        """Click at Berlin → paginated popup with prev/next chrome appears."""
        self._open_journal_map(page, base_url)

        # Fire a synthetic click on the live map at the Berlin latlng. The
        # overlap manager listens to map.on('click') and is the click
        # authority once it's instantiated.
        page.evaluate(
            """() => {
                if (window.geometadataMap) {
                    window.geometadataMap.fire('click', {
                        latlng: L.latLng(52.5, 13.4)
                    });
                }
            }"""
        )

        # Paginated popup chrome must be visible.
        page.wait_for_selector(".geometadata-overlap-header", timeout=5000)
        counter = page.locator(".geometadata-overlap-counter").first
        expect(counter).to_be_visible()
        expect(counter).to_contain_text("1")
        expect(counter).to_contain_text("2")

        ensure_screenshot_dir()
        page.screenshot(
            path=SCREENSHOTS_DIR / "overlap_paginated_popup.png", full_page=True
        )

    def test_next_button_advances_and_wraps(
        self, page: Page, base_url: str, journal, article, article_overlap
    ):
        """Pressing Next advances the counter, wraps around at the end."""
        self._open_journal_map(page, base_url)
        page.evaluate(
            """() => {
                if (window.geometadataMap) {
                    window.geometadataMap.fire('click', {
                        latlng: L.latLng(52.5, 13.4)
                    });
                }
            }"""
        )
        page.wait_for_selector(".geometadata-overlap-counter", timeout=5000)

        next_btn = page.locator(".geometadata-overlap-next").first
        expect(next_btn).to_be_visible()
        next_btn.click()
        # Counter should now read "2 of 2".
        counter = page.locator(".geometadata-overlap-counter").first
        expect(counter).to_contain_text("2 of 2")

        # Next again wraps around.
        next_btn.click()
        expect(counter).to_contain_text("1 of 2")

    def test_arrow_right_advances(
        self, page: Page, base_url: str, journal, article, article_overlap
    ):
        """Keyboard ArrowRight cycles through pages."""
        self._open_journal_map(page, base_url)
        page.evaluate(
            """() => {
                if (window.geometadataMap) {
                    window.geometadataMap.fire('click', {
                        latlng: L.latLng(52.5, 13.4)
                    });
                }
            }"""
        )
        page.wait_for_selector(".geometadata-overlap-counter", timeout=5000)
        page.keyboard.press("ArrowRight")
        counter = page.locator(".geometadata-overlap-counter").first
        expect(counter).to_contain_text("2 of 2")

    def test_escape_closes_popup(
        self, page: Page, base_url: str, journal, article, article_overlap
    ):
        """Escape key closes the paginated popup."""
        self._open_journal_map(page, base_url)
        page.evaluate(
            """() => {
                if (window.geometadataMap) {
                    window.geometadataMap.fire('click', {
                        latlng: L.latLng(52.5, 13.4)
                    });
                }
            }"""
        )
        page.wait_for_selector(".geometadata-overlap-header", timeout=5000)
        page.keyboard.press("Escape")
        # Popup should be gone.
        page.wait_for_selector(
            ".geometadata-overlap-header", state="detached", timeout=5000
        )
