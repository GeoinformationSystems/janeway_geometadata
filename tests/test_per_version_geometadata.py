"""
Tests for the per-version preprint geometadata schema.

The schema and helper introduced for #39 let each ``PreprintVersion``
carry its own ``PreprintGeometadata`` row, alongside a legacy /
canonical row at ``preprint_version=None``. ``logic.get_current_geometadata``
resolves which one to display.
"""

__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__license__ = "AGPL v3"

from django.db import IntegrityError, transaction

from plugins.geometadata import logic
from plugins.geometadata.models import PreprintGeometadata
from plugins.geometadata.tests.base import GeometadataTestCase


def _make_version(preprint, version_number, file=None):
    """Create a PreprintVersion row stub for the given preprint."""
    from repository.models import PreprintFile, PreprintVersion
    from django.utils import timezone

    pf = file
    if pf is None:
        pf = PreprintFile.objects.create(
            preprint=preprint,
            original_filename=f"v{version_number}.pdf",
            mime_type="application/pdf",
            size=0,
        )
    return PreprintVersion.objects.create(
        preprint=preprint,
        file=pf,
        version=version_number,
        date_time=timezone.now(),
        title=f"v{version_number}",
        abstract="",
    )


class PreprintGeometadataSchemaTests(GeometadataTestCase):
    """Direct uniqueness + reverse-accessor checks on the new schema."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.create_repository()
        cls.v1 = _make_version(cls.preprint, 1)
        cls.v2 = _make_version(cls.preprint, 2)

    def test_multiple_rows_per_preprint_allowed(self):
        """One row per (preprint, version) pair — legacy + v1 + v2 = 3 rows."""
        PreprintGeometadata.objects.create(
            preprint=self.preprint, preprint_version=None, geometry_wkt="POINT(0 0)"
        )
        PreprintGeometadata.objects.create(
            preprint=self.preprint, preprint_version=self.v1, geometry_wkt="POINT(1 1)"
        )
        PreprintGeometadata.objects.create(
            preprint=self.preprint, preprint_version=self.v2, geometry_wkt="POINT(2 2)"
        )
        self.assertEqual(
            PreprintGeometadata.objects.filter(preprint=self.preprint).count(), 3
        )

    def test_unique_per_preprint_and_version(self):
        PreprintGeometadata.objects.create(
            preprint=self.preprint,
            preprint_version=self.v1,
            geometry_wkt="POINT(1 1)",
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                PreprintGeometadata.objects.create(
                    preprint=self.preprint,
                    preprint_version=self.v1,
                    geometry_wkt="POINT(2 2)",
                )

    def test_reverse_accessor_is_now_a_manager(self):
        """``preprint.geometadata_set.all()`` returns the manager, not a
        single instance (the OneToOne reverse-accessor was renamed)."""
        PreprintGeometadata.objects.create(
            preprint=self.preprint, preprint_version=None, geometry_wkt=""
        )
        PreprintGeometadata.objects.create(
            preprint=self.preprint, preprint_version=self.v1, geometry_wkt=""
        )
        # Refresh to clear any cached reverse-rel
        self.preprint.refresh_from_db()
        self.assertEqual(self.preprint.geometadata_set.count(), 2)


class CurrentGeometadataResolutionTests(GeometadataTestCase):
    """``logic.get_current_geometadata`` precedence: current → legacy → None."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.create_repository()
        cls.v1 = _make_version(cls.preprint, 1)
        cls.v2 = _make_version(cls.preprint, 2)
        # PreprintVersion ordering picks v2 as current (the QuerySet
        # default for preprintversion_set returns the most-recent first).

    def test_resolves_to_current_version_row_when_present(self):
        PreprintGeometadata.objects.create(
            preprint=self.preprint, preprint_version=self.v1, geometry_wkt="POINT(1 1)"
        )
        v2_row = PreprintGeometadata.objects.create(
            preprint=self.preprint, preprint_version=self.v2, geometry_wkt="POINT(2 2)"
        )
        resolved = logic.get_current_geometadata(self.preprint)
        self.assertEqual(resolved.pk, v2_row.pk)
        self.assertEqual(resolved.geometry_wkt, "POINT(2 2)")

    def test_falls_back_to_legacy_when_current_version_row_missing(self):
        legacy = PreprintGeometadata.objects.create(
            preprint=self.preprint, preprint_version=None, geometry_wkt="POINT(0 0)"
        )
        # v1 has a row but v2 (current) does not — legacy should still win
        # over v1, since the rule is current → legacy → None.
        PreprintGeometadata.objects.create(
            preprint=self.preprint, preprint_version=self.v1, geometry_wkt="POINT(1 1)"
        )
        resolved = logic.get_current_geometadata(self.preprint)
        self.assertEqual(resolved.pk, legacy.pk)

    def test_returns_none_when_no_matching_row_anywhere(self):
        # Only a v1 row exists; current is v2 and there is no legacy row
        PreprintGeometadata.objects.create(
            preprint=self.preprint, preprint_version=self.v1, geometry_wkt="POINT(1 1)"
        )
        self.assertIsNone(logic.get_current_geometadata(self.preprint))

    def test_preprint_with_no_versions_resolves_to_legacy(self):
        # Use a preprint with no PreprintVersion rows; only the legacy slot
        # can apply.
        from repository.models import Preprint, PreprintFile

        bare = Preprint.objects.create(
            repository=self.repository,
            owner=self.editor,
            title="Bare preprint",
            stage="preprint_published",
        )
        legacy = PreprintGeometadata.objects.create(
            preprint=bare, preprint_version=None, geometry_wkt="POINT(0 0)"
        )
        self.assertEqual(logic.get_current_geometadata(bare).pk, legacy.pk)


class EditViewBindsToCurrentVersionTests(GeometadataTestCase):
    """The edit-metadata view binds the form to
    ``(preprint, preprint.current_version)`` so the editor mutates the
    row that the sidebar displays."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.create_repository()
        cls.v1 = _make_version(cls.preprint, 1)
        cls.v2 = _make_version(cls.preprint, 2)

    def test_get_or_create_targets_current_version(self):
        """Mirrors the view's `get_or_create(preprint=..., preprint_version=current)`
        path. After the call there should be exactly one row for the
        (preprint, v2) pair."""
        before = PreprintGeometadata.objects.filter(
            preprint=self.preprint, preprint_version=self.v2
        ).count()
        self.assertEqual(before, 0)

        target_version = self.preprint.current_version
        row, created = PreprintGeometadata.objects.get_or_create(
            preprint=self.preprint, preprint_version=target_version
        )
        self.assertTrue(created)
        self.assertEqual(row.preprint_version_id, self.v2.pk)
