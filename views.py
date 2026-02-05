__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__author__ = "Daniel Nüst & KOMET Team"
__license__ = "AGPL v3"


import json
import os
import re

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods

from journal.models import Issue

from plugins.geometadata import plugin_settings
from plugins.geometadata.forms import ArticleGeometadataForm, PreprintGeometadataForm
from plugins.geometadata.models import ArticleGeometadata, PreprintGeometadata
from security.decorators import editor_user_required
from submission.models import Article
from utils import setting_handler
from utils.logger import get_logger

logger = get_logger(__name__)


# Hooks that require template modifications (not in standard Janeway)
NON_STANDARD_HOOKS = {
    "issue_footer_block": {
        "template_path": "journal/issue_display.html",
        "description": "Issue page map and temporal coverage display",
        "dependent_settings": ["show_issue_temporal"],
    },
}

# Standard hooks that are available in base Janeway
STANDARD_HOOKS = ["article_footer_block", "nav_block", "base_head_css"]


def check_hook_availability(journal=None):
    """
    Check which hooks are available in the current theme's templates.

    Returns a dict mapping hook names to availability info:
    {
        'hook_name': {
            'available': True/False,
            'description': str,
            'dependent_settings': [str, ...],
        }
    }
    """
    result = {}

    # Standard hooks are always available
    for hook_name in STANDARD_HOOKS:
        result[hook_name] = {
            "available": True,
            "description": "",
            "dependent_settings": [],
        }

    # Check non-standard hooks by scanning template files
    for hook_name, hook_info in NON_STANDARD_HOOKS.items():
        available = _check_hook_in_templates(hook_name, hook_info["template_path"])
        result[hook_name] = {
            "available": available,
            "description": hook_info["description"],
            "dependent_settings": hook_info["dependent_settings"],
        }

    return result


def _check_hook_in_templates(hook_name, template_path):
    """
    Check if a hook is called in the specified template across all themes.

    Searches for {% hook 'hook_name' %} or {% hook "hook_name" %} pattern.
    Returns True if found in at least one theme.
    """
    # Pattern to match {% hook 'hook_name' %} or {% hook "hook_name" %}
    pattern = re.compile(r"\{%\s*hook\s+['\"]" + re.escape(hook_name) + r"['\"]\s*%\}")

    # Get the themes directory
    src_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    themes_dir = os.path.join(src_dir, "themes")

    if not os.path.exists(themes_dir):
        return False

    # Check each theme
    for theme_name in os.listdir(themes_dir):
        theme_template = os.path.join(
            themes_dir, theme_name, "templates", template_path
        )
        if os.path.exists(theme_template):
            try:
                with open(theme_template, "r", encoding="utf-8") as f:
                    content = f.read()
                    if pattern.search(content):
                        return True
            except (IOError, OSError):
                continue

    return False


def get_unavailable_settings(hook_availability):
    """
    Return a set of setting names that cannot be used because their
    required hooks are not available.
    """
    unavailable = set()
    for hook_name, info in hook_availability.items():
        if not info["available"]:
            unavailable.update(info.get("dependent_settings", []))
    return unavailable


def _get_plugin_setting(setting_name, journal=None, repository=None):
    """Helper to get plugin settings.

    When both journal and repository are None, returns press-level (default)
    settings.
    """
    plugin = plugin_settings.get_self()
    if not plugin:
        return None

    # Determine context: journal, repository's press, or None (press-level)
    context = journal or (repository.press if repository else None)
    return setting_handler.get_plugin_setting(
        plugin,
        setting_name,
        context,
        create=False,
    )


def _save_plugin_setting(setting_name, value, journal=None, repository=None):
    """
    Helper to save plugin settings, creating the setting if it doesn't exist.

    This is more robust than calling setting_handler.save_plugin_setting
    directly, as it handles the case where the setting hasn't been created
    yet (e.g., plugin updated but install_plugins not re-run).

    When both journal and repository are None, saves press-level (default)
    settings.
    """
    import core.models as core_models

    plugin = plugin_settings.get_self()
    if not plugin:
        return None

    # Determine context: journal, repository's press, or None (press-level)
    context = journal or (repository.press if repository else None)

    plugin_group_name = f"plugin:{plugin.name}"

    # Ensure the setting group exists
    setting_group, _ = core_models.SettingGroup.objects.get_or_create(
        name=plugin_group_name,
    )

    # Check if the setting exists; if not, create it
    try:
        setting = core_models.Setting.objects.get(
            name=setting_name,
            group=setting_group,
        )
    except core_models.Setting.DoesNotExist:
        # Create the setting with sensible defaults
        setting = core_models.Setting.objects.create(
            name=setting_name,
            group=setting_group,
            pretty_name=setting_name.replace("_", " ").title(),
            types="char",
            description="",
            is_translatable=False,
        )
        # Create a default value
        setting_handler.get_or_create_default_setting(setting, default_value="")

    # Now save the value
    return setting_handler.save_plugin_setting(plugin, setting_name, value, context)


# Basemap providers available without API key or registration.
# Keys are leaflet-providers provider strings passed to
# ``L.tileLayer.provider(key)``.  ``label`` is shown in the manager
# UI; ``attribution`` is displayed as a preview next to the dropdown.
BASEMAP_PROVIDERS = {
    "OpenStreetMap.Mapnik": {
        "label": "OpenStreetMap",
        "attribution": (
            '&copy; <a href="https://www.openstreetmap.org/copyright">'
            "OpenStreetMap</a> contributors"
        ),
    },
    "OpenStreetMap.DE": {
        "label": "OpenStreetMap (German style)",
        "attribution": (
            '&copy; <a href="https://www.openstreetmap.org/copyright">'
            "OpenStreetMap</a> contributors"
        ),
    },
    "OpenStreetMap.CH": {
        "label": "OpenStreetMap (Switzerland)",
        "attribution": (
            '&copy; <a href="https://www.openstreetmap.org/copyright">'
            "OpenStreetMap</a> contributors"
        ),
    },
    "OpenStreetMap.France": {
        "label": "OpenStreetMap France",
        "attribution": (
            "&copy; OpenStreetMap France | "
            '&copy; <a href="https://www.openstreetmap.org/copyright">'
            "OpenStreetMap</a> contributors"
        ),
    },
    "OpenStreetMap.HOT": {
        "label": "OpenStreetMap Humanitarian",
        "attribution": (
            '&copy; <a href="https://www.openstreetmap.org/copyright">'
            "OpenStreetMap</a> contributors, "
            'Tiles style by <a href="https://www.hotosm.org/">'
            "Humanitarian OpenStreetMap Team</a> hosted by "
            '<a href="https://openstreetmap.fr/">OpenStreetMap France</a>'
        ),
    },
    "OpenStreetMap.BZH": {
        "label": "OpenStreetMap Bretagne",
        "attribution": (
            '&copy; <a href="https://www.openstreetmap.org/copyright">'
            "OpenStreetMap</a> contributors, "
            'Tiles courtesy of <a href="http://www.openstreetmap.bzh/">'
            "Breton OpenStreetMap Team</a>"
        ),
    },
    "OpenTopoMap": {
        "label": "OpenTopoMap",
        "attribution": (
            'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">'
            "OpenStreetMap</a> contributors, "
            '<a href="http://viewfinderpanoramas.org">SRTM</a> | '
            'Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a>'
        ),
    },
    "CyclOSM": {
        "label": "CyclOSM (cycling)",
        "attribution": (
            '<a href="https://github.com/cyclosm/cyclosm-cartocss-style/releases">'
            "CyclOSM</a> | Map data: "
            '&copy; <a href="https://www.openstreetmap.org/copyright">'
            "OpenStreetMap</a> contributors"
        ),
    },
    "GeoportailFrance.plan": {
        "label": "Geoportail France \u2013 Plan IGN",
        "attribution": (
            '<a target="_blank" href="https://www.geoportail.gouv.fr/">'
            "Geoportail France</a>"
        ),
    },
    "GeoportailFrance.orthos": {
        "label": "Geoportail France \u2013 Aerial Photos",
        "attribution": (
            '<a target="_blank" href="https://www.geoportail.gouv.fr/">'
            "Geoportail France</a>"
        ),
    },
    "TopPlusOpen.Color": {
        "label": "TopPlusOpen Colour (BKG, Germany)",
        "attribution": (
            'Map data: &copy; <a href="http://www.govdata.de/dl-de/by-2-0">'
            "dl-de/by-2-0</a>"
        ),
    },
    "TopPlusOpen.Grey": {
        "label": "TopPlusOpen Grey (BKG, Germany)",
        "attribution": (
            'Map data: &copy; <a href="http://www.govdata.de/dl-de/by-2-0">'
            "dl-de/by-2-0</a>"
        ),
    },
}

# Default provider key
DEFAULT_BASEMAP = "OpenStreetMap.Mapnik"


def _apply_bbox_filter(queryset, request):
    """
    Apply bounding box filter to a geometadata queryset based on request params.

    Supports query parameters: north, south, east, west (all optional).
    Returns records whose bounding box intersects the query bounding box.

    For intersection, the record's bbox must satisfy:
    - record.bbox_south <= query_north (record not entirely above query)
    - record.bbox_north >= query_south (record not entirely below query)
    - record.bbox_west <= query_east (record not entirely east of query)
    - record.bbox_east >= query_west (record not entirely west of query)
    """
    north = request.GET.get("north")
    south = request.GET.get("south")
    east = request.GET.get("east")
    west = request.GET.get("west")

    # Only apply filter if at least one param is provided
    if not any([north, south, east, west]):
        return queryset

    try:
        if north is not None:
            north = float(north)
            queryset = queryset.filter(bbox_south__lte=north)
        if south is not None:
            south = float(south)
            queryset = queryset.filter(bbox_north__gte=south)
        if east is not None:
            east = float(east)
            queryset = queryset.filter(bbox_west__lte=east)
        if west is not None:
            west = float(west)
            queryset = queryset.filter(bbox_east__gte=west)
    except (ValueError, TypeError):
        # Invalid float values — return unfiltered queryset
        pass

    return queryset


def _get_tile_config(journal=None, repository=None):
    """Return the basemap provider key for leaflet-providers.

    Returns a dict with ``basemap_provider`` (a leaflet-providers key
    string such as ``"OpenStreetMap.Mapnik"``) that is consumed by the
    JavaScript via ``L.tileLayer.provider(key)``.
    """
    provider_setting = _get_plugin_setting(
        "map_tile_provider",
        journal=journal,
        repository=repository,
    )
    provider_key = (
        provider_setting.value
        if provider_setting and provider_setting.value
        else DEFAULT_BASEMAP
    )
    # Validate against known providers; fall back to default
    if provider_key not in BASEMAP_PROVIDERS:
        provider_key = DEFAULT_BASEMAP
    return {"basemap_provider": provider_key}


COLOUR_SCHEMES = [
    "Set1",
    "Set2",
    "Set3",
    "Paired",
    "Dark2",
    "Accent",
    "Pastel1",
    "Pastel2",
    "Spectral",
    "RdYlBu",
]

# Default palette used when no stored palette exists yet
_DEFAULT_PALETTE = [
    "#66c2a5",
    "#fc8d62",
    "#8da0cb",
    "#e78ac3",
    "#a6d854",
    "#ffd92f",
    "#e5c494",
    "#b3b3b3",
]


def _get_colour_config(journal=None, repository=None):
    """Return colour-coding configuration from plugin settings.

    The map templates receive ``enable_map_colours`` (bool) and
    ``colour_palette_json`` (a JSON array string of hex colours ready
    to be embedded in a ``data-`` attribute or fed to JS).
    """
    enable_setting = _get_plugin_setting(
        "enable_map_colours", journal=journal, repository=repository
    )
    enabled = not enable_setting or enable_setting.value == "on"
    if not enabled:
        return {"enable_map_colours": False, "colour_palette_json": "[]"}

    palette_setting = _get_plugin_setting(
        "map_colour_palette", journal=journal, repository=repository
    )
    palette_json = ""
    if palette_setting and palette_setting.value:
        palette_json = palette_setting.value
    else:
        # Fallback: resolve from scheme setting
        palette_json = _resolve_palette_json(journal=journal, repository=repository)

    return {
        "enable_map_colours": True,
        "colour_palette_json": palette_json,
    }


def _resolve_palette_json(journal=None, repository=None):
    """Resolve a palette JSON string from the ColorBrewer scheme setting."""
    from plugins.geometadata.static_colorbrewer import COLORBREWER_DATA

    scheme_setting = _get_plugin_setting(
        "map_colour_scheme", journal=journal, repository=repository
    )
    scheme = scheme_setting.value if scheme_setting and scheme_setting.value else "Set2"
    palette = COLORBREWER_DATA.get(scheme, _DEFAULT_PALETTE)
    return json.dumps(palette)


@staff_member_required
def manager(request):
    """
    Plugin manager/settings page.

    Allows administrators to configure the geometadata plugin settings.
    """
    plugin = plugin_settings.get_self()

    if request.method == "POST":
        # Handle settings update
        journal = getattr(request, "journal", None)
        repository = getattr(request, "repository", None)

        if plugin:
            boolean_settings = [
                "enable_geometadata",
                "enable_spatial",
                "enable_temporal",
                "enable_map",
                "require_geometadata",
                "show_article_map",
                "show_article_temporal",
                "show_article_placenames",
                "show_issue_temporal",
                "show_download_geojson",
                "enable_map_colours",
                "embed_dc_coverage",
                "embed_geo_meta",
                "embed_schema_spatial",
                "embed_geojson_link",
                "geocoding_enabled",
            ]
            text_settings = [
                "map_colour_method",
                "map_colour_scheme",
                "map_colour_palette",
                "custom_colours",
                "article_map_colour",
                "map_feature_opacity",
                "default_map_lat",
                "default_map_lng",
                "default_map_zoom",
                "map_tile_provider",
                "geocoding_provider",
                "geocoding_user_agent",
                "geocoding_geonames_username",
            ]

            for setting_name in boolean_settings:
                value = "on" if request.POST.get(setting_name) else ""
                _save_plugin_setting(
                    setting_name,
                    value,
                    journal=journal,
                    repository=repository,
                )

            for setting_name in text_settings:
                value = request.POST.get(setting_name, "")
                _save_plugin_setting(
                    setting_name,
                    value,
                    journal=journal,
                    repository=repository,
                )

            messages.success(request, _("Settings saved successfully."))

        return redirect(reverse("geometadata_manager"))

    # Get current settings
    journal = getattr(request, "journal", None)
    repository = getattr(request, "repository", None)

    settings = {}
    setting_names = [
        "enable_geometadata",
        "enable_spatial",
        "enable_temporal",
        "enable_map",
        "require_geometadata",
        "show_article_map",
        "show_article_temporal",
        "show_article_placenames",
        "show_issue_temporal",
        "show_download_geojson",
        "enable_map_colours",
        "map_colour_method",
        "map_colour_scheme",
        "map_colour_palette",
        "custom_colours",
        "article_map_colour",
        "map_feature_opacity",
        "embed_dc_coverage",
        "embed_geo_meta",
        "embed_schema_spatial",
        "embed_geojson_link",
        "default_map_lat",
        "default_map_lng",
        "default_map_zoom",
        "map_tile_provider",
        "geocoding_enabled",
        "geocoding_provider",
        "geocoding_user_agent",
        "geocoding_geonames_username",
    ]

    for name in setting_names:
        setting = _get_plugin_setting(name, journal=journal, repository=repository)
        settings[name] = setting.value if setting else ""

    # Get statistics
    if journal:
        article_count = ArticleGeometadata.objects.filter(
            article__journal=journal
        ).count()
        total_article_count = Article.objects.filter(journal=journal).count()
        preprint_count = 0
        total_preprint_count = 0
        has_journal = True
        has_repository = False
    elif repository:
        from repository.models import Preprint

        article_count = 0
        total_article_count = 0
        preprint_count = PreprintGeometadata.objects.filter(
            preprint__repository=repository
        ).count()
        total_preprint_count = Preprint.objects.filter(repository=repository).count()
        has_journal = False
        has_repository = True
    else:
        # Press-level view: show both if they exist
        from repository.models import Preprint

        article_count = ArticleGeometadata.objects.count()
        total_article_count = Article.objects.count()
        preprint_count = PreprintGeometadata.objects.count()
        total_preprint_count = Preprint.objects.count()
        # Show sections based on whether content exists
        has_journal = total_article_count > 0
        has_repository = total_preprint_count > 0

    # Count distinct groups for colour coding
    group_count = 0
    site_seed = ""
    if journal:
        from journal.models import Issue

        group_count = (
            Issue.objects.filter(
                journal=journal,
                articles__in=ArticleGeometadata.objects.filter(
                    article__journal=journal,
                    geometry_wkt__isnull=False,
                )
                .exclude(geometry_wkt="")
                .values_list("article", flat=True),
            )
            .distinct()
            .count()
        )
        site_seed = f"{journal.name}-{journal.pk}"
    elif repository:
        group_count = 1  # repositories have no sub-grouping yet
        site_seed = f"{repository.name}-{repository.pk}"

    # Check hook availability
    hook_availability = check_hook_availability(journal=journal)
    unavailable_settings = get_unavailable_settings(hook_availability)

    template_context = {
        "plugin": plugin,
        "settings": settings,
        "article_count": article_count,
        "total_article_count": total_article_count,
        "preprint_count": preprint_count,
        "total_preprint_count": total_preprint_count,
        "has_journal": has_journal,
        "has_repository": has_repository,
        "colour_schemes": COLOUR_SCHEMES,
        "group_count": group_count,
        "site_seed": site_seed,
        "basemap_providers": BASEMAP_PROVIDERS,
        "hook_availability": hook_availability,
        "unavailable_settings": unavailable_settings,
    }

    return render(
        request,
        "geometadata/manager.html",
        template_context,
    )


@staff_member_required
def curation_queue(request):
    """
    Curation queue listing all articles with their geometadata status.
    Editors can work through the back catalogue and add missing geometadata.
    """
    journal = getattr(request, "journal", None)
    repository = getattr(request, "repository", None)

    hide_done = request.GET.get("hide_done") == "1"

    all_items = []

    if journal:
        articles = Article.objects.filter(journal=journal).select_related("section")
        geo_lookup = {}
        for gm in ArticleGeometadata.objects.filter(article__journal=journal):
            geo_lookup[gm.article_id] = gm.has_spatial_data() or gm.has_temporal_data()

        for article in articles.order_by("-date_published", "-pk"):
            all_items.append(
                {
                    "title": article.title,
                    "pk": article.pk,
                    "stage": article.stage,
                    "date_published": article.date_published,
                    "has_geometadata": geo_lookup.get(article.pk, False),
                    "edit_url_name": "geometadata_edit_article",
                    "content_type": "article",
                }
            )

    elif repository:
        from repository.models import Preprint

        preprints = Preprint.objects.filter(repository=repository)
        geo_lookup = {}
        for gm in PreprintGeometadata.objects.filter(
            preprint__repository=repository,
        ):
            geo_lookup[gm.preprint_id] = gm.has_spatial_data() or gm.has_temporal_data()

        for preprint in preprints.order_by("-date_published", "-pk"):
            all_items.append(
                {
                    "title": preprint.title,
                    "pk": preprint.pk,
                    "stage": getattr(preprint, "stage", ""),
                    "date_published": getattr(preprint, "date_published", None),
                    "has_geometadata": geo_lookup.get(preprint.pk, False),
                    "edit_url_name": "geometadata_edit_preprint",
                    "content_type": "preprint",
                }
            )

    total_count = len(all_items)
    done_count = sum(1 for i in all_items if i["has_geometadata"])

    if hide_done:
        display_items = [i for i in all_items if not i["has_geometadata"]]
    else:
        display_items = all_items

    paginator = Paginator(display_items, 50)
    page_number = request.GET.get("page", 1)
    page = paginator.get_page(page_number)

    template_context = {
        "page": page,
        "hide_done": hide_done,
        "total_count": total_count,
        "done_count": done_count,
        "content_type": "article" if journal else "preprint",
    }

    return render(
        request,
        "geometadata/curation_queue.html",
        template_context,
    )


def map_page(request):
    """
    Full-page map view showing all articles/preprints with geometadata.
    Scoped to the current journal or repository.
    """
    journal = getattr(request, "journal", None)
    repository = getattr(request, "repository", None)

    # Check if map page is enabled
    enable_map = _get_plugin_setting(
        "enable_map", journal=journal, repository=repository
    )
    if not enable_map or enable_map.value != "on":
        from django.http import Http404

        raise Http404

    # Get default map settings
    default_lat = _get_plugin_setting(
        "default_map_lat", journal=journal, repository=repository
    )
    default_lng = _get_plugin_setting(
        "default_map_lng", journal=journal, repository=repository
    )
    default_zoom = _get_plugin_setting(
        "default_map_zoom", journal=journal, repository=repository
    )

    # Determine site name for page title
    if journal:
        site_name = journal.name
    elif repository:
        site_name = repository.name
    else:
        site_name = getattr(request, "press", None)
        site_name = site_name.name if site_name else ""

    # Get feature opacity setting
    opacity_setting = _get_plugin_setting(
        "map_feature_opacity", journal=journal, repository=repository
    )
    feature_opacity = 0.7
    if opacity_setting and opacity_setting.value:
        try:
            feature_opacity = float(opacity_setting.value)
        except (ValueError, TypeError):
            pass

    # Check if GeoJSON download is enabled
    show_download = _get_plugin_setting(
        "show_download_geojson", journal=journal, repository=repository
    )
    show_download_geojson = show_download and show_download.value == "on"

    template_context = {
        "default_lat": default_lat.value if default_lat else 0,
        "default_lng": default_lng.value if default_lng else 0,
        "default_zoom": default_zoom.value if default_zoom else 2,
        "api_url": reverse("geometadata_all_api"),
        "scope": "journal" if journal else ("repository" if repository else "press"),
        "site_name": site_name,
        "feature_opacity": feature_opacity,
        "show_download_geojson": show_download_geojson,
        "journal": journal,
        "repository": repository,
    }
    template_context.update(_get_tile_config(journal=journal, repository=repository))
    template_context.update(_get_colour_config(journal=journal, repository=repository))
    # Journal maps group by issue; the colour-group property is "issue"
    if template_context.get("enable_map_colours"):
        template_context["colour_group_prop"] = "issue"

    return render(
        request,
        "geometadata/map_page.html",
        template_context,
    )


def press_map_page(request):
    """
    Press-wide map view showing all articles and preprints across all
    journals and repositories in the Janeway instance.
    """
    # Check if press-wide map is enabled (press-level = no journal context)
    enable_map = _get_plugin_setting("enable_map", journal=None, repository=None)
    if not enable_map or enable_map.value != "on":
        from django.http import Http404

        raise Http404

    # Determine site name for page title
    press = getattr(request, "press", None)
    site_name = press.name if press else ""

    # Get press-level settings for map defaults
    opacity_setting = _get_plugin_setting("map_feature_opacity")
    feature_opacity = 0.7
    if opacity_setting and opacity_setting.value:
        try:
            feature_opacity = float(opacity_setting.value)
        except (ValueError, TypeError):
            pass

    lat_setting = _get_plugin_setting("default_map_lat")
    lng_setting = _get_plugin_setting("default_map_lng")
    zoom_setting = _get_plugin_setting("default_map_zoom")

    default_lat = 0
    default_lng = 0
    default_zoom = 2
    if lat_setting and lat_setting.value:
        try:
            default_lat = float(lat_setting.value)
        except (ValueError, TypeError):
            pass
    if lng_setting and lng_setting.value:
        try:
            default_lng = float(lng_setting.value)
        except (ValueError, TypeError):
            pass
    if zoom_setting and zoom_setting.value:
        try:
            default_zoom = int(zoom_setting.value)
        except (ValueError, TypeError):
            pass

    template_context = {
        "default_lat": default_lat,
        "default_lng": default_lng,
        "default_zoom": default_zoom,
        "api_url": reverse("geometadata_press_api"),
        "scope": "press",
        "site_name": site_name,
        "feature_opacity": feature_opacity,
    }
    template_context.update(_get_tile_config())
    template_context.update(_get_colour_config())
    # Press maps group by journal; the colour-group property is "journal"
    if template_context.get("enable_map_colours"):
        template_context["colour_group_prop"] = "journal"

    return render(
        request,
        "geometadata/map_page.html",
        template_context,
    )


@require_http_methods(["GET"])
def article_geometadata_api(request, article_id):
    """
    API endpoint to get geometadata for a specific article.
    Returns GeoJSON format.
    """
    journal = getattr(request, "journal", None)
    article = get_object_or_404(Article, pk=article_id)

    # Security check: article must belong to current journal
    if journal and article.journal != journal:
        return JsonResponse({"error": "Article not found"}, status=404)

    try:
        geometadata = ArticleGeometadata.objects.get(article=article)
        geojson = geometadata.to_geojson()
        if geojson:
            # Add article metadata to properties
            geojson["properties"]["title"] = article.title
            geojson["properties"]["url"] = article.local_url
            geojson["properties"]["id"] = article.pk
            return JsonResponse(geojson)
        return JsonResponse({"error": "No geometry data"}, status=404)
    except ArticleGeometadata.DoesNotExist:
        return JsonResponse({"error": "No geometadata"}, status=404)


@require_http_methods(["GET"])
def preprint_geometadata_api(request, preprint_id):
    """
    API endpoint to get geometadata for a specific preprint.
    Returns GeoJSON format.
    """
    from repository.models import Preprint

    repository = getattr(request, "repository", None)
    preprint = get_object_or_404(Preprint, pk=preprint_id)

    # Security check: preprint must belong to current repository
    if repository and preprint.repository != repository:
        return JsonResponse({"error": "Preprint not found"}, status=404)

    try:
        geometadata = PreprintGeometadata.objects.get(preprint=preprint)
        geojson = geometadata.to_geojson()
        if geojson:
            # Add preprint metadata to properties
            geojson["properties"]["title"] = preprint.title
            geojson["properties"]["url"] = preprint.local_url
            geojson["properties"]["id"] = preprint.pk
            return JsonResponse(geojson)
        return JsonResponse({"error": "No geometry data"}, status=404)
    except PreprintGeometadata.DoesNotExist:
        return JsonResponse({"error": "No geometadata"}, status=404)


@require_http_methods(["GET"])
def all_geometadata_api(request):
    """
    API endpoint to get all geometadata for a journal/repository.
    Returns GeoJSON FeatureCollection.

    Optional query parameters for bounding box filtering:
    - north: maximum latitude (-90 to 90)
    - south: minimum latitude (-90 to 90)
    - east: maximum longitude (-180 to 180)
    - west: minimum longitude (-180 to 180)

    Records are returned if their bounding box intersects the query box.
    """
    journal = getattr(request, "journal", None)
    repository = getattr(request, "repository", None)

    features = []

    if journal:
        # Get all article geometadata for this journal
        geometadata_qs = (
            ArticleGeometadata.objects.filter(
                article__journal=journal,
                geometry_wkt__isnull=False,
            )
            .exclude(geometry_wkt="")
            .select_related("article")
            .prefetch_related("article__issues")
        )
        geometadata_qs = _apply_bbox_filter(geometadata_qs, request)

        for gm in geometadata_qs:
            geojson = gm.to_geojson()
            if geojson:
                geojson["properties"]["title"] = gm.article.title
                geojson["properties"]["url"] = gm.article.local_url
                geojson["properties"]["id"] = gm.article.pk
                geojson["properties"]["type"] = "article"
                # Group key for colouring: primary issue or first issue
                issue = gm.article.primary_issue or gm.article.issues.first()
                if issue:
                    geojson["properties"]["issue"] = (
                        issue.issue_title or f"Vol. {issue.volume} No. {issue.issue}"
                    )
                features.append(geojson)

    elif repository:
        # Get all preprint geometadata for this repository
        geometadata_qs = (
            PreprintGeometadata.objects.filter(
                preprint__repository=repository,
                geometry_wkt__isnull=False,
            )
            .exclude(geometry_wkt="")
            .select_related("preprint")
        )
        geometadata_qs = _apply_bbox_filter(geometadata_qs, request)

        for gm in geometadata_qs:
            geojson = gm.to_geojson()
            if geojson:
                geojson["properties"]["title"] = gm.preprint.title
                geojson["properties"]["url"] = gm.preprint.local_url
                geojson["properties"]["id"] = gm.preprint.pk
                geojson["properties"]["type"] = "preprint"
                features.append(geojson)

    feature_collection = {
        "type": "FeatureCollection",
        "features": features,
    }

    return JsonResponse(feature_collection)


@require_http_methods(["GET"])
def issue_geometadata_api(request, issue_id):
    """
    API endpoint to get all geometadata for a single issue.
    Returns a GeoJSON FeatureCollection with rich article properties.

    Optional query parameters for bounding box filtering:
    - north: maximum latitude (-90 to 90)
    - south: minimum latitude (-90 to 90)
    - east: maximum longitude (-180 to 180)
    - west: minimum longitude (-180 to 180)

    Records are returned if their bounding box intersects the query box.
    """
    journal = getattr(request, "journal", None)
    issue = get_object_or_404(Issue, pk=issue_id, journal=journal)

    geometadata_qs = (
        ArticleGeometadata.objects.filter(
            article__in=issue.articles.all(),
            geometry_wkt__isnull=False,
        )
        .exclude(geometry_wkt="")
        .select_related("article", "article__journal")
    )
    geometadata_qs = _apply_bbox_filter(geometadata_qs, request)

    features = []
    for gm in geometadata_qs:
        geojson = gm.to_geojson()
        if geojson:
            geojson["properties"] = _build_rich_properties(gm.article, gm)
            features.append(geojson)

    feature_collection = {
        "type": "FeatureCollection",
        "features": features,
    }

    return JsonResponse(feature_collection)


@require_http_methods(["GET"])
def press_geometadata_api(request):
    """
    Press-wide API endpoint returning geometadata from all journals
    and repositories across the entire Janeway instance.
    Returns GeoJSON FeatureCollection.

    Optional query parameters for bounding box filtering:
    - north: maximum latitude (-90 to 90)
    - south: minimum latitude (-90 to 90)
    - east: maximum longitude (-180 to 180)
    - west: minimum longitude (-180 to 180)

    Records are returned if their bounding box intersects the query box.
    """
    features = []

    # All article geometadata across all journals
    article_qs = (
        ArticleGeometadata.objects.filter(
            geometry_wkt__isnull=False,
        )
        .exclude(geometry_wkt="")
        .select_related("article", "article__journal")
    )
    article_qs = _apply_bbox_filter(article_qs, request)

    for gm in article_qs:
        geojson = gm.to_geojson()
        if geojson:
            geojson["properties"]["title"] = gm.article.title
            geojson["properties"]["url"] = gm.article.local_url
            geojson["properties"]["id"] = gm.article.pk
            geojson["properties"]["type"] = "article"
            geojson["properties"]["journal"] = gm.article.journal.name
            features.append(geojson)

    # All preprint geometadata across all repositories
    preprint_qs = (
        PreprintGeometadata.objects.filter(
            geometry_wkt__isnull=False,
        )
        .exclude(geometry_wkt="")
        .select_related("preprint", "preprint__repository")
    )
    preprint_qs = _apply_bbox_filter(preprint_qs, request)

    for gm in preprint_qs:
        geojson = gm.to_geojson()
        if geojson:
            geojson["properties"]["title"] = gm.preprint.title
            geojson["properties"]["url"] = gm.preprint.local_url
            geojson["properties"]["id"] = gm.preprint.pk
            geojson["properties"]["type"] = "preprint"
            geojson["properties"]["repository"] = gm.preprint.repository.name
            features.append(geojson)

    feature_collection = {
        "type": "FeatureCollection",
        "features": features,
    }

    return JsonResponse(feature_collection)


@require_http_methods(["GET"])
def colour_palette_api(request):
    """
    Return the stored colour palette as a JSON array of hex strings.

    Used by the map page JavaScript to colour-code features by group.
    """
    journal = getattr(request, "journal", None)
    repository = getattr(request, "repository", None)

    config = _get_colour_config(journal=journal, repository=repository)
    palette_json = config.get("colour_palette_json", "[]")

    try:
        palette = json.loads(palette_json)
    except (json.JSONDecodeError, TypeError):
        palette = []

    return JsonResponse({"palette": palette})


@editor_user_required
def edit_article_geometadata(request, article_id):
    """
    Editor view to edit geometadata for an article.
    """
    journal = getattr(request, "journal", None)
    article = get_object_or_404(Article, pk=article_id)

    # Security check
    if journal and article.journal != journal:
        messages.error(request, _("Article not found."))
        return redirect("core_dashboard")

    # Get or create geometadata
    geometadata, created = ArticleGeometadata.objects.get_or_create(article=article)

    if request.method == "POST":
        form = ArticleGeometadataForm(request.POST, instance=geometadata)
        if form.is_valid():
            form.save()
            messages.success(request, _("Geometadata saved successfully."))
            return redirect(reverse("geometadata_edit_article", args=[article_id]))
    else:
        form = ArticleGeometadataForm(instance=geometadata)

    # Get default map settings for the widget
    default_lat = _get_plugin_setting("default_map_lat", journal=journal)
    default_lng = _get_plugin_setting("default_map_lng", journal=journal)
    default_zoom = _get_plugin_setting("default_map_zoom", journal=journal)

    template_context = {
        "article": article,
        "form": form,
        "geometadata": geometadata,
        "default_lat": default_lat.value if default_lat else 0,
        "default_lng": default_lng.value if default_lng else 0,
        "default_zoom": default_zoom.value if default_zoom else 2,
    }
    template_context.update(_get_tile_config(journal=journal))

    return render(
        request,
        "geometadata/edit_article.html",
        template_context,
    )


@editor_user_required
def edit_preprint_geometadata(request, preprint_id):
    """
    Editor view to edit geometadata for a preprint.
    """
    from repository.models import Preprint

    repository = getattr(request, "repository", None)
    preprint = get_object_or_404(Preprint, pk=preprint_id)

    # Security check
    if repository and preprint.repository != repository:
        messages.error(request, _("Preprint not found."))
        return redirect("core_dashboard")

    # Get or create geometadata
    geometadata, created = PreprintGeometadata.objects.get_or_create(preprint=preprint)

    if request.method == "POST":
        form = PreprintGeometadataForm(request.POST, instance=geometadata)
        if form.is_valid():
            form.save()
            messages.success(request, _("Geometadata saved successfully."))
            return redirect(reverse("geometadata_edit_preprint", args=[preprint_id]))
    else:
        form = PreprintGeometadataForm(instance=geometadata)

    # Get default map settings for the widget
    default_lat = _get_plugin_setting("default_map_lat", repository=repository)
    default_lng = _get_plugin_setting("default_map_lng", repository=repository)
    default_zoom = _get_plugin_setting("default_map_zoom", repository=repository)

    template_context = {
        "preprint": preprint,
        "form": form,
        "geometadata": geometadata,
        "default_lat": default_lat.value if default_lat else 0,
        "default_lng": default_lng.value if default_lng else 0,
        "default_zoom": default_zoom.value if default_zoom else 2,
    }
    template_context.update(_get_tile_config(repository=repository))

    return render(
        request,
        "geometadata/edit_preprint.html",
        template_context,
    )


def _build_rich_properties(article, geometadata):
    """Build comprehensive metadata properties for GeoJSON export."""
    authors = "; ".join(
        f"{a.last_name}, {a.first_name}" for a in article.frozen_authors()
    )
    return {
        "title": article.title,
        "authors": authors,
        "doi": article.get_doi() or "",
        "doi_url": article.get_doi_url() or "",
        "url": article.url,
        "date_published": str(article.date_published) if article.date_published else "",
        "date_accepted": str(article.date_accepted) if article.date_accepted else "",
        "abstract": article.abstract or "",
        "keywords": ", ".join(str(k) for k in article.keywords.all()),
        "license": str(article.license) if article.license else "",
        "section": str(article.section) if article.section else "",
        "language": article.language or "",
        "peer_reviewed": article.peer_reviewed,
        "journal": article.journal.name if article.journal else "",
        "place_name": geometadata.place_name or "",
        "admin_units": geometadata.admin_units or "",
        "temporal_periods": geometadata.temporal_periods or [],
    }


@require_http_methods(["POST"])
@editor_user_required
def reverse_geocode_api(request):
    """
    API endpoint to reverse-geocode a WKT geometry string.
    Returns place_name and admin_units derived from the geometry.
    """
    journal = getattr(request, "journal", None)
    repository = getattr(request, "repository", None)

    # Check if geocoding is enabled
    enabled = _get_plugin_setting(
        "geocoding_enabled", journal=journal, repository=repository
    )
    if not enabled or enabled.value != "on":
        return JsonResponse({"error": _("Reverse geocoding is disabled.")}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": _("Invalid JSON.")}, status=400)

    wkt = data.get("wkt", "").strip()
    if not wkt:
        return JsonResponse({"error": _("No WKT geometry provided.")}, status=400)

    provider_setting = _get_plugin_setting(
        "geocoding_provider", journal=journal, repository=repository
    )
    provider = (
        provider_setting.value
        if provider_setting and provider_setting.value
        else "nominatim"
    )

    user_agent_setting = _get_plugin_setting(
        "geocoding_user_agent", journal=journal, repository=repository
    )
    user_agent = (
        user_agent_setting.value
        if user_agent_setting and user_agent_setting.value
        else "janeway-geometadata"
    )

    geonames_setting = _get_plugin_setting(
        "geocoding_geonames_username", journal=journal, repository=repository
    )
    geonames_username = (
        geonames_setting.value if geonames_setting and geonames_setting.value else ""
    )

    try:
        from plugins.geometadata.geocoding import reverse_geocode_wkt

        result = reverse_geocode_wkt(
            wkt,
            provider=provider,
            user_agent=user_agent,
            geonames_username=geonames_username,
        )
        return JsonResponse(
            {
                "success": True,
                "place_name": result.get("place_name", ""),
                "admin_units": result.get("admin_units", ""),
            }
        )
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception:
        logger.exception("Reverse geocoding failed")
        return JsonResponse(
            {"error": _("Geocoding failed. Please try again later.")},
            status=500,
        )


@require_http_methods(["GET"])
def download_article_geojson(request, article_id):
    """Download GeoJSON file for a single article's geometadata."""
    journal = getattr(request, "journal", None)
    article = get_object_or_404(Article, pk=article_id)

    if journal and article.journal != journal:
        return JsonResponse({"error": "Article not found"}, status=404)

    try:
        geometadata = ArticleGeometadata.objects.get(article=article)
    except ArticleGeometadata.DoesNotExist:
        return JsonResponse({"error": "No geometadata"}, status=404)

    geojson = geometadata.to_geojson()
    if not geojson:
        return JsonResponse({"error": "No geometry data"}, status=404)

    geojson["properties"] = _build_rich_properties(article, geometadata)

    feature_collection = {
        "type": "FeatureCollection",
        "features": [geojson],
    }

    response = JsonResponse(feature_collection)
    journal_slug = article.journal.code if article.journal else "unknown"

    # Use DOI as identifier if available, otherwise use article ID
    # Sanitize DOI for filename (replace / with _)
    doi = article.get_doi()
    if doi:
        identifier = doi.replace("/", "_")
    else:
        identifier = str(article_id)

    response["Content-Disposition"] = (
        f'attachment; filename="{journal_slug}-geometadata-{identifier}.geojson"'
    )
    return response


@require_http_methods(["GET"])
def download_issue_geojson(request, issue_id):
    """Download GeoJSON file for all articles in an issue."""
    journal = getattr(request, "journal", None)
    issue = get_object_or_404(Issue, pk=issue_id, journal=journal)

    geometadata_qs = (
        ArticleGeometadata.objects.filter(
            article__in=issue.articles.all(),
            geometry_wkt__isnull=False,
        )
        .exclude(geometry_wkt="")
        .select_related("article", "article__journal")
    )

    features = []
    for gm in geometadata_qs:
        geojson = gm.to_geojson()
        if geojson:
            geojson["properties"] = _build_rich_properties(gm.article, gm)
            features.append(geojson)

    if not features:
        return JsonResponse({"error": "No geometry data"}, status=404)

    feature_collection = {
        "type": "FeatureCollection",
        "features": features,
    }

    response = JsonResponse(feature_collection)
    journal_slug = issue.journal.code if issue.journal else "unknown"
    response["Content-Disposition"] = (
        f'attachment; filename="{journal_slug}-geometadata-issue-{issue_id}.geojson"'
    )
    return response


@require_http_methods(["GET"])
def download_journal_geojson(request):
    """Download GeoJSON file for all articles in a journal."""
    journal = getattr(request, "journal", None)
    if not journal:
        return JsonResponse({"error": "Journal context required"}, status=404)

    geometadata_qs = (
        ArticleGeometadata.objects.filter(
            article__journal=journal,
            geometry_wkt__isnull=False,
        )
        .exclude(geometry_wkt="")
        .select_related("article", "article__journal")
        .prefetch_related("article__issues")
    )

    features = []
    for gm in geometadata_qs:
        geojson = gm.to_geojson()
        if geojson:
            props = _build_rich_properties(gm.article, gm)
            # Add issue information
            issue = gm.article.primary_issue or gm.article.issues.first()
            if issue:
                props["issue"] = (
                    issue.issue_title or f"Vol. {issue.volume} No. {issue.issue}"
                )
                props["issue_id"] = issue.pk
            geojson["properties"] = props
            features.append(geojson)

    if not features:
        return JsonResponse({"error": "No geometry data"}, status=404)

    feature_collection = {
        "type": "FeatureCollection",
        "features": features,
    }

    response = JsonResponse(feature_collection)
    response["Content-Disposition"] = (
        f'attachment; filename="{journal.code}-geometadata-all.geojson"'
    )
    return response
