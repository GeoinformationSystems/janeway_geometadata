# Changelog

All notable changes to the Geometadata plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **ISO 19139 XML embedding** in article and preprint HTML head, controlled
  by a new `embed_iso19139` plugin setting (default on). Emits a
  `<script type="application/xml" id="geometadata-iso19139">` block
  containing a `gmd:EX_Extent` fragment with `EX_GeographicDescription`
  (place name), `EX_GeographicBoundingBox`, and one `gml:TimePeriod` per
  stored temporal period. Open-ended periods use
  `gml:indeterminatePosition="unknown"`. Closes #4.
- **WKT meta tag** in article and preprint HTML head, controlled by a new
  `embed_wkt` plugin setting (default on). Emits
  `<meta name="DC.SpatialCoverage" scheme="WKT" content="...">` alongside
  the existing GeoJSON variant. The DC schema link is now emitted whenever
  any DC-style tag (DC or WKT) is enabled. Closes #27.

### Changed

- ...

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
