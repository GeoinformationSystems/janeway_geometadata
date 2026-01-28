# Geometadata Plugin for Janeway

This plugin adds geospatial and temporal metadata support for articles (journals) and preprints (repositories) in [Janeway](https://github.com/openlibhums/janeway).

## Background

This plugin is part of the [KOMET](https://projects.tib.eu/komet/) project ("Kompetenznetzwerk für das Management und die Erschließung von textbasierten Forschungsdaten"), funded by the German Federal Ministry of Education and Research (BMBF).
It brings spatiotemporal metadata capabilities to the Janeway publishing platform, complementing existing work for [Open Journal Systems (OJS)](https://pkp.sfu.ca/software/ojs/).

The plugin builds on concepts and experience from the [geoMetadata](https://github.com/TIBHannover/geoMetadata) plugin for OJS.
While geoMetadata targets OJS, this plugin implements equivalent functionality for Janeway, adapted to its plugin architecture and hook system.
Geospatial metadata collected by this plugin and its OJS counterparts can be aggregated and made discoverable through [OPTIMAP](https://github.com/GeoinformationSystems/optimap), a web portal for geospatial discovery of research articles based on open metadata.

## Features

- **Spatial Metadata**: Store geographic coverage as Well-Known Text (WKT) geometry
- **Temporal Metadata**: Record time periods covered by research
- **Interactive Maps**: Leaflet.js-based map display and editing interface
- **JSON API**: GeoJSON endpoints for map data retrieval
- **Admin Integration**: Edit geometadata from article/preprint management pages
- **Full-Page Map**: Browse all articles/preprints with geographic metadata on a single map

## Installation

1. Clone this repository into the Janeway `src/plugins` folder:

   ```bash
   cd path/to/janeway/src/plugins
   git clone https://github.com/GeoinformationSystems/janeway_geometadata geometadata
   ```

2. From the `src` directory, install the plugin and run migrations:

   ```bash
   python3 manage.py install_plugins geometadata
   python3 manage.py migrate
   ```

3. Restart your server (Apache, Passenger, etc.)
4. Enable the plugin via the Janeway manager interface

## Dependencies

- **Janeway** 1.7+ (tested with current main branch)
- **geopy** ~2.4 (pip, MIT) - reverse geocoding
- **Leaflet.js** 1.9.4 (bundled, BSD-2-Clause) - interactive maps
- **Leaflet.draw** 1.0.4 (bundled, MIT) - drawing tools for geometry editing
- **leaflet-providers** (bundled, BSD-2-Clause) - basemap provider definitions

## Configuration

Settings are configurable per journal/repository via the manager at
`/plugins/geometadata/manager/`. Press-level defaults apply to all
journals/repositories and can be overridden per journal.

### General Settings

| Setting | Default | Description |
|---|---|---|
| Enable Geometadata Collection | off | Master switch for the plugin |
| Enable Spatial Metadata | on | Allow geographic location/area input |
| Enable Temporal Metadata | on | Allow time period input |
| Enable Map Page | on | Enable the aggregated map page (press-wide or journal-wide) |
| Require Geometadata on Submission | off | Require authors to provide geospatial metadata |

### Article Landing Page Display

| Setting | Default | Description |
|---|---|---|
| Show Map on Article Pages | on | Display an interactive map on article/preprint pages |
| Show Temporal Coverage | on | Display temporal coverage (date range) on article pages |
| Show Place Names | on | Display place name labels alongside the map |

### Issue Page Display

| Setting | Default | Description |
|---|---|---|
| Show Temporal Coverage on Issue Pages | on | Display aggregated temporal coverage on issue landing pages |

### Downloads

| Setting | Default | Description |
|---|---|---|
| Show GeoJSON Download Links | on | Show download links for geometadata in GeoJSON format on article and issue pages |

### HTML Metadata Embedding

Controls which metadata formats are embedded in the HTML `<head>` of article
pages for harvesters and search engines. All embedding respects the
Enable Spatial / Enable Temporal toggles — e.g., when temporal metadata is
disabled, Schema.org output omits `temporalCoverage` but still includes
`spatialCoverage`.

| Setting | Default | Description |
|---|---|---|
| Dublin Core Coverage | on | Embed `DC.SpatialCoverage`, `DC.box`, `DC.temporal`, `DC.PeriodOfTime` meta tags |
| geo.* Meta Tags | on | Embed `geo.placename` meta tags |
| Schema.org Coverage (JSON-LD) | on | Embed Schema.org `spatialCoverage`/`temporalCoverage` as JSON-LD |
| GeoJSON Link Element | off | Include a `<link rel="alternate" type="application/geo+json">` to the GeoJSON API endpoint |

### Map Colour Coding

Colour-code geometries on aggregated maps (journal and press map pages) by
issue or journal.

| Setting | Default | Description |
|---|---|---|
| Enable Colour Coding | off | Assign colours to markers and geometries based on their grouping (issue on journal maps, journal on press maps) |
| Colour Method | `scheme` | How to generate the palette: `scheme` (ColorBrewer), `generate` (iwanthue algorithm) |
| Colour Scheme | `Set1` | ColorBrewer palette name (Set1, Set2, Dark2, etc.). Qualitative schemes recommended. |
| Colour Palette | _(auto)_ | JSON array of hex colours. Auto-populated when using a scheme or generating. |

### Map Basemap

The plugin uses [leaflet-providers](https://github.com/leaflet-extras/leaflet-providers)
for basemap selection. Only providers that work without registration or API keys
are included.

| Setting | Default | Description |
|---|---|---|
| Basemap Provider | `OpenStreetMap.Mapnik` | Basemap provider key from leaflet-providers |

**Available basemaps:**

| Provider Key | Description |
|---|---|
| `OpenStreetMap.Mapnik` | Standard OpenStreetMap style |
| `OpenStreetMap.DE` | German OpenStreetMap style |
| `OpenStreetMap.CH` | Swiss OpenStreetMap style (Switzerland only) |
| `OpenStreetMap.France` | French OpenStreetMap style |
| `OpenStreetMap.HOT` | Humanitarian OpenStreetMap Team style |
| `OpenStreetMap.BZH` | Breton OpenStreetMap style (Brittany region) |
| `OpenTopoMap` | Topographic map with contour lines |
| `CyclOSM` | Cycling-focused map style |
| `GeoportailFrance.plan` | French IGN Plan map |
| `GeoportailFrance.orthos` | French IGN aerial photos |
| `TopPlusOpen.Color` | German BKG topographic map (colour) |
| `TopPlusOpen.Grey` | German BKG topographic map (greyscale) |

To preview all basemaps interactively, visit the
[leaflet-providers demo](https://leaflet-extras.github.io/leaflet-providers/preview/).

### Reverse Geocoding

Automatically derive place names and administrative units from drawn geometries
using reverse geocoding services.

| Setting | Default | Description |
|---|---|---|
| Enable Reverse Geocoding | on | Enable the "Lookup Location Names" button on edit pages |
| Geocoding Provider | `nominatim` | Service to use: `nominatim` (OpenStreetMap), `photon`, or `geonames` |
| User Agent | `janeway-geometadata` | Identifies your instance to Nominatim/Photon (required by their usage policies) |
| GeoNames Username | _(empty)_ | Required when using GeoNames provider. Register at [geonames.org](https://www.geonames.org/login) |

### Default Map View

| Setting | Default | Description |
|---|---|---|
| Default Map Latitude | 0 | Default center latitude (-90 to 90) |
| Default Map Longitude | 0 | Default center longitude (-180 to 180) |
| Default Map Zoom | 2 | Default zoom level (1-18) |

## Data Privacy and Tile Servers

When maps are displayed, the user's browser connects directly to an external
tile server to load map tiles (the background map images). **No map tile data
is proxied through the Janeway server** — the browser makes requests to the
tile provider, which will receive the user's IP address, browser user agent,
and the geographic extent of the requested map area.

### Default Tile Server: OpenStreetMap

By default, the plugin uses tile servers operated by the
[OpenStreetMap Foundation](https://osmfoundation.org/) (OSMF), located in the
United Kingdom and other countries. The Janeway site operator has no control
over these connections or OSMF's data processing practices.

If you select a different basemap provider (see [Map Basemap](#map-basemap)),
the browser will connect to that provider instead. Each provider has its own
privacy policy and usage terms.

The use of this map service can be justified under the legitimate interest of
displaying map functions to users of the website (cf. Article 6(1)(f) GDPR).

**OSMF Privacy Policy:** <https://wiki.osmfoundation.org/wiki/Privacy_Policy>

**OSMF Tile Usage Policy:** <https://operations.osmfoundation.org/policies/tiles/>

### Privacy Page Guidance

If your journal or press displays maps to visitors, your data privacy
statement should inform users that:

1. Map tiles are loaded from an external service (identify which one).
2. The user's browser connects directly to that service, transmitting
   the IP address, browser user agent, and the map area viewed.
3. The site operator has no control over the external service's data
   processing.
4. Link to the tile provider's privacy policy.

Example paragraph (adapt to your tile provider and legal requirements):

> This website uses map services provided by the OpenStreetMap Foundation
> (OSMF). When you view a page containing a map, your browser connects to
> servers operated by the OSMF to load map tiles. This transmits your IP
> address and other request data to the OSMF. We have no control over this
> data processing. The legal basis for this processing is our legitimate
> interest in displaying geographic information (Art. 6(1)(f) GDPR). For
> details, see the
> [OSMF Privacy Policy](https://wiki.osmfoundation.org/wiki/Privacy_Policy).

## Usage

### For Editors

1. Navigate to an article or preprint in the manager
2. Click "Edit Geometadata" link
3. Draw shapes on the map or paste WKT geometry
4. Add place name and administrative units
5. Add temporal information (start date, end date, description)
6. Save

### API Endpoints

| Endpoint | Description |
|---|---|
| `/plugins/geometadata/api/article/<pk>.json` | GeoJSON Feature for a single article |
| `/plugins/geometadata/api/preprint/<pk>.json` | GeoJSON Feature for a single preprint |
| `/plugins/geometadata/api/all.json` | GeoJSON FeatureCollection for all articles/preprints in the current journal/repository |
| `/plugins/geometadata/api/issue/<pk>.json` | GeoJSON FeatureCollection for all articles in an issue |
| `/plugins/geometadata/api/press.json` | GeoJSON FeatureCollection across all journals and repositories |
| `/plugins/geometadata/api/palette.json` | Colour palette array for map colour coding |

**Bounding box filtering:** The `all.json`, `issue/<pk>.json`, and `press.json`
endpoints support optional query parameters for spatial filtering:

| Parameter | Description |
|---|---|
| `north` | Maximum latitude (-90 to 90) |
| `south` | Minimum latitude (-90 to 90) |
| `east` | Maximum longitude (-180 to 180) |
| `west` | Minimum longitude (-180 to 180) |

Records are returned if their bounding box **intersects** the query box. All
parameters are optional — you can filter by a single boundary if needed.

Example: `/plugins/geometadata/api/all.json?south=40&north=60&west=-10&east=30`

### Full-Page Map

A public map page showing all articles/preprints with geographic metadata is
available at `/plugins/geometadata/map/`. A navigation link is automatically
added via the `nav_block` hook.

## Data Model

Geometry is stored as WKT (Well-Known Text), a standard text format:

```txt
POINT(-122.4194 37.7749)
POLYGON((-10 35, 40 35, 40 70, -10 70, -10 35))
```

This approach was chosen over GeoDjango/PostGIS for:

- No additional database requirements
- CSV import/export compatibility
- Simpler deployment

Each record includes automatically-calculated bounding box fields
(`bbox_north`, `bbox_south`, `bbox_east`, `bbox_west`) for efficient spatial
queries without requiring PostGIS. A composite B-tree index on these four
fields enables fast bounding-box intersection queries used by the API's
spatial filtering feature.

## Translations (i18n)

This plugin supports Janeway's multilingual system. All user-facing strings
are wrapped with Django's translation functions (`gettext_lazy` in Python,
`{% trans %}` in templates), so the plugin can be displayed in any language
that Janeway supports.

### How Janeway's i18n Works

Janeway uses three layers for internationalization:

1. **Django's standard i18n** (`USE_I18N = True`, `LocaleMiddleware`) —
   translates Python strings and template text via `.po`/`.mo` files
2. **Per-journal language settings** — each journal can configure which
   languages are available and which is the default
   (via `journal_languages` and `default_journal_language` settings)
3. **django-modeltranslation** — translates model field values stored in the
   database (e.g., article titles, CMS page content)

Plugins participate in layer 1: they provide `.po` translation files in a
`locales/` directory. Janeway automatically discovers plugin locale
directories via `plugin_installed_apps.load_plugin_locales()` in
`janeway_global_settings.py`.

### Included Translations

- English (source language, all strings)
- German

### Adding a New Translation

1. **Create the locale directory:**

   ```bash
   mkdir -p src/plugins/geometadata/locales/fr/LC_MESSAGES
   ```

2. **Generate a `.po` file** from the existing source strings. You can either
   copy the German `.po` file as a template and replace the `msgstr` values,
   or use Django's `makemessages` command:

   ```bash
   cd src/plugins/geometadata
   django-admin makemessages -l fr
   ```

   This scans all Python files and templates for `_()` and `{% trans %}`
   strings and creates `locales/fr/LC_MESSAGES/django.po`.

3. **Translate** the `msgstr` entries in the `.po` file. Each entry has a
   `msgid` (English source) and a `msgstr` (your translation). Leave
   `msgstr ""` empty for untranslated strings — Django will fall back to
   English.

4. **Compile** the `.po` file into a binary `.mo` file:

   ```bash
   cd src/plugins/geometadata/locales/fr/LC_MESSAGES
   msgfmt -o django.mo django.po
   ```

   Or use Django's command:

   ```bash
   cd src
   python3 manage.py compilemessages -l fr
   ```

5. **Restart** the server. Django loads `.mo` files at startup.

### When to Update Translations

You need to regenerate/update `.po` files when:

- You add new user-facing strings in Python code (wrapped in `_()` or
  `gettext_lazy()`)
- You add or change `{% trans %}` or `{% blocktrans %}` tags in templates
- You change existing English source strings (the `msgid` values)

After modifying source strings, run `makemessages` again for each language,
then update the translations and recompile with `msgfmt` or
`compilemessages`.

### File Layout

```txt
plugins/geometadata/
└── locales/
    ├── de/
    │   └── LC_MESSAGES/
    │       ├── django.po    # German translations (editable text)
    │       └── django.mo    # Compiled binary (generated, do not edit)
    └── en/
        └── LC_MESSAGES/
            ├── django.po    # English (empty — source strings are English)
            └── django.mo    # Compiled binary
```

### Map UI Translations

Leaflet map controls (zoom buttons, fullscreen toggle, drawing toolbar) are
translated without modifying any vendor JavaScript files. Django `{% trans %}`
strings are passed to JS at runtime via two mechanisms:

- **`data-i18n-*` attributes** on the map container `<div>` — read by
  `geometadata-display.js` and `geometadata-edit.js` to set Leaflet's
  `zoomInTitle`/`zoomOutTitle` and fullscreen control `title`/`titleCancel`.
- **`L.drawLocal` overrides** in a `<script>` block in the edit templates
  (`edit_article.html`, `edit_preprint.html`) — sets all ~35 Leaflet.draw
  toolbar and tooltip strings before the draw control is initialised.

This keeps all vendor files (`leaflet.js`, `leaflet.draw.js`,
`leaflet.fullscreen.js`) unmodified and updatable independently.

### Important Notes for Plugin Developers

- **Python code:** Use `from django.utils.translation import gettext_lazy as _`
  for model fields, form labels, and anything evaluated at import time. Use
  `from django.utils.translation import gettext as _` in views for strings
  evaluated at request time.
- **Templates:** Add `{% load i18n %}` at the top, then wrap strings with
  `{% trans "text" %}` or `{% blocktrans %}...{% endblocktrans %}` for strings
  with variables.
- **`.po` file encoding:** Files must be UTF-8. Literal double-quote characters
  inside translated strings must be escaped as `\"`.
- **Janeway auto-discovers plugin locales:** The directory must be named
  `locales/` (not `locale/`) and placed in the plugin root.

## Development

### Testing

```bash
cd src
python3 manage.py test plugins.geometadata
```

### Code Style

Follow Janeway's code style:

```bash
ruff check src/plugins/geometadata
ruff format src/plugins/geometadata
```

### Updating Bundled Libraries

See [static/geometadata/README.md](static/geometadata/README.md) for details on
the bundled Leaflet libraries, their licenses, and update instructions.

### Potential Core Changes

Several enhancements to Janeway's core would improve geometadata integration.
These are tracked in [Issue #1](https://github.com/GeoinformationSystems/janeway_geometadata/issues/1).

## License

This plugin is part of the KOMET project and is licensed under AGPL v3+,
consistent with Janeway.

## Contributors

- Daniel Nüst, TU Dresden

## Related

- [Janeway Issue #1928](https://github.com/openlibhums/janeway/issues/1928) - Original feature request
- [Janeway Documentation](https://janeway.readthedocs.io/)
- [Janeway Plugin Documentation](https://janeway.readthedocs.io/en/latest/dev/plugins.html)
