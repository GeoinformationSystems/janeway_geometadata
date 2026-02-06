"""
Pytest configuration for geometadata E2E tests.

Provides fixtures for Django live server and test data setup.
Uses pytest-playwright for browser automation.
"""

import os

import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import Page

from plugins.geometadata import plugin_settings
from plugins.geometadata.models import ArticleGeometadata
from utils.testing import helpers


# Allow async unsafe operations for Django ORM in Playwright tests
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


class GeometadataLiveServerTestCase(StaticLiveServerTestCase):
    """
    Live server test case with geometadata fixtures.

    Provides a running Django server and pre-populated test data
    for E2E testing with Playwright.
    """

    host = "localhost"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Install plugin settings
        plugin_settings.install()

        # Create core fixtures
        cls.press = helpers.create_press()
        cls.journal, _ = helpers.create_journals()

        # Create editor user
        cls.editor = helpers.create_user(
            "editor@test.com",
            ["editor"],
            cls.journal,
            is_staff=True,
            is_active=True,
        )
        cls.editor.set_password("testpass123")
        cls.editor.save()

        # Create published article with geometadata
        cls.article = helpers.create_article(cls.journal, with_author=True)
        cls.article.stage = "Published"
        cls.article.date_published = "2024-01-15"
        cls.article.save()

        cls.geometadata = ArticleGeometadata.objects.create(
            article=cls.article,
            geometry_wkt="POINT(13.4 52.5)",
            place_name="Berlin",
            admin_units="Berlin, Germany",
            temporal_periods=[["2020-01-01", "2021-12-31"]],
        )

        # Create issue with the article
        cls.issue = helpers.create_issue(
            cls.journal, vol=1, number=1, articles=[cls.article]
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()


@pytest.fixture(scope="module")
def live_server():
    """
    Fixture providing a live Django server for E2E tests.

    Uses Django's StaticLiveServerTestCase to serve static files.
    """
    server = GeometadataLiveServerTestCase("run")
    server.setUpClass()
    try:
        yield server
    finally:
        server.tearDownClass()


@pytest.fixture
def base_url(live_server):
    """Return the base URL of the live server."""
    return live_server.live_server_url


@pytest.fixture
def journal(live_server):
    """Return the test journal."""
    return live_server.journal


@pytest.fixture
def article(live_server):
    """Return the test article with geometadata."""
    return live_server.article


@pytest.fixture
def geometadata(live_server):
    """Return the test geometadata."""
    return live_server.geometadata


@pytest.fixture
def issue(live_server):
    """Return the test issue."""
    return live_server.issue


@pytest.fixture
def editor(live_server):
    """Return the editor user."""
    return live_server.editor


@pytest.fixture
def authenticated_page(page: Page, base_url: str, editor, journal) -> Page:
    """
    Return a page with an authenticated editor session.

    Logs in via the Django login page.
    """
    # Navigate to login page
    login_url = f"{base_url}/login/"
    page.goto(login_url)

    # Fill in credentials
    page.fill('input[name="user_name"]', editor.email)
    page.fill('input[name="user_pass"]', "testpass123")
    page.click('button[type="submit"], input[type="submit"]')

    # Wait for redirect
    page.wait_for_load_state("networkidle")

    return page


@pytest.fixture
def map_selectors():
    """
    Return CSS selectors for map elements.

    Centralizes selector definitions for maintainability.
    """
    return {
        "map_container": "#geometadata-map, .geometadata-map, [data-geometadata-map]",
        "leaflet_map": ".leaflet-container",
        "leaflet_marker": ".leaflet-marker-icon",
        "leaflet_popup": ".leaflet-popup",
        "leaflet_tile": ".leaflet-tile",
        "loading_indicator": ".geometadata-loading",
        "error_message": ".geometadata-error",
        "download_button": 'a[href*="geojson"], button[data-download="geojson"]',
    }
