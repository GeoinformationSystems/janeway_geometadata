"""
Geometadata Plugin Logic Module

Shared helper functions for the geometadata plugin.
Following Janeway convention of separating logic from views.
"""

__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__author__ = "Daniel Nüst & KOMET Team"
__license__ = "AGPL v3"

import core.models as core_models
from utils import setting_handler
from utils.logger import get_logger

from plugins.geometadata import plugin_settings

logger = get_logger(__name__)


# =============================================================================
# Plugin Setting Helpers
# =============================================================================


def get_plugin_setting(setting_name, journal=None, repository=None):
    """
    Get a plugin setting value.

    :param setting_name: Name of the setting
    :param journal: Journal context (optional)
    :param repository: Repository context (optional)
    :return: SettingValue object or None

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


def save_plugin_setting(setting_name, value, journal=None, repository=None):
    """
    Save a plugin setting, creating it if it doesn't exist.

    This is more robust than calling setting_handler.save_plugin_setting
    directly, as it handles the case where the setting hasn't been created
    yet (e.g., plugin updated but install_plugins not re-run).

    :param setting_name: Name of the setting
    :param value: Value to save
    :param journal: Journal context (optional)
    :param repository: Repository context (optional)
    :return: SettingValue object or None

    When both journal and repository are None, saves press-level (default)
    settings.
    """
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
        core_models.Setting.objects.get(
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


def is_enabled(journal=None, repository=None):
    """
    Check if geometadata is enabled for this journal/repository.

    :param journal: Journal context (optional)
    :param repository: Repository context (optional)
    :return: Boolean
    """
    setting = get_plugin_setting("enable_geometadata", journal, repository)
    return setting and setting.value == "on"


def get_setting_value(setting_name, journal=None, repository=None, default=""):
    """
    Get a plugin setting value as a string.

    :param setting_name: Name of the setting
    :param journal: Journal context (optional)
    :param repository: Repository context (optional)
    :param default: Default value if setting not found
    :return: String value
    """
    setting = get_plugin_setting(setting_name, journal, repository)
    if setting and setting.value:
        return setting.value
    return default


def is_setting_on(setting_name, journal=None, repository=None, default=True):
    """
    Check if a boolean setting is enabled.

    :param setting_name: Name of the setting
    :param journal: Journal context (optional)
    :param repository: Repository context (optional)
    :param default: Default value if setting not found
    :return: Boolean
    """
    setting = get_plugin_setting(setting_name, journal, repository)
    if not setting:
        return default
    return setting.value == "on"


# =============================================================================
# Display Configuration Helpers
# =============================================================================


def get_display_flags(journal=None, repository=None):
    """
    Return display flag settings for article/preprint landing pages.

    :param journal: Journal context (optional)
    :param repository: Repository context (optional)
    :return: Dict with display flags
    """
    return {
        "show_temporal": is_setting_on("show_article_temporal", journal, repository),
        "show_placenames": is_setting_on(
            "show_article_placenames", journal, repository
        ),
        "show_download_geojson": is_setting_on(
            "show_download_geojson", journal, repository
        ),
    }


def get_tile_config(journal=None, repository=None):
    """
    Return the basemap provider key for leaflet-providers.

    :param journal: Journal context (optional)
    :param repository: Repository context (optional)
    :return: Dict with basemap_provider key
    """
    from plugins.geometadata.views import BASEMAP_PROVIDERS, DEFAULT_BASEMAP

    provider_key = get_setting_value(
        "map_tile_provider", journal, repository, DEFAULT_BASEMAP
    )
    # Validate against known providers; fall back to default
    if provider_key not in BASEMAP_PROVIDERS:
        provider_key = DEFAULT_BASEMAP
    return {"basemap_provider": provider_key}


def get_article_map_colour(journal=None, repository=None):
    """
    Return the colour for article map features.

    :param journal: Journal context (optional)
    :param repository: Repository context (optional)
    :return: Hex colour string
    """
    return get_setting_value("article_map_colour", journal, repository, "#3388ff")


def get_feature_opacity(journal=None, repository=None):
    """
    Return the opacity for map features.

    :param journal: Journal context (optional)
    :param repository: Repository context (optional)
    :return: Float opacity value (0.0 to 1.0)
    """
    opacity_str = get_setting_value("map_feature_opacity", journal, repository, "0.7")
    try:
        return float(opacity_str)
    except (ValueError, TypeError):
        return 0.7


def get_colour_config(journal=None, repository=None):
    """
    Return colour coding configuration for maps.

    :param journal: Journal context (optional)
    :param repository: Repository context (optional)
    :return: Dict with colour configuration
    """
    return {
        "enable_map_colours": is_setting_on(
            "enable_map_colours", journal, repository, default=False
        ),
        "map_colour_palette": get_setting_value(
            "map_colour_palette", journal, repository, ""
        ),
    }


# =============================================================================
# Template Context Builders
# =============================================================================


def build_article_map_context(
    geometadata, article, journal=None, default_lat=0, default_lng=0, default_zoom=2
):
    """
    Build template context for an article map.

    :param geometadata: ArticleGeometadata instance
    :param article: Article instance
    :param journal: Journal context
    :param default_lat: Default map center latitude
    :param default_lng: Default map center longitude
    :param default_zoom: Default map zoom level
    :return: Dict with template context
    """
    import json

    geojson = geometadata.to_geojson()
    centroid = geometadata.get_centroid()

    context = {
        "geometadata": geometadata,
        "geojson": json.dumps(geojson) if geojson else "null",
        "has_geometry": bool(geometadata.geometry_wkt),
        "centroid_lat": centroid[0] if centroid else default_lat,
        "centroid_lng": centroid[1] if centroid else default_lng,
        "default_zoom": default_zoom,
        "content_type": "article",
        "content_id": article.pk,
        "feature_colour": get_article_map_colour(journal=journal),
        "feature_opacity": get_feature_opacity(journal=journal),
    }
    context.update(get_display_flags(journal=journal))
    context.update(get_tile_config(journal=journal))
    return context


def build_preprint_map_context(
    geometadata, preprint, repository=None, default_lat=0, default_lng=0, default_zoom=2
):
    """
    Build template context for a preprint map.

    :param geometadata: PreprintGeometadata instance
    :param preprint: Preprint instance
    :param repository: Repository context
    :param default_lat: Default map center latitude
    :param default_lng: Default map center longitude
    :param default_zoom: Default map zoom level
    :return: Dict with template context
    """
    import json

    geojson = geometadata.to_geojson()
    centroid = geometadata.get_centroid()

    context = {
        "geometadata": geometadata,
        "geojson": json.dumps(geojson) if geojson else "null",
        "has_geometry": bool(geometadata.geometry_wkt),
        "centroid_lat": centroid[0] if centroid else default_lat,
        "centroid_lng": centroid[1] if centroid else default_lng,
        "default_zoom": default_zoom,
        "content_type": "preprint",
        "content_id": preprint.pk,
        "feature_colour": get_article_map_colour(repository=repository),
        "feature_opacity": get_feature_opacity(repository=repository),
    }
    context.update(get_display_flags(repository=repository))
    context.update(get_tile_config(repository=repository))
    return context
