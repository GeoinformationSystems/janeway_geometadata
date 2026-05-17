# Changelog

All notable changes to the Geometadata plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Per-version preprint geometadata.** `PreprintGeometadata` gains a
  nullable `preprint_version` FK so each `PreprintVersion` can carry its
  own geometry and temporal periods, alongside the existing legacy /
  canonical slot at `preprint_version=None`. `unique_together` on
  `(preprint, preprint_version)` enforces one row per pair.
  `logic.get_current_geometadata(preprint)` resolves which row to
  display via the rule: current-version row → legacy row → `None`.
  Display surfaces (sidebar map, embedded HTML metadata, JSON API
  endpoints) and the press / repository aggregated maps all route
  through the helper so they show the current version's footprint.
  The edit-metadata view binds the form to the current version's row
  (creating it on demand) so editors mutate the same row the sidebar
  displays. Demo loader extended with a `versions[].geometadata` block
  in `demo_preprints.json`; the Berlin sensors and European bison
  preprints carry concrete per-version geometries showing real
  refinement across versions. Closes #39.

### Changed

- `PreprintGeometadata.preprint` becomes a `ForeignKey` (was
  `OneToOneField`); the reverse accessor on `Preprint` is renamed from
  `.geometadata` (the OneToOne reverse-rel) to `.geometadata_set` (the
  ForeignKey manager). Callers that need a single row should use
  `logic.get_current_geometadata(preprint)`.

## [0.2.0] - 2026-05-15

### Added

- **Per-repository plugin setting store**
  (`RepositoryPluginSetting` model + migration
  `0003_add_repository_plugin_setting`). Core Janeway's
  `setting_handler` keys `SettingValue` rows on `Journal`, so
  repositories previously had no first-class place to carry plugin
  toggle state. The new model stores
  `(repository, setting_name) → value` rows. `logic.get_plugin_setting`
  now resolves scopes in order: per-journal `SettingValue` →
  `RepositoryPluginSetting` → press-level default. `views.py`
  setting helpers collapse to thin `logic` delegates so the
  precedence rule lives in one place. The manager page renders
  correctly under repository scope at
  `/<repo-short-name>/plugins/geometadata/manager/`: the Issue
  Page Display section is hidden, the issue-hook warning is
  suppressed, and the intro paragraph names the scope and
  explains the per-repo store. POST writes route to
  `RepositoryPluginSetting.update_or_create` rather than to
  journal `SettingValue`. The demo loader gains
  `_configure_repository_plugin_settings` so `geo-repo` carries
  explicit toggle values.
- **Preprint map in the sidebar** — UI parity with the journal
  article landing page. The OLH and Material preprint templates
  fire `{% hook 'article_sidebar' preprint %}` inside their
  sidebar columns; the `article_sidebar` hook function resolves
  both `Article` and `Preprint` from the positional argument or
  context. `article_footer_block` no longer renders preprint
  maps. Third-party preprint themes that previously fired only
  `article_footer_block` now need to also fire `article_sidebar`
  — surface change documented in the README.
- **Prose temporal/place sentences in the sidebar.** Instead of
  bare list items, the article/preprint sidebar reads
  *"This preprint covers the time period from 2023-06-01 to
  2023-08-31."* and *"The geographic coverage of this preprint
  is **Berlin, Germany**."* Multiple periods render as a lead-in
  sentence followed by a list. New
  `AbstractGeometadata.get_temporal_prose` returns begin/end-aware
  fragments (`from X to Y` / `from X onwards` / `up to Y`).
- **Demo loader: preprint dimensions** in `load_geometadata_demo`.
  - Version history via `versions` in `demo_preprints.json`. Each
    entry materialises as a `PreprintVersion` row with its own
    title / abstract / date_time. A v1 is auto-created for every
    preprint that doesn't declare its own versions.
  - Promotion linkage via `linked_article_title`. Resolves to an
    existing demo `Article` by exact (then startswith) title
    match and sets `Preprint.article`. The link self-heals across
    `--clear-existing` reruns when the linked article is
    re-created with a new PK.
  - Mixed-stage preprints via `stage` on a preprint entry. Two
    new in-review preprints appear in the moderation queue.
  - Preprint-side loader is now idempotent end-to-end:
    `Preprint.objects.get_or_create` replaces the prior
    skip-if-exists guard. Article creation remains opt-in via
    `--clear-existing`.
- **ISO 19139 XML embedding** in article and preprint HTML head,
  controlled by a new `embed_iso19139` plugin setting (default
  on). Emits a `<script type="application/xml"
  id="geometadata-iso19139">` block with a `gmd:EX_Extent`
  fragment (`EX_GeographicDescription` with place name,
  `EX_GeographicBoundingBox`, and one `gml:TimePeriod` per
  stored temporal period). Open-ended periods use
  `gml:indeterminatePosition="unknown"`. Closes #4.
- **WKT meta tag** in article and preprint HTML head, controlled
  by a new `embed_wkt` plugin setting (default on). Emits
  `<meta name="DC.SpatialCoverage" scheme="WKT" content="...">`
  alongside the existing GeoJSON variant. The DC schema link is
  now emitted whenever any DC-style tag (DC or WKT) is enabled.
  Closes #27.
- **Overlap picker** on aggregated maps (journal/press/issue).
  When a map click hits multiple article geometries at the same
  location, open a paginated popup with wrap-around prev/next
  chrome (and ArrowLeft / ArrowRight / Escape keyboard
  navigation) so readers can page through every overlapping
  article. Geometry hit-testing supports Point / LineString /
  Polygon (with holes) / Multi* / GeometryCollection in pixel
  space. Adapted from the OJS geoMetadata plugin's
  `js/lib/map_overlap.js` (with the marker / line-string
  hit-test fixes from
  [PR #162 commit `d486562`](https://github.com/TIBHannover/geoMetadata/commit/d486562)),
  itself inspired by OPTIMAP's `MapInteractionManager`.
  Controlled by a new `enable_overlap_picker` plugin setting
  (default on). Closes #14.
- **Test coverage for the per-repo store and preprint UI surfaces.**
  New `tests/test_repository_settings.py` covers
  `RepositoryPluginSetting` CRUD + uniqueness, scope precedence
  in `logic.get_plugin_setting` / `is_setting_on` /
  `get_setting_value` / `save_plugin_setting`, and the preprint
  sidebar hook (renders when the setting is on, empty when off;
  `article_footer_block` skips preprints).

### Fixed

- **Repository / preprint map rendering** previously failed
  end-to-end. `_get_plugin_setting` (in `views.py`) and
  `get_plugin_setting` / `save_plugin_setting` (in `logic.py`)
  used `repository.press` (a `Press` instance) as a fallback
  when only a repository was supplied. Core's `setting_handler`
  keys `SettingValue` rows on `Journal`, so the downstream
  filter raised `ValueError: Cannot query "<Press>": Must be
  "Journal" instance.` This crashed the repository map page
  (`/<repo>/plugins/geometadata/map/` → HTTP 500) and silently
  short-circuited the preprint detail hook. Routing now goes
  through `RepositoryPluginSetting` (see Added above) and falls
  back to the press-level default when no per-repo row exists.
- **Preprint download links 500'd** when version files were
  created by the demo loader because `PreprintFile.file` was
  empty. The loader now copies `test/data/placeholder.pdf` into
  `PreprintFile.file`'s storage once at a stable shared name
  (`repos/_demo_placeholder.pdf`) and points every demo
  `PreprintFile` row at it — single file on disk, unchanged git
  footprint. A heal-pass on every loader run rewrites
  pre-existing demo rows whose `file` field is empty.
- **`AbstractGeometadata.Meta` inheritance.** The concrete
  `ArticleGeometadata` / `PreprintGeometadata` Meta classes did
  not inherit from `AbstractGeometadata.Meta`, so the abstract
  bbox indexes (`%(class)s_bbox_idx`) were silently dropped at
  the model layer. Migration 0002 had added them back
  explicitly under the truncated names `articlegeom_bbox_idx` /
  `preprintgeo_bbox_idx`. Concrete Metas now inherit
  (`class Meta(AbstractGeometadata.Meta): abstract = False`)
  and the rename to the template-resolved names happens in
  migration 0003.
- **OLH theme repository nav** did not fire
  `{% hook 'nav_block' %}` (the Material theme already does).
  The Map link therefore did not appear in the repository main
  menu under OLH or its subthemes (e.g. `clean`). The OLH
  repository nav is updated and the README's Non-Standard Hooks
  section documents the required one-line modification so
  plugin users on the OLH theme can apply the same fix.
- **Multi-line Django template comment** in `meta_tags.html`
  rendered as literal text on preprint pages. `{# ... #}` is
  single-line only in Django; converted to
  `{% comment %}...{% endcomment %}`.
- **Leaflet `t is null` crash on map pages with empty default
  coordinates.** `views.py` now coerces setting values to numbers
  via `_setting_number` before embedding them in JavaScript;
  `map_page.html` adds `|default` filters as a belt-and-suspenders
  fallback.

## [0.1.0] - 2025-05-02

Initial development release.

### Added

- **Spatial metadata**: WKT geometry storage with automatic bounding box calculation
- **Temporal metadata**: Flexible JSON-based time periods supporting multiple date ranges
  and free-text values (e.g., "Holocene", "Summer 2021")
- **Article and Preprint support**: Separate models for journal articles and repository
  preprints with identical field structure
- **Issue-level GeoJSON API endpoint** (`/api/issue/<id>/`) for focused harvesting of
  geometadata per journal issue with rich article properties
- **Basemap provider selection** now uses [leaflet-providers](https://github.com/leaflet-extras/leaflet-providers)
  library with 12 preset providers (various OpenStreetMap styles, OpenTopoMap, CyclOSM,
  Geoportail France, TopPlusOpen) instead of manual tile URL configuration
- **Article/preprint landing pages**: Interactive Leaflet map in footer via
  `article_footer_block` hook
- **Issue pages**: Aggregated map showing all articles in an issue via
  `issue_footer_block` hook
- **Journal/repository map page**: Full-page map at `/plugins/geometadata/map/`
- **Press-wide map page**: Cross-journal map at `/plugins/geometadata/press-map/`
- **Fullscreen control**: Maps support fullscreen mode via leaflet.fullscreen
- **Colour-coded markers**: Deterministic colour assignment by issue (journal maps)
  or journal (press maps) using ColorBrewer palettes
- **Geometadata edit forms**: Dedicated pages for editing article/preprint geometadata
  with interactive Leaflet.draw tools (polygon, rectangle, polyline, marker)
- **WKT input**: Direct WKT geometry entry with format validation
- **Temporal periods UI**: JavaScript-powered add/remove rows for multiple time periods
- **Reverse geocoding**: "Lookup Location Names" button to auto-populate place name
  and administrative units from drawn geometry (Nominatim, Photon, or GeoNames)
- **Curation queue**: Paginated list view for back-catalogue work with progress tracking
  and hide-completed toggle
- **Django admin**: Full admin interface for both ArticleGeometadata and
  PreprintGeometadata models

- **Metadata Embedding**
  - **Dublin Core**: `DC.SpatialCoverage`, `DC.box`, `DC.temporal`, `DC.PeriodOfTime`
  - **ISO 19139**: `EX_GeographicBoundingBox` meta tag
  - **geo.* meta tags**: `geo.placename`
  - **Schema.org JSON-LD**: `spatialCoverage` (GeoShape), `temporalCoverage`
  - **GeoJSON link element**: Optional `<link rel="alternate" type="application/geo+json">`

- **Settings**: 27 configurable options for display, embedding, basemap, colour coding,
  and reverse geocoding providers
- Full i18n support with Django translation system for **English** and **German**, including translations for map UI elements

[0.1.0]: https://github.com/GeoinformationSystems/janeway_geometadata/releases/tag/v0.1.0
