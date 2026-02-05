__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__author__ = "Daniel Nüst & KOMET Team"
__license__ = "AGPL v3"

from django.contrib import admin

from plugins.geometadata.models import ArticleGeometadata, PreprintGeometadata


class AbstractGeometadataAdmin(admin.ModelAdmin):
    """Base admin configuration for geometadata models."""

    list_display = [
        "get_content_title",
        "place_name",
        "has_spatial",
        "has_temporal",
        "updated",
    ]
    list_filter = ["created", "updated"]
    search_fields = ["place_name", "admin_units"]
    readonly_fields = [
        "bbox_north",
        "bbox_south",
        "bbox_east",
        "bbox_west",
        "created",
        "updated",
    ]

    fieldsets = (
        (
            "Spatial Metadata",
            {
                "fields": (
                    "geometry_wkt",
                    "place_name",
                    "admin_units",
                ),
                "description": (
                    "Enter geographic coverage. Geometry should be in WKT format. "
                    "Example: POLYGON((-10 35, 40 35, 40 70, -10 70, -10 35))"
                ),
            },
        ),
        (
            "Bounding Box (auto-calculated)",
            {
                "fields": (
                    ("bbox_north", "bbox_south"),
                    ("bbox_east", "bbox_west"),
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Temporal Metadata",
            {
                "fields": ("temporal_periods",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created", "updated"),
                "classes": ("collapse",),
            },
        ),
    )

    def has_spatial(self, obj):
        return obj.has_spatial_data()

    has_spatial.boolean = True
    has_spatial.short_description = "Has Spatial"

    def has_temporal(self, obj):
        return obj.has_temporal_data()

    has_temporal.boolean = True
    has_temporal.short_description = "Has Temporal"


@admin.register(ArticleGeometadata)
class ArticleGeometadataAdmin(AbstractGeometadataAdmin):
    """Admin for Article geometadata."""

    list_display = ["article"] + AbstractGeometadataAdmin.list_display[1:]
    raw_id_fields = ["article"]

    fieldsets = (
        (
            None,
            {
                "fields": ("article",),
            },
        ),
    ) + AbstractGeometadataAdmin.fieldsets

    def get_content_title(self, obj):
        return obj.article.title[:50] if obj.article else "-"

    get_content_title.short_description = "Article"


@admin.register(PreprintGeometadata)
class PreprintGeometadataAdmin(AbstractGeometadataAdmin):
    """Admin for Preprint geometadata."""

    list_display = ["preprint"] + AbstractGeometadataAdmin.list_display[1:]
    raw_id_fields = ["preprint"]

    fieldsets = (
        (
            None,
            {
                "fields": ("preprint",),
            },
        ),
    ) + AbstractGeometadataAdmin.fieldsets

    def get_content_title(self, obj):
        return obj.preprint.title[:50] if obj.preprint else "-"

    get_content_title.short_description = "Preprint"
