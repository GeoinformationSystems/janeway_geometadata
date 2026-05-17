"""
Base test case for geometadata plugin tests.

Provides common fixtures and setup for all test modules.

The base class is intentionally backward-compatible: ``cls.article`` is left
**clean** (no geometadata record attached) so that subclasses can attach their
own ArticleGeometadata via the standard OneToOne relation. Tests that want a
ready-to-use record should use the :mod:`plugins.geometadata.tests.factories`
helpers, or call ``cls.attach_geometadata(article, kind="...")``.
"""

__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__license__ = "AGPL v3"

from django.test import TestCase

from utils.testing import helpers

from plugins.geometadata import plugin_settings
from plugins.geometadata.tests import factories


class GeometadataTestCase(TestCase):
    """
    Base test case with common fixtures for geometadata tests.

    Provides:

    - ``cls.press`` — Press instance
    - ``cls.journal`` — primary Journal (clean: no issue, no geometadata)
    - ``cls.journal_two`` — secondary Journal for cross-journal / press-wide
      tests (clean)
    - ``cls.editor`` — staff Account with the editor role on ``cls.journal``
    - ``cls.author`` — Account with the author role on ``cls.journal``
    - ``cls.article`` — published Article on ``cls.journal`` with a frozen
      author (no geometadata pre-attached, no issue assignment)

    Lazy fixtures (build on demand to keep the default fast):

    - ``cls.create_repository()`` — repository + a single preprint
    - ``cls.create_shared_issue(articles=...)`` — issue containing the given
      articles, default ``[cls.article]``
    - ``cls.attach_geometadata(article, kind=..., temporal=...)`` — convenience
      wrapper around :func:`factories.make_article_geometadata`
    """

    @classmethod
    def setUpTestData(cls):
        """Set up test data once for the entire test class."""
        # Install plugin settings (idempotent)
        plugin_settings.install()

        # Core fixtures
        cls.press = helpers.create_press()
        cls.journal, cls.journal_two = helpers.create_journals()

        cls.editor = helpers.create_user(
            "editor@test.com",
            ["editor"],
            cls.journal,
            is_staff=True,
            is_active=True,
        )
        cls.author = helpers.create_author(cls.journal)

        cls.article = helpers.create_article(cls.journal, with_author=True)

    # ------------------------------------------------------------------
    # Lazy / opt-in fixtures
    # ------------------------------------------------------------------

    @classmethod
    def create_repository(cls):
        """Create repository and preprint fixtures (call when needed).

        Caches the result on the class so repeated calls are cheap.
        """
        if hasattr(cls, "repository"):
            return cls.repository, cls.preprint

        cls.repository, cls.subject = helpers.create_repository(
            cls.press, [cls.editor], [cls.editor]
        )
        cls.preprint = helpers.create_preprint(
            cls.repository, cls.article.owner, cls.subject
        )
        return cls.repository, cls.preprint

    @classmethod
    def create_shared_issue(cls, articles=None, vol=99, number=1):
        """Create an Issue (vol/number default to 99/1 to avoid collisions
        with subclass-defined issues at vol/number 1/1).
        """
        if articles is None:
            articles = [cls.article]
        return helpers.create_issue(
            cls.journal, vol=vol, number=number, articles=articles
        )

    @classmethod
    def attach_geometadata(
        cls, article, kind="point", temporal="modern_closed", **overrides
    ):
        """Attach an ArticleGeometadata record built from a sample kind."""
        return factories.make_article_geometadata(
            article, kind=kind, temporal=temporal, **overrides
        )

    @classmethod
    def attach_preprint_geometadata(
        cls,
        preprint,
        kind="point",
        temporal="modern_closed",
        preprint_version=None,
        **overrides,
    ):
        """Attach a PreprintGeometadata record built from a sample kind.

        Pass ``preprint_version=<PreprintVersion>`` to bind the row to a
        specific version; the default ``None`` writes to the legacy /
        canonical slot.
        """
        return factories.make_preprint_geometadata(
            preprint,
            kind=kind,
            temporal=temporal,
            preprint_version=preprint_version,
            **overrides,
        )
