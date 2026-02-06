# Geometadata Plugin for Janeway

<div>
<a href="https://projects.tib.eu/komet/en/">
<img src="https://projects.tib.eu/fileadmin/data/komet/img/Logo_Komet_RZ.png" alt="KOMET Logo" title="KOMET Project" width="20%">
</a>
</div>

This plugin adds geospatial and temporal metadata support for articles (journals) and preprints (repositories) in [Janeway](https://github.com/openlibhums/janeway).

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18495577.svg)](https://doi.org/10.5281/zenodo.18495577)

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
- **geomet** ~1.1 (pip, Apache-2.0) - WKT/GeoJSON conversion
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

> **Note:** Issue page features require the `issue_footer_block` hook which is
> not present in standard Janeway. See [Template Requirements](#template-requirements)
> below. The settings page will detect if the hook is missing and disable
> these settings with an explanatory message.

### Downloads

| Setting | Default | Description |
|---|---|---|
| Show GeoJSON Download Links | on | Show download links for geometadata in GeoJSON format on article pages, issue pages, and the journal-wide map page |

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
| Colour Method | `colorbrewer` | How to generate the palette: `colorbrewer` (ColorBrewer schemes), `startrek` (Star Trek themed palettes), `custom` (enter your own colours) |
| Colour Scheme | `Set2` | Palette name for the selected method. Qualitative schemes recommended for categorical data. |
| Custom Colours | _(empty)_ | One HTML colour code per line (e.g., `#3388ff`). Used when method is `custom`. |
| Colour Palette | _(auto)_ | JSON array of hex colours. Auto-populated from the selected method/scheme. |
| Map Feature Colour | `#3388ff` | Colour for map features on article and issue pages (when colour coding is disabled). Enter a hex code or select from the palette. |

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

## Template Requirements

Some plugin features require hooks that are not present in standard Janeway
templates. The plugin's settings page automatically detects which hooks are
available and disables settings that cannot function without them.

### Standard Hooks (No Changes Required)

These hooks are present in all Janeway themes out of the box:

| Hook | Purpose |
|---|---|
| `article_footer_block` | Display maps on article/preprint pages |
| `nav_block` | Add navigation link to map page |
| `base_head_css` | Inject Leaflet CSS and custom styling |
| `in_review_editor_actions` | Display link to geometadata editing in editor review workflow |

### Non-Standard Hooks (Template Modification Required)

These hooks require adding a single line to your theme templates:

| Hook | Template File | Purpose |
|---|---|---|
| `issue_footer_block` | `journal/issue_display.html` | Display aggregated map and temporal coverage on issue pages |

### Adding the issue_footer_block Hook

To enable issue page features, add the following line to your theme's
`journal/issue_display.html` template, typically after the issue article list:

```django
{% load hooks %}{% hook 'issue_footer_block' %}
```

For all three standard themes (OLH, material, clean), the recommended location
is after the `{% include "elements/journal/issue_block.html" %}` line:

```django
{% include "elements/journal/issue_block.html" %}
{% load hooks %}{% hook 'issue_footer_block' %}
```

After adding this line to your theme templates, the issue page settings
(Show Temporal Coverage on Issue Pages) will become available in the
plugin settings.

## Usage

### For Editors

Editors can access geometadata editing from multiple locations:

| Access Point | Description |
|---|---|
| **Review Workflow** | Click "Edit Geometadata" button in the editor actions during article review |
| **Curation Queue** | Navigate to `/plugins/geometadata/curation-queue/` for a list of all articles with their geometadata status |
| **Direct URL** | Access editing directly at `/plugins/geometadata/edit/article/<article_id>/` |
| **Article Archive Page** | The "Edit Geometadata" link appears on the article's archive/management page |

**Editing geometadata:**

1. Navigate to the geometadata editing page via any of the methods above
2. Draw shapes on the map or paste WKT geometry in the text field
3. Use "Lookup Location Names" to auto-fill place name and administrative units
4. Add temporal information (start date, end date) for relevant time periods
5. Save

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
added via the `nav_block` hook when viewing journal or repository pages.

#### Press-Wide Map

A press-wide map showing articles from all journals and repositories is
available at `/plugins/geometadata/press-map/`. This requires the "Enable Map
Page" setting to be turned on at the press level (via
`/plugins/geometadata/manager/` when accessed outside a journal context).

**Note:** The `nav_block` hook only adds navigation links within journal or
repository contexts. To add a map link to your press landing page, manually
add a link to your press theme template:

```django
<a href="{% url 'geometadata_press_map_page' %}">Map</a>
```

Or add it to your press navigation in `themes/<your-theme>/templates/press/nav.html`
or equivalent.

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

### Demo Data

The plugin includes a management command to load demo data for testing and
development. The demo data is based on articles from the
[OJS geoMetadata Demo Journal](https://service.tib.eu/komet/ojs330/index.php/gmdj).

**Loading demo data:**

```bash
# Create the demo journal and load all data (recommended for fresh installs)
python3 manage.py load_geometadata_demo --create-journal

# Load into an existing journal
python3 manage.py load_geometadata_demo --journal-code=geodemo

# Include placeholder PDF galleys
python3 manage.py load_geometadata_demo --create-journal --with-galleys

# Clear existing demo articles before loading
python3 manage.py load_geometadata_demo --journal-code=geodemo --clear-existing
```

**Arguments:**

| Argument | Default | Description |
|---|---|---|
| `--journal-code` | `dqj` | Journal short code to load data into |
| `--create-journal` | off | Create the demo journal from `demo_journal.json` if it doesn't exist |
| `--owner-email` | `admin@example.com` | Email of user to be set as article owner |
| `--with-galleys` | off | Attach a placeholder PDF galley to each article |
| `--clear-existing` | off | Delete existing demo articles before loading (matches by title prefix) |

**What gets created:**

- **Journal** (when using `--create-journal`): "Delta Quadrant Journal" (`dqj`)
- **2 issues**: Vol. 1 No. 1 (12 articles) and Vol. 1 No. 2 (6 articles)
- **18 articles** with titles, abstracts, authors, and keywords
- **Geographic metadata**: WKT geometries (points, polygons, multipoints) and place names
- **Temporal metadata**: Various historical and modern time periods

**Demo data files:**

| File | Description |
|---|---|
| `test/data/demo_journal.json` | Journal metadata (name, code, settings) |
| `test/data/demo_issues.json` | Issue metadata (volume, number, title, description) |
| `test/data/demo_articles.json` | Article data with authors, keywords, and geometadata |
| `test/data/placeholder.pdf` | Placeholder PDF for galleys |

These JSON files can be customized or extended with additional test data.
The default demo journal "Delta Quadrant Journal" (code: `dqj`) is configured
with sensible defaults for testing the geometadata plugin.

### Testing

#### Local Development Setup

For running tests outside of the Janeway Docker environment, create a virtual
environment in the Janeway `src` directory:

```bash
cd path/to/janeway/src

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Janeway and plugin dependencies
pip install -r ../requirements.txt -r ../dev-requirements.txt
pip install -r plugins/geometadata/requirements.txt
```

The `.venv` directory is already in Janeway's `.gitignore`.

**Note:** If you've previously run Janeway with Docker, log files may be owned
by root. Fix with: `sudo chown -R $USER:$USER logs/`

#### Unit Tests

Run the Django unit tests with SQLite (requires environment variables):

```bash
cd src
source .venv/bin/activate  # If not already activated

# Set required environment variables
export DB_VENDOR=sqlite
export JANEWAY_SETTINGS_MODULE=core.janeway_global_settings

# Run all plugin tests
python3 manage.py test plugins.geometadata

# Or run specific test modules
python3 manage.py test plugins.geometadata.tests.test_models
python3 manage.py test plugins.geometadata.tests.test_geojson_validation
```

You can also set these variables inline:

```bash
DB_VENDOR=sqlite JANEWAY_SETTINGS_MODULE=core.janeway_global_settings \
    python3 manage.py test plugins.geometadata
```

#### E2E Tests (Playwright)

The plugin includes end-to-end tests using [Playwright](https://playwright.dev/python/) to verify map functionality in a real browser. These tests check that maps render correctly on article, issue, journal, and press pages.

**Prerequisites:**

```bash
cd src
source .venv/bin/activate  # If not already activated

# Install E2E test dependencies
pip install -r plugins/geometadata/requirements-e2e.txt

# Install Playwright browsers (first time only)
playwright install chromium
```

**Run E2E tests (headless):**

```bash
cd src
source .venv/bin/activate
export DB_VENDOR=sqlite
export JANEWAY_SETTINGS_MODULE=core.janeway_global_settings

pytest plugins/geometadata/tests/e2e/ -v
```

**Run E2E tests with visible browser** (useful for debugging or following along):

```bash
cd src
source .venv/bin/activate
DB_VENDOR=sqlite JANEWAY_SETTINGS_MODULE=core.janeway_global_settings \
    pytest plugins/geometadata/tests/e2e/ -v --headed --slowmo=500
```

The `--headed` flag opens a browser window so you can watch the tests run.
The `--slowmo=500` adds a 500ms delay between actions for easier observation.

**Run a specific test:**

```bash
DB_VENDOR=sqlite JANEWAY_SETTINGS_MODULE=core.janeway_global_settings \
    pytest plugins/geometadata/tests/e2e/test_maps.py::TestJournalMapPage::test_map_page_contains_leaflet_map -v --headed
```

**Test Artifacts:**

When tests run, they generate several artifacts in `tests/e2e/test-results/`:

| Artifact | Description |
|---|---|
| `screenshots/*.png` | Screenshots of map pages (captured for visual verification) |
| `traces/*.zip` | Playwright traces for failed tests (can be viewed with `playwright show-trace`) |

To view a trace file for debugging a failed test:

```bash
playwright show-trace tests/e2e/test-results/traces/test-name-trace.zip
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

## Citation

If you use this plugin in your research or publication workflow, please cite it:

> Nüst, D. (2026). *Geometadata Plugin for Janeway* (v0.1.0). Zenodo. https://doi.org/10.5281/zenodo.18495577

**BibTeX:**

```bibtex
@software{nust_geometadata_2026,
  author       = {Nüst, Daniel},
  title        = {Geometadata Plugin for Janeway},
  year         = 2026,
  publisher    = {Zenodo},
  version      = {v0.1.0},
  doi          = {10.5281/zenodo.18495577},
  url          = {https://doi.org/10.5281/zenodo.18495577}
}
```
