"""
Pytest configuration for geometadata E2E tests.

Provides fixtures for Django live server and test data setup.
Uses pytest-playwright for browser automation.
"""

import os
from urllib.parse import urlparse

import pytest
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import Page

from plugins.geometadata import plugin_settings
from plugins.geometadata.models import ArticleGeometadata
from utils.testing import helpers


# Allow async unsafe operations for Django ORM in Playwright tests
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

# Force domain-based URL routing for E2E tests (not path-based)
# This must be set before Django processes any requests
settings.URL_CONFIG = "domain"


def _disable_migrations():
    """Disable Django migrations for faster test database creation.

    Uses the same SkipMigrations approach as Janeway's global settings
    (IN_TEST_RUNNER path), creating tables from model definitions instead.
    """
    from collections.abc import Mapping

    from django.conf import settings

    class SkipMigrations(Mapping):
        def __getitem__(self, key):
            return None

        def __contains__(self, key):
            return True

        def __iter__(self):
            return iter("")

        def __len__(self):
            return 1

    settings.MIGRATION_MODULES = SkipMigrations()


class GeometadataLiveServerTestCase(StaticLiveServerTestCase):
    """
    Live server test case with geometadata fixtures.

    Provides a running Django server and pre-populated test data
    for E2E testing with Playwright.

    Data is pre-populated by ``_create_test_data()`` before the server
    starts, so that Django's URL configuration (which loads plugin URLs
    at import time) discovers the installed geometadata plugin.

    Port selection
    --------------
    The live server's port is configurable via ``GEOMETADATA_E2E_PORT``
    (or, equivalently, Django's standard ``DJANGO_LIVE_TEST_SERVER_ADDRESS``).
    When neither is set, ``StaticLiveServerTestCase`` lets the OS assign a
    free port — fine for CI and most local runs, but if you happen to be
    running a non-test development server (e.g. ``make janeway`` on 8000)
    and want to pin the test server to a known port for debugging, export
    ``GEOMETADATA_E2E_PORT=9001`` (or any free port that's not your dev
    server's). Tests address the server via ``base_url``, which is derived
    from ``live_server_url`` — never hardcode 8000.
    """

    host = "localhost"

    @classmethod
    def _resolve_test_port(cls):
        """Return an explicit port override, or None for OS-assigned."""
        port = os.environ.get("GEOMETADATA_E2E_PORT")
        if not port:
            return None
        try:
            return int(port)
        except (TypeError, ValueError):
            return None

    @classmethod
    def setUpClass(cls):
        # Create test data BEFORE starting the server, so that when
        # Django's URL resolver imports include_urls.py (which calls
        # plugin_loader.load()), the geometadata plugin is already
        # registered in the database.
        cls._create_test_data()
        super().setUpClass()

    @classmethod
    def _create_test_data(cls):
        """Populate the test database with fixtures."""
        # Install plugin settings
        plugin_settings.install()

        # Create core fixtures
        # Note: journal domain is updated in live_server fixture after
        # the server starts, to match the actual live server hostname.
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

        # Second article with a polygon that *contains* the Berlin point so
        # a click at (13.4, 52.5) hits both — the overlap-picker test relies
        # on this geometric overlap.
        cls.article_overlap = helpers.create_article(cls.journal, with_author=True)
        cls.article_overlap.stage = "Published"
        cls.article_overlap.date_published = "2024-02-01"
        cls.article_overlap.title = "Overlap test polygon (Germany)"
        cls.article_overlap.save()

        cls.geometadata_overlap = ArticleGeometadata.objects.create(
            article=cls.article_overlap,
            geometry_wkt="POLYGON((5.87 47.27, 15.04 47.27, 15.04 55.06, 5.87 55.06, 5.87 47.27))",
            place_name="Germany",
            admin_units="Germany",
            temporal_periods=[["2024-01-01", "2024-12-31"]],
        )

        # Create issue with both articles
        cls.issue = helpers.create_issue(
            cls.journal, vol=1, number=1, articles=[cls.article, cls.article_overlap]
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()


@pytest.fixture(scope="session")
def django_db_setup():
    """Override pytest-django's database setup.

    The live_server fixture manages its own test database lifecycle,
    so we skip pytest-django's default setup_databases/teardown_databases.
    """
    pass


@pytest.fixture(autouse=True)
def _django_db_helper():
    """Override pytest-django's per-test database management.

    The session-scoped live_server fixture manages the entire database
    lifecycle.  Individual tests access data through Playwright (not
    direct DB queries), so pytest-django's per-test transaction wrapping
    and flush logic must be disabled to keep the test data intact.
    """
    yield


@pytest.fixture(scope="session")
def live_server(django_db_blocker):
    """
    Fixture providing a live Django server for E2E tests.

    Uses Django's StaticLiveServerTestCase to serve static files.
    Manages its own test database lifecycle (skipping migrations and
    using syncdb) so the live server thread has proper access to data.

    The blocker is permanently unblocked for the entire session so
    that the live server thread can access the database freely.
    """
    from django.test.utils import setup_databases, teardown_databases

    from journal.models import Journal

    _disable_migrations()
    django_db_blocker.unblock()

    db_cfg = setup_databases(
        verbosity=0,
        interactive=False,
    )
    # Honor an explicit port override before spinning up the live server.
    # StaticLiveServerTestCase reads DJANGO_LIVE_TEST_SERVER_ADDRESS at class
    # setup time (it parses "host:port"), so we only need to set the env var
    # when the user has chosen a specific port. Otherwise the OS picks one
    # and the server runs on a free port that won't clash with whatever else
    # is on 8000 / 9000 / etc.
    explicit_port = GeometadataLiveServerTestCase._resolve_test_port()
    _restore_env = None
    if explicit_port is not None:
        _restore_env = os.environ.get("DJANGO_LIVE_TEST_SERVER_ADDRESS")
        os.environ["DJANGO_LIVE_TEST_SERVER_ADDRESS"] = (
            f"localhost:{explicit_port}"
        )
    try:
        server = GeometadataLiveServerTestCase("run")
        server.setUpClass()

        # Update journal domain to match the actual live server host.
        # The live_server_url is like "http://127.0.0.1:8000" - we need
        # the host part (127.0.0.1) to match Janeway's domain-based routing.
        parsed = urlparse(server.live_server_url)
        actual_host = parsed.hostname  # e.g., "localhost"
        server.journal.domain = actual_host
        server.journal.save()

        # Also update press domain for press-level pages
        server.press.domain = actual_host
        server.press.save()

        # Refresh cached objects
        server.journal = Journal.objects.get(pk=server.journal.pk)

        try:
            yield server
        finally:
            server.tearDownClass()
    finally:
        teardown_databases(db_cfg, verbosity=0)
        django_db_blocker.restore()
        # Restore the env var so we don't leak the override into subsequent
        # test sessions that share the same process (e.g. pytest --pdb).
        if explicit_port is not None:
            if _restore_env is None:
                os.environ.pop("DJANGO_LIVE_TEST_SERVER_ADDRESS", None)
            else:
                os.environ["DJANGO_LIVE_TEST_SERVER_ADDRESS"] = _restore_env


@pytest.fixture(scope="session")
def base_url(live_server):
    """Return the base URL of the live server."""
    return live_server.live_server_url


@pytest.fixture(scope="session")
def journal(live_server):
    """Return the test journal."""
    return live_server.journal


@pytest.fixture(scope="session")
def article(live_server):
    """Return the test article with geometadata."""
    return live_server.article


@pytest.fixture(scope="session")
def article_overlap(live_server):
    """Return the second test article whose polygon contains article's point."""
    return live_server.article_overlap


@pytest.fixture(scope="session")
def geometadata(live_server):
    """Return the test geometadata."""
    return live_server.geometadata


@pytest.fixture(scope="session")
def issue(live_server):
    """Return the test issue."""
    return live_server.issue


@pytest.fixture(scope="session")
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
        "leaflet_marker": ".leaflet-overlay-pane path.leaflet-interactive",
        "leaflet_popup": ".leaflet-popup",
        "leaflet_tile": ".leaflet-tile",
        "loading_indicator": ".geometadata-loading",
        "error_message": ".geometadata-error",
        "download_button": 'a[href*="geojson"], button[data-download="geojson"]',
    }
