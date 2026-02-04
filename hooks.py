"""
Geometadata Plugin Hooks

Template hooks for integrating geometadata into Janeway pages.
"""

__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__author__ = "Daniel Nüst & KOMET Team"
__license__ = "AGPL v3"

import json

from django.template.loader import render_to_string
from django.urls import reverse

from utils.logger import get_logger

from plugins.geometadata import logic

logger = get_logger(__name__)


# =============================================================================
# Article/Preprint Page Hooks
# =============================================================================


def article_footer_block(context, *args, **kwargs):
    """
    Hook for article_footer_block - displays map on article/preprint pages.

    This hook is called in:
    - themes/*/templates/journal/article.html
    - themes/*/templates/repository/preprint.html
    """
    request = context.get("request")
    if not request:
        return ""

    article = context.get("article")
    preprint = context.get("preprint")

    if article:
        return _render_article_map(request, article)
    elif preprint:
        return _render_preprint_map(request, preprint)

    return ""


def article_sidebar(context, *args, **kwargs):
    """
    Hook for article_sidebar - displays map in article sidebar.

    Provides an alternative to article_footer_block for themes where
    the footer hook is inside a conditional block. Only renders when
    article_content is not present to avoid duplicate maps.
    """
    request = context.get("request")
    if not request:
        return ""

    # Skip if article_content exists - article_footer_block will render
    if context.get("article_content"):
        return ""

    article = args[0] if args else context.get("article")
    if not article:
        return ""

    return _render_article_map(request, article)


def _render_article_map(request, article):
    """Render map for a journal article."""
    from plugins.geometadata.models import ArticleGeometadata

    journal = getattr(request, "journal", None)
    if not journal or not logic.is_enabled(journal=journal):
        return ""

    if not logic.is_setting_on("show_article_map", journal=journal):
        return ""

    try:
        geometadata = ArticleGeometadata.objects.get(article=article)
    except ArticleGeometadata.DoesNotExist:
        return ""

    if not geometadata.has_spatial_data() and not geometadata.has_temporal_data():
        return ""

    # Get default map position
    default_lat = float(
        logic.get_setting_value("default_map_lat", journal=journal) or 0
    )
    default_lng = float(
        logic.get_setting_value("default_map_lng", journal=journal) or 0
    )
    default_zoom = int(
        logic.get_setting_value("default_map_zoom", journal=journal) or 2
    )

    template_context = logic.build_article_map_context(
        geometadata,
        article,
        journal=journal,
        default_lat=default_lat,
        default_lng=default_lng,
        default_zoom=default_zoom,
    )

    return render_to_string(
        "geometadata/article_map.html",
        template_context,
        request=request,
    )


def _render_preprint_map(request, preprint):
    """Render map for a repository preprint."""
    from plugins.geometadata.models import PreprintGeometadata

    repository = getattr(request, "repository", None)
    if not repository or not logic.is_enabled(repository=repository):
        return ""

    if not logic.is_setting_on("show_article_map", repository=repository):
        return ""

    try:
        geometadata = PreprintGeometadata.objects.get(preprint=preprint)
    except PreprintGeometadata.DoesNotExist:
        return ""

    if not geometadata.has_spatial_data() and not geometadata.has_temporal_data():
        return ""

    # Get default map position
    default_lat = float(
        logic.get_setting_value("default_map_lat", repository=repository) or 0
    )
    default_lng = float(
        logic.get_setting_value("default_map_lng", repository=repository) or 0
    )
    default_zoom = int(
        logic.get_setting_value("default_map_zoom", repository=repository) or 2
    )

    template_context = logic.build_preprint_map_context(
        geometadata,
        preprint,
        repository=repository,
        default_lat=default_lat,
        default_lng=default_lng,
        default_zoom=default_zoom,
    )

    return render_to_string(
        "geometadata/article_map.html",
        template_context,
        request=request,
    )


# =============================================================================
# Issue Page Hook
# =============================================================================


def issue_footer_block(context, *args, **kwargs):
    """
    Hook for issue_footer_block - displays aggregated map and temporal
    coverage on issue landing pages.
    """
    request = context.get("request")
    issue = context.get("issue")
    if not request or not issue:
        return ""

    journal = getattr(request, "journal", None)
    if not journal or not logic.is_enabled(journal=journal):
        return ""

    from plugins.geometadata.forms import parse_date_text
    from plugins.geometadata.models import ArticleGeometadata

    geometadata_qs = ArticleGeometadata.objects.filter(
        article__in=issue.articles.all(),
    )

    if not geometadata_qs.exists():
        return ""

    # Aggregate temporal range
    all_dates = []
    all_period_displays = []
    for gm in geometadata_qs:
        all_period_displays.extend(gm.get_temporal_display())
        for period in gm.temporal_periods or []:
            for text in period:
                if text and text.strip():
                    parsed = parse_date_text(text.strip())
                    if parsed:
                        all_dates.append((parsed, text.strip()))

    temporal_start = ""
    temporal_end = ""
    if all_dates:
        all_dates.sort(key=lambda x: x[0])
        temporal_start = all_dates[0][1]
        temporal_end = all_dates[-1][1]
    has_temporal = bool(all_period_displays)

    # Build GeoJSON FeatureCollection
    features = []
    for gm in geometadata_qs.filter(geometry_wkt__isnull=False).exclude(
        geometry_wkt=""
    ):
        geojson = gm.to_geojson()
        if geojson:
            geojson["properties"]["title"] = gm.article.title
            geojson["properties"]["url"] = gm.article.local_url
            geojson["properties"]["id"] = gm.article.pk
            features.append(geojson)

    has_geometry = bool(features)
    if not has_temporal and not has_geometry:
        return ""

    template_context = {
        "issue": issue,
        "has_data": True,
        "has_temporal": has_temporal,
        "temporal_start": temporal_start,
        "temporal_end": temporal_end,
        "has_geometry": has_geometry,
        "geojson_collection": json.dumps(
            {"type": "FeatureCollection", "features": features}
        ),
        "show_issue_temporal": logic.is_setting_on(
            "show_issue_temporal", journal=journal
        ),
        "show_download_geojson": logic.is_setting_on(
            "show_download_geojson", journal=journal
        ),
        "feature_colour": logic.get_article_map_colour(journal=journal),
        "feature_opacity": logic.get_feature_opacity(journal=journal),
    }
    template_context.update(logic.get_tile_config(journal=journal))

    return render_to_string(
        "geometadata/issue_map.html",
        template_context,
        request=request,
    )


# =============================================================================
# Navigation Hook
# =============================================================================


def nav_block(context, *args, **kwargs):
    """
    Hook for nav_block - adds a "Map" link to navigation.
    """
    request = context.get("request")
    if not request:
        return ""

    journal = getattr(request, "journal", None)
    repository = getattr(request, "repository", None)

    if journal and not logic.is_enabled(journal=journal):
        return ""
    if repository and not logic.is_enabled(repository=repository):
        return ""

    if not logic.is_setting_on("enable_map", journal=journal, repository=repository):
        return ""

    # Check if there's any geometadata to show
    from plugins.geometadata.models import ArticleGeometadata, PreprintGeometadata

    has_data = False
    if journal:
        has_data = ArticleGeometadata.objects.filter(
            article__journal=journal,
            geometry_wkt__isnull=False,
        ).exists()
    elif repository:
        has_data = PreprintGeometadata.objects.filter(
            preprint__repository=repository,
            geometry_wkt__isnull=False,
        ).exists()

    if not has_data:
        return ""

    try:
        map_url = reverse("geometadata_map_page")
    except Exception:
        return ""

    return render_to_string(
        "geometadata/nav_link.html",
        {"map_url": map_url},
        request=request,
    )


# =============================================================================
# Head CSS/Meta Tags Hook
# =============================================================================


def inject_head_css(context, *args, **kwargs):
    """
    Hook for base_head_css - injects Leaflet CSS and geospatial meta tags.
    """
    request = context.get("request")
    if not request:
        return ""

    journal = getattr(request, "journal", None)
    repository = getattr(request, "repository", None)

    if journal and not logic.is_enabled(journal=journal):
        return ""
    if repository and not logic.is_enabled(repository=repository):
        return ""

    parts = [render_to_string("geometadata/head_css.html", {}, request=request)]

    meta_html = _inject_meta_tags(context, request)
    if meta_html:
        parts.append(meta_html)

    return "\n".join(parts)


def _inject_meta_tags(context, request):
    """
    Inject geospatial and temporal meta tags into <head> on
    article/preprint detail pages.
    """
    from plugins.geometadata.models import ArticleGeometadata, PreprintGeometadata

    article = context.get("article")
    preprint = context.get("preprint")

    journal = getattr(request, "journal", None)
    repository = getattr(request, "repository", None)

    geometadata = None
    if article:
        try:
            geometadata = ArticleGeometadata.objects.get(article=article)
        except ArticleGeometadata.DoesNotExist:
            pass
    elif preprint:
        try:
            geometadata = PreprintGeometadata.objects.get(preprint=preprint)
        except PreprintGeometadata.DoesNotExist:
            pass

    if not geometadata:
        return ""

    if not geometadata.has_spatial_data() and not geometadata.has_temporal_data():
        return ""

    # Check which embedding formats are enabled
    spatial_enabled = logic.is_setting_on(
        "enable_spatial", journal=journal, repository=repository
    )
    temporal_enabled = logic.is_setting_on(
        "enable_temporal", journal=journal, repository=repository
    )
    embed_dc = logic.is_setting_on(
        "embed_dc_coverage", journal=journal, repository=repository
    )
    embed_geo = logic.is_setting_on(
        "embed_geo_meta", journal=journal, repository=repository
    )
    embed_schema = logic.is_setting_on(
        "embed_schema_spatial", journal=journal, repository=repository
    )
    embed_geojson = logic.is_setting_on(
        "embed_geojson_link", journal=journal, repository=repository, default=False
    )

    # Build GeoJSON
    geojson = geometadata.to_geojson() if spatial_enabled else None
    geojson_str = ""
    geojson_geometry_str = ""
    if geojson:
        geojson_str = json.dumps(geojson, separators=(",", ":"))
        if geojson.get("geometry"):
            geojson_geometry_str = json.dumps(geojson["geometry"])

    # Build temporal intervals
    temporal_intervals = []
    if temporal_enabled and geometadata.temporal_periods:
        for period in geometadata.temporal_periods:
            start = period[0].strip() if period[0] else ""
            end = period[1].strip() if period[1] else ""
            if start and end:
                temporal_intervals.append(f"{start}/{end}")
            elif start:
                temporal_intervals.append(f"{start}/..")
            elif end:
                temporal_intervals.append(f"../{end}")

    # Build GeoJSON download URL
    geojson_download_url = ""
    if embed_geojson and spatial_enabled:
        try:
            if article:
                geojson_download_url = reverse(
                    "geometadata_download_article", args=[article.pk]
                )
            elif preprint:
                geojson_download_url = reverse(
                    "geometadata_preprint_api", args=[preprint.pk]
                )
        except Exception:
            pass

    return render_to_string(
        "geometadata/meta_tags.html",
        {
            "geometadata": geometadata,
            "geojson_str": geojson_str,
            "geojson_geometry_str": geojson_geometry_str,
            "temporal_interval": ", ".join(temporal_intervals),
            "temporal_intervals": temporal_intervals,
            "embed_dc": embed_dc,
            "embed_geo": embed_geo,
            "embed_schema": embed_schema,
            "embed_geojson": embed_geojson,
            "geojson_download_url": geojson_download_url,
            "spatial_enabled": spatial_enabled,
            "temporal_enabled": temporal_enabled,
        },
        request=request,
    )


# =============================================================================
# Submission/Editor Workflow Hooks
# =============================================================================


def submission_review(context, *args, **kwargs):
    """
    Hook for submission_review - displays geometadata summary during
    author submission review.
    """
    request = context.get("request")
    article = context.get("article")
    if not request or not article:
        return ""

    journal = getattr(request, "journal", None)
    if not journal or not logic.is_enabled(journal=journal):
        return ""

    from plugins.geometadata.models import ArticleGeometadata

    try:
        geometadata = ArticleGeometadata.objects.get(article=article)
    except ArticleGeometadata.DoesNotExist:
        return ""

    has_spatial = geometadata.has_spatial_data()
    has_temporal = geometadata.has_temporal_data()

    if not has_spatial and not has_temporal:
        return ""

    return render_to_string(
        "geometadata/submission_review_summary.html",
        {
            "geometadata": geometadata,
            "has_data": True,
            "has_spatial": has_spatial,
            "has_temporal": has_temporal,
            "temporal_display": geometadata.get_temporal_display()
            if has_temporal
            else [],
        },
        request=request,
    )


def edit_article(context, *args, **kwargs):
    """
    Hook for edit_article - displays link to geometadata editing on
    the author article dashboard.
    """
    request = context.get("request")
    article = context.get("article")
    if not request or not article:
        return ""

    journal = getattr(request, "journal", None)
    if not journal or not logic.is_enabled(journal=journal):
        return ""

    from plugins.geometadata.models import ArticleGeometadata

    geometadata = None
    has_geometadata = False
    temporal_display = []

    try:
        geometadata = ArticleGeometadata.objects.get(article=article)
        has_geometadata = (
            geometadata.has_spatial_data() or geometadata.has_temporal_data()
        )
        if geometadata.has_temporal_data():
            temporal_display = geometadata.get_temporal_display()
    except ArticleGeometadata.DoesNotExist:
        pass

    try:
        edit_url = reverse("geometadata_edit_article", args=[article.pk])
    except Exception:
        return ""

    return render_to_string(
        "geometadata/edit_article_link.html",
        {
            "show_link": True,
            "geometadata": geometadata,
            "has_geometadata": has_geometadata,
            "temporal_display": temporal_display,
            "edit_url": edit_url,
        },
        request=request,
    )


def in_review_editor_actions(context, *args, **kwargs):
    """
    Hook for in_review_editor_actions - displays link to geometadata
    editing in the review workflow.
    """
    request = context.get("request")
    article = context.get("article")
    if not request or not article:
        return ""

    journal = getattr(request, "journal", None)
    if not journal or not logic.is_enabled(journal=journal):
        return ""

    try:
        edit_url = reverse("geometadata_edit_article", args=[article.pk])
    except Exception:
        return ""

    return render_to_string(
        "geometadata/editor_action_link.html",
        {"show_link": True, "edit_url": edit_url},
        request=request,
    )
