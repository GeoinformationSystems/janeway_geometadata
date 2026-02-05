"""
Base test case for geometadata plugin tests.

Provides common fixtures and setup for all test modules.
"""

from django.test import TestCase

from utils.testing import helpers

from plugins.geometadata import plugin_settings


class GeometadataTestCase(TestCase):
    """
    Base test case with common fixtures for geometadata tests.

    Provides:
    - press: Press instance
    - journal: Journal instance
    - article: Published article with owner
    - editor: User with editor role on journal
    - repository: Preprint repository (lazy, create via create_repository())
    - preprint: Preprint instance (lazy, create via create_preprint())
    """

    @classmethod
    def setUpTestData(cls):
        """Set up test data once for the entire test class."""
        # Install plugin settings
        plugin_settings.install()

        # Create core fixtures
        cls.press = helpers.create_press()
        cls.journal, _ = helpers.create_journals()
        cls.editor = helpers.create_user(
            "editor@test.com", ["editor"], cls.journal, is_staff=True, is_active=True
        )
        cls.article = helpers.create_article(cls.journal, with_author=True)

    @classmethod
    def create_repository(cls):
        """Create repository and preprint fixtures (call when needed)."""
        if hasattr(cls, "repository"):
            return cls.repository, cls.preprint

        cls.repository, cls.subject = helpers.create_repository(
            cls.press, [cls.editor], [cls.editor]
        )
        cls.preprint = helpers.create_preprint(
            cls.repository, cls.article.owner, cls.subject
        )
        return cls.repository, cls.preprint
