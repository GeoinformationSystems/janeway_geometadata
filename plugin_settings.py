__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__author__ = "Daniel Nüst & KOMET Team"
__license__ = "AGPL v3"
__maintainer__ = "KOMET Project"

from django.db.utils import OperationalError

from utils import models, setting_handler
from utils.logger import get_logger

logger = get_logger(__name__)

PLUGIN_NAME = "geometadata"
DISPLAY_NAME = "Geometadata"
DESCRIPTION = (
    "Adds geospatial and temporal metadata support for articles and preprints. "
    "Allows authors to specify geographic coverage and time periods during submission, "
    "and displays interactive maps on article pages."
)
AUTHOR = "Daniel Nüst & KOMET Team (TU Dresden)"
VERSION = "0.1.0"
SHORT_NAME = "geometadata"
MANAGER_URL = "geometadata_manager"
JANEWAY_VERSION = "1.7.0"

# Not a workflow plugin - just adds metadata
IS_WORKFLOW_PLUGIN = False


def get_self():
    """Get the plugin instance from the database."""
    try:
        plugin = models.Plugin.objects.get(name=PLUGIN_NAME)
        return plugin
    except models.Plugin.DoesNotExist:
        return None


def install():
    """Install the plugin and create necessary settings."""
    import core.models as core_models

    # Create or update plugin record
    plugin, created = models.Plugin.objects.get_or_create(
        name=PLUGIN_NAME,
        defaults={
            "enabled": True,
            "version": VERSION,
            "display_name": DISPLAY_NAME,
            "press_wide": True,
        },
    )

    if not created:
        plugin.version = VERSION
        plugin.display_name = DISPLAY_NAME
        plugin.save()
        logger.debug("Plugin updated.")
    else:
        logger.debug("Plugin installed.")

    # Create settings group for the plugin
    plugin_group_name = f"plugin:{PLUGIN_NAME}"
    setting_group, _ = core_models.SettingGroup.objects.get_or_create(
        name=plugin_group_name,
    )

    # Setting: Enable geometadata collection for journals
    setting, _ = core_models.Setting.objects.get_or_create(
        name="enable_geometadata",
        group=setting_group,
        defaults={
            "pretty_name": "Enable Geometadata",
            "types": "boolean",
            "description": (
                "Enable collection and display of geospatial and temporal metadata "
                "for articles in this journal."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="")

    # Setting: Enable spatial metadata
    setting, _ = core_models.Setting.objects.get_or_create(
        name="enable_spatial",
        group=setting_group,
        defaults={
            "pretty_name": "Enable Spatial Metadata",
            "types": "boolean",
            "description": "Allow collection of geographic location/area metadata.",
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="on")

    # Setting: Enable temporal metadata
    setting, _ = core_models.Setting.objects.get_or_create(
        name="enable_temporal",
        group=setting_group,
        defaults={
            "pretty_name": "Enable Temporal Metadata",
            "types": "boolean",
            "description": "Allow collection of time period metadata.",
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="on")

    # Setting: Show map on article page
    setting, _ = core_models.Setting.objects.get_or_create(
        name="show_article_map",
        group=setting_group,
        defaults={
            "pretty_name": "Show Map on Article Page",
            "types": "boolean",
            "description": "Display an interactive map on article pages showing geographic coverage.",
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="on")

    # Setting: Default map center (latitude)
    setting, _ = core_models.Setting.objects.get_or_create(
        name="default_map_lat",
        group=setting_group,
        defaults={
            "pretty_name": "Default Map Center Latitude",
            "types": "text",
            "description": "Default latitude for map center (e.g., 0 for equator).",
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="0")

    # Setting: Default map center (longitude)
    setting, _ = core_models.Setting.objects.get_or_create(
        name="default_map_lng",
        group=setting_group,
        defaults={
            "pretty_name": "Default Map Center Longitude",
            "types": "text",
            "description": "Default longitude for map center (e.g., 0 for prime meridian).",
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="0")

    # Setting: Default map zoom level
    setting, _ = core_models.Setting.objects.get_or_create(
        name="default_map_zoom",
        group=setting_group,
        defaults={
            "pretty_name": "Default Map Zoom Level",
            "types": "text",
            "description": "Default zoom level for maps (1-18, where 1 is world view).",
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="2")

    # Setting: Enable aggregated map page (scoped by context)
    setting, _ = core_models.Setting.objects.get_or_create(
        name="enable_map",
        group=setting_group,
        defaults={
            "pretty_name": "Enable Map Page",
            "types": "boolean",
            "description": (
                "Enable the aggregated map page. At press level this "
                "controls the press-wide map; per-journal overrides "
                "control journal-wide maps."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="on")

    # Setting: Require geometadata during submission
    setting, _ = core_models.Setting.objects.get_or_create(
        name="require_geometadata",
        group=setting_group,
        defaults={
            "pretty_name": "Require Geometadata on Submission",
            "types": "boolean",
            "description": (
                "Require authors to provide geospatial metadata "
                "during article submission."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="")

    # Setting: Show temporal coverage on article pages
    setting, _ = core_models.Setting.objects.get_or_create(
        name="show_article_temporal",
        group=setting_group,
        defaults={
            "pretty_name": "Show Temporal Coverage on Article Pages",
            "types": "boolean",
            "description": (
                "Display temporal coverage (date range) on article landing pages."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="on")

    # Setting: Show place names on article pages
    setting, _ = core_models.Setting.objects.get_or_create(
        name="show_article_placenames",
        group=setting_group,
        defaults={
            "pretty_name": "Show Place Names on Article Pages",
            "types": "boolean",
            "description": (
                "Display place name labels alongside the map on article landing pages."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="on")

    # Setting: Show temporal coverage on issue pages
    setting, _ = core_models.Setting.objects.get_or_create(
        name="show_issue_temporal",
        group=setting_group,
        defaults={
            "pretty_name": "Show Temporal Coverage on Issue Pages",
            "types": "boolean",
            "description": (
                "Display aggregated temporal coverage (date range) on issue landing pages."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="on")

    # Setting: Show GeoJSON download links
    setting, _ = core_models.Setting.objects.get_or_create(
        name="show_download_geojson",
        group=setting_group,
        defaults={
            "pretty_name": "Show GeoJSON Download Links",
            "types": "boolean",
            "description": (
                "Show download links for geometadata in GeoJSON format "
                "on article pages, issue pages, and the journal-wide map page."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="on")

    # HTML metadata embedding settings
    setting, _ = core_models.Setting.objects.get_or_create(
        name="embed_dc_coverage",
        group=setting_group,
        defaults={
            "pretty_name": "Embed Dublin Core Coverage Meta Tags",
            "types": "boolean",
            "description": (
                "Embed DC.SpatialCoverage, DC.box, DC.temporal, and "
                "DC.PeriodOfTime meta tags in article HTML head."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="on")

    setting, _ = core_models.Setting.objects.get_or_create(
        name="embed_geo_meta",
        group=setting_group,
        defaults={
            "pretty_name": "Embed geo.* Meta Tags",
            "types": "boolean",
            "description": ("Embed geo.placename meta tags in article HTML head."),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="on")

    setting, _ = core_models.Setting.objects.get_or_create(
        name="embed_schema_spatial",
        group=setting_group,
        defaults={
            "pretty_name": "Embed Schema.org Spatial/Temporal Coverage",
            "types": "boolean",
            "description": (
                "Embed Schema.org spatialCoverage and temporalCoverage "
                "as JSON-LD in article HTML head. Respects the "
                "enable_spatial and enable_temporal toggles."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="on")

    setting, _ = core_models.Setting.objects.get_or_create(
        name="embed_geojson_link",
        group=setting_group,
        defaults={
            "pretty_name": "Include GeoJSON Link in HTML Head",
            "types": "boolean",
            "description": (
                "Include a <link> element pointing to the GeoJSON API "
                "endpoint in the HTML head of article pages."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="on")

    # Map colour settings
    setting, _ = core_models.Setting.objects.get_or_create(
        name="enable_map_colours",
        group=setting_group,
        defaults={
            "pretty_name": "Enable Map Colour Coding",
            "types": "boolean",
            "description": (
                "Colour-code geometries on aggregated maps (journal map, "
                "press map) by their grouping (e.g. issue or journal)."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="on")

    setting, _ = core_models.Setting.objects.get_or_create(
        name="map_colour_method",
        group=setting_group,
        defaults={
            "pretty_name": "Colour Generation Method",
            "types": "char",
            "description": (
                "Method for generating the map colour palette: "
                "'colorbrewer' selects a preset ColorBrewer scheme, "
                "'startrek' uses Star Trek themed palettes, "
                "'custom' allows entering your own colour codes."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="colorbrewer")

    setting, _ = core_models.Setting.objects.get_or_create(
        name="map_colour_scheme",
        group=setting_group,
        defaults={
            "pretty_name": "ColorBrewer Scheme",
            "types": "char",
            "description": (
                "ColorBrewer colour scheme name (used when method is "
                "'colorbrewer'). Qualitative schemes (Set1, Set2, Dark2, "
                "etc.) are recommended for categorical data."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="Set2")

    setting, _ = core_models.Setting.objects.get_or_create(
        name="map_colour_palette",
        group=setting_group,
        defaults={
            "pretty_name": "Colour Palette",
            "types": "char",
            "description": (
                "JSON array of hex colour strings used on aggregated maps. "
                "Populated automatically from the selected method/scheme. "
                "When more groups exist than palette entries, colours wrap."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="")

    # Custom colours setting (one colour per line)
    setting, _ = core_models.Setting.objects.get_or_create(
        name="custom_colours",
        group=setting_group,
        defaults={
            "pretty_name": "Custom Colours",
            "types": "text",
            "description": (
                "Custom colour palette for maps. Enter one HTML colour code "
                "per line (e.g., #3388ff, rgb(51,136,255))."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="")

    # Map feature colour (for article and issue pages without palette)
    setting, _ = core_models.Setting.objects.get_or_create(
        name="article_map_colour",
        group=setting_group,
        defaults={
            "pretty_name": "Map Feature Colour",
            "types": "char",
            "description": (
                "Colour for map features on article pages and issue pages "
                "(when colour coding is disabled). "
                "Enter a hex colour code or select from the palette."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="#3388ff")

    # Map feature opacity setting
    setting, _ = core_models.Setting.objects.get_or_create(
        name="map_feature_opacity",
        group=setting_group,
        defaults={
            "pretty_name": "Map Feature Opacity",
            "types": "char",
            "description": (
                "Opacity of map features (polygons, lines, markers). "
                "Value between 0.0 (transparent) and 1.0 (opaque). "
                "Lower values help features blend better with darker basemaps."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="0.7")

    # Map basemap provider setting (leaflet-providers key)
    setting, _ = core_models.Setting.objects.get_or_create(
        name="map_tile_provider",
        group=setting_group,
        defaults={
            "pretty_name": "Map Basemap Provider",
            "types": "char",
            "description": (
                "Basemap provider key for leaflet-providers, e.g. "
                "OpenStreetMap.Mapnik, OpenTopoMap, CyclOSM."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(
        setting, default_value="OpenStreetMap.Mapnik"
    )

    # Reverse geocoding settings
    setting, _ = core_models.Setting.objects.get_or_create(
        name="geocoding_enabled",
        group=setting_group,
        defaults={
            "pretty_name": "Enable Reverse Geocoding",
            "types": "boolean",
            "description": (
                "Enable the reverse geocoding feature that allows editors "
                "to automatically derive place names from drawn geometries."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="on")

    setting, _ = core_models.Setting.objects.get_or_create(
        name="geocoding_provider",
        group=setting_group,
        defaults={
            "pretty_name": "Geocoding Provider",
            "types": "char",
            "description": (
                "Reverse geocoding provider: nominatim, photon, or geonames."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="nominatim")

    setting, _ = core_models.Setting.objects.get_or_create(
        name="geocoding_user_agent",
        group=setting_group,
        defaults={
            "pretty_name": "Geocoding User Agent",
            "types": "char",
            "description": (
                "User-Agent string sent to Nominatim or Photon. "
                "Should identify your Janeway instance."
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(
        setting, default_value="janeway-geometadata"
    )

    setting, _ = core_models.Setting.objects.get_or_create(
        name="geocoding_geonames_username",
        group=setting_group,
        defaults={
            "pretty_name": "GeoNames Username",
            "types": "char",
            "description": (
                "GeoNames API username (required when provider is 'geonames'). "
                "Register at https://www.geonames.org/login"
            ),
            "is_translatable": False,
        },
    )
    setting_handler.get_or_create_default_setting(setting, default_value="")

    logger.info(f"Geometadata plugin v{VERSION} installation complete.")


def hook_registry():
    """Register hooks for template integration."""
    try:
        return {
            # Display map on article pages (journal articles)
            "article_footer_block": {
                "module": "plugins.geometadata.hooks",
                "function": "article_footer_block",
                "name": PLUGIN_NAME,
            },
            # Display map in article sidebar (alternative to footer for themes
            # where footer hook is inside a conditional block)
            "article_sidebar": {
                "module": "plugins.geometadata.hooks",
                "function": "article_sidebar",
                "name": PLUGIN_NAME,
            },
            # Display map on preprint pages (repository)
            # Note: Uses same hook name - works for both article and preprint templates
            # Display map on issue pages (journal issues)
            "issue_footer_block": {
                "module": "plugins.geometadata.hooks",
                "function": "issue_footer_block",
                "name": PLUGIN_NAME,
            },
            # Add navigation link for map page
            "nav_block": {
                "module": "plugins.geometadata.hooks",
                "function": "nav_block",
                "name": PLUGIN_NAME,
            },
            # Inject CSS in head
            "base_head_css": {
                "module": "plugins.geometadata.hooks",
                "function": "inject_head_css",
                "name": PLUGIN_NAME,
            },
            # Display geometadata summary during submission review
            "submission_review": {
                "module": "plugins.geometadata.hooks",
                "function": "submission_review",
                "name": PLUGIN_NAME,
            },
            # Display link to geometadata editing on article dashboard
            "edit_article": {
                "module": "plugins.geometadata.hooks",
                "function": "edit_article",
                "name": PLUGIN_NAME,
            },
            # Display link to geometadata editing in review workflow
            "in_review_editor_actions": {
                "module": "plugins.geometadata.hooks",
                "function": "in_review_editor_actions",
                "name": PLUGIN_NAME,
            },
        }
    except OperationalError:
        # Database not yet created
        return {}
    except Exception:
        return {}
