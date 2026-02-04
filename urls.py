__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__author__ = "Daniel Nüst & KOMET Team"
__license__ = "AGPL v3"

from django.urls import path

from plugins.geometadata import views

urlpatterns = [
    # Manager/settings page
    path(
        "manager/",
        views.manager,
        name="geometadata_manager",
    ),
    # Curation queue for back-catalogue work
    path(
        "curation-queue/",
        views.curation_queue,
        name="geometadata_curation_queue",
    ),
    # Full map page showing all articles/preprints
    path(
        "map/",
        views.map_page,
        name="geometadata_map_page",
    ),
    # API endpoints for geometadata
    path(
        "api/article/<int:article_id>/",
        views.article_geometadata_api,
        name="geometadata_article_api",
    ),
    path(
        "api/preprint/<int:preprint_id>/",
        views.preprint_geometadata_api,
        name="geometadata_preprint_api",
    ),
    # API endpoint for all geometadata in a journal/repository
    path(
        "api/all/",
        views.all_geometadata_api,
        name="geometadata_all_api",
    ),
    # API endpoint for all geometadata in a single issue
    path(
        "api/issue/<int:issue_id>/",
        views.issue_geometadata_api,
        name="geometadata_issue_api",
    ),
    # Press-wide API endpoint (all journals and repositories)
    path(
        "api/press/",
        views.press_geometadata_api,
        name="geometadata_press_api",
    ),
    # Colour palette API endpoint
    path(
        "api/colour-palette/",
        views.colour_palette_api,
        name="geometadata_colour_palette_api",
    ),
    # Press-wide map page
    path(
        "press-map/",
        views.press_map_page,
        name="geometadata_press_map_page",
    ),
    # Edit geometadata for an article (for editors)
    path(
        "edit/article/<int:article_id>/",
        views.edit_article_geometadata,
        name="geometadata_edit_article",
    ),
    # Download geometadata as GeoJSON
    path(
        "download/article/<int:article_id>/geojson/",
        views.download_article_geojson,
        name="geometadata_download_article",
    ),
    path(
        "download/issue/<int:issue_id>/geojson/",
        views.download_issue_geojson,
        name="geometadata_download_issue",
    ),
    # Reverse geocoding API
    path(
        "api/reverse-geocode/",
        views.reverse_geocode_api,
        name="geometadata_reverse_geocode_api",
    ),
    # Edit geometadata for a preprint (for editors)
    path(
        "edit/preprint/<int:preprint_id>/",
        views.edit_preprint_geometadata,
        name="geometadata_edit_preprint",
    ),
]
