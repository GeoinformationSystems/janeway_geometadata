"""
Tests for the per-repository plugin setting store and preprint UI surfaces.

Covers gaps surfaced when wiring up repository-scoped behaviour:

1. ``RepositoryPluginSetting`` CRUD and uniqueness.
2. ``logic.get_plugin_setting`` / ``logic.is_setting_on`` /
   ``logic.get_setting_value`` precedence — per-repository override
   beats press-level default; both can coexist for different repos.
3. ``_render_preprint_map`` hook behaviour gated by the per-repo
   ``show_article_map`` setting (off → empty, on → renders).
"""

__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__license__ = "AGPL v3"

from django.test import RequestFactory, override_settings

from plugins.geometadata import hooks, logic
from plugins.geometadata.models import RepositoryPluginSetting
from plugins.geometadata.tests.base import GeometadataTestCase


class RepositoryPluginSettingModelTests(GeometadataTestCase):
    """Direct CRUD + uniqueness checks on the new model."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.create_repository()

    def test_create_and_read(self):
        row = RepositoryPluginSetting.objects.create(
            repository=self.repository,
            setting_name="show_article_map",
            value="on",
        )
        self.assertEqual(row.value, "on")
        fetched = RepositoryPluginSetting.objects.get(
            repository=self.repository, setting_name="show_article_map"
        )
        self.assertEqual(fetched.pk, row.pk)

    def test_unique_per_repository_and_name(self):
        RepositoryPluginSetting.objects.create(
            repository=self.repository,
            setting_name="enable_map",
            value="on",
        )
        with self.assertRaises(Exception):
            # IntegrityError under most backends; the test just needs
            # *any* exception to confirm the uniqueness constraint fires.
            RepositoryPluginSetting.objects.create(
                repository=self.repository,
                setting_name="enable_map",
                value="off",
            )

    def test_update_or_create_round_trip(self):
        row, created = RepositoryPluginSetting.objects.update_or_create(
            repository=self.repository,
            setting_name="embed_wkt",
            defaults={"value": "on"},
        )
        self.assertTrue(created)
        row, created = RepositoryPluginSetting.objects.update_or_create(
            repository=self.repository,
            setting_name="embed_wkt",
            defaults={"value": "off"},
        )
        self.assertFalse(created)
        self.assertEqual(row.value, "off")


class RepositoryPluginSettingPrecedenceTests(GeometadataTestCase):
    """``logic`` helpers route correctly through journal / repo / press."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.create_repository()

    def test_repository_override_beats_press_default_for_is_setting_on(self):
        # No repo row yet — falls back to press-level default (the install
        # default is "on" for show_article_map, but it may have been wiped
        # in this test DB; assert by direct comparison rather than the
        # absolute value).
        press_default_on = logic.is_setting_on(
            "show_article_map", journal=None, repository=None
        )

        # Per-repo override flips the value.
        RepositoryPluginSetting.objects.update_or_create(
            repository=self.repository,
            setting_name="show_article_map",
            defaults={"value": "off" if press_default_on else "on"},
        )

        repo_value = logic.is_setting_on(
            "show_article_map", repository=self.repository
        )
        self.assertNotEqual(press_default_on, repo_value)

    def test_get_setting_value_returns_repository_override(self):
        RepositoryPluginSetting.objects.update_or_create(
            repository=self.repository,
            setting_name="map_tile_provider",
            defaults={"value": "OpenStreetMap.DE"},
        )
        value = logic.get_setting_value(
            "map_tile_provider", repository=self.repository
        )
        self.assertEqual(value, "OpenStreetMap.DE")

    def test_save_plugin_setting_writes_to_repository_store(self):
        result = logic.save_plugin_setting(
            "enable_map",
            "off",
            repository=self.repository,
        )
        self.assertIsInstance(result, RepositoryPluginSetting)
        row = RepositoryPluginSetting.objects.get(
            repository=self.repository, setting_name="enable_map"
        )
        self.assertEqual(row.value, "off")

    def test_save_plugin_setting_journal_does_not_touch_repo_store(self):
        before = RepositoryPluginSetting.objects.filter(
            repository=self.repository
        ).count()
        logic.save_plugin_setting(
            "enable_map",
            "off",
            journal=self.journal,
        )
        after = RepositoryPluginSetting.objects.filter(
            repository=self.repository
        ).count()
        self.assertEqual(before, after)


@override_settings(ROOT_URLCONF="plugins.geometadata.tests.urls")
class PreprintMapHookTests(GeometadataTestCase):
    """Smoke test that ``article_sidebar`` renders the preprint map.

    Fills the gap where no unit test previously exercised
    ``_render_preprint_map`` or the preprint-side scope routing.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.create_repository()
        cls.attach_preprint_geometadata(cls.preprint, kind="point")
        cls.factory = RequestFactory()

    def _request_with_repo(self):
        request = self.factory.get("/")
        request.repository = self.repository
        request.journal = None
        request.press = self.press
        # Stub attributes that Janeway middleware would normally set;
        # context processors consult them during template rendering.
        request.model_content_type = None
        request.site_type = self.repository
        request.user = self.editor
        return request

    def test_sidebar_hook_renders_preprint_map_when_setting_on(self):
        RepositoryPluginSetting.objects.update_or_create(
            repository=self.repository,
            setting_name="enable_geometadata",
            defaults={"value": "on"},
        )
        RepositoryPluginSetting.objects.update_or_create(
            repository=self.repository,
            setting_name="show_article_map",
            defaults={"value": "on"},
        )

        request = self._request_with_repo()
        rendered = hooks.article_sidebar(
            {"request": request},
            self.preprint,
        )
        self.assertIn("geometadata-container", rendered)
        self.assertIn(f"geometadata-preprint-{self.preprint.pk}", rendered)

    def test_sidebar_hook_empty_when_show_article_map_off(self):
        RepositoryPluginSetting.objects.update_or_create(
            repository=self.repository,
            setting_name="enable_geometadata",
            defaults={"value": "on"},
        )
        RepositoryPluginSetting.objects.update_or_create(
            repository=self.repository,
            setting_name="show_article_map",
            defaults={"value": "off"},
        )

        request = self._request_with_repo()
        rendered = hooks.article_sidebar(
            {"request": request},
            self.preprint,
        )
        self.assertEqual(rendered, "")

    def test_footer_hook_skips_preprints(self):
        """``article_footer_block`` no longer renders preprint maps —
        ``article_sidebar`` owns them exclusively."""
        request = self._request_with_repo()
        rendered = hooks.article_footer_block(
            {"request": request, "preprint": self.preprint},
        )
        self.assertEqual(rendered, "")
