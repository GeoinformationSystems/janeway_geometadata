/**
 * Geometadata Display Module
 * Handles map display for articles and preprints
 */

(function(window) {
    'use strict';

    var DEFAULT_COLOUR = '#3388ff';

    /**
     * Build a mapping from group key → colour using a palette array.
     * Groups are sorted so that the assignment is deterministic across
     * page loads and API responses.  When more groups than colours
     * exist, colours wrap around.
     *
     * @param {Array} features  GeoJSON features (properties._groupKey set)
     * @param {Array} palette   Array of hex colour strings
     * @returns {Object} groupKey → hex colour
     */
    function buildGroupColourMap(features, palette) {
        if (!palette || palette.length === 0) {
            return {};
        }

        // Collect unique group keys
        var seen = {};
        var keys = [];
        for (var i = 0; i < features.length; i++) {
            var k = features[i].properties && features[i].properties._groupKey;
            if (k != null && !seen[k]) {
                seen[k] = true;
                keys.push(String(k));
            }
        }

        // Sort deterministically so the same data always produces the
        // same colour assignment regardless of API response order.
        keys.sort();

        var map = {};
        for (var j = 0; j < keys.length; j++) {
            map[keys[j]] = palette[j % palette.length];
        }
        return map;
    }

    /**
     * Return the colour for a feature, falling back to the default.
     */
    function featureColour(feature, colourMap) {
        var key = feature.properties && feature.properties._groupKey;
        if (key != null && colourMap[String(key)]) {
            return colourMap[String(key)];
        }
        return DEFAULT_COLOUR;
    }

    /**
     * Initialize a map for displaying geometadata
     * @param {string} mapElementId - The ID of the map container element
     * @returns {Object|null} Object with { map, geoLayer } or null if element not found
     */
    function initGeometadataMap(mapElementId) {
        var mapElement = document.getElementById(mapElementId);
        if (!mapElement) {
            console.warn('Geometadata map element not found:', mapElementId);
            return null;
        }

        // Get data attributes
        var geojsonData = mapElement.getAttribute('data-geojson');
        var centerLat = parseFloat(mapElement.getAttribute('data-center-lat')) || 0;
        var centerLng = parseFloat(mapElement.getAttribute('data-center-lng')) || 0;
        var zoom = parseInt(mapElement.getAttribute('data-zoom'), 10) || 4;

        // Colour and opacity configuration
        var colourPaletteAttr = mapElement.getAttribute('data-colour-palette') || '';
        var colourGroupProp = mapElement.getAttribute('data-colour-group-prop') || '';
        var featureColourAttr = mapElement.getAttribute('data-feature-colour') || DEFAULT_COLOUR;
        var featureOpacity = parseFloat(mapElement.getAttribute('data-feature-opacity')) || 0.7;
        var colourPalette = [];
        if (colourPaletteAttr) {
            try { colourPalette = JSON.parse(colourPaletteAttr); } catch (e) { /* ignore */ }
        }

        // i18n strings from data attributes
        var i18n = {
            zoomIn: mapElement.getAttribute('data-i18n-zoom-in') || 'Zoom in',
            zoomOut: mapElement.getAttribute('data-i18n-zoom-out') || 'Zoom out',
            fullscreen: mapElement.getAttribute('data-i18n-fullscreen') || 'Full Screen',
            exitFullscreen: mapElement.getAttribute('data-i18n-exit-fullscreen') || 'Exit Full Screen',
            viewLink: mapElement.getAttribute('data-i18n-view') || 'View',
            resetView: mapElement.getAttribute('data-i18n-reset-view') || 'Reset map view'
        };

        // Check if popups should be disabled (e.g., for single article maps)
        var disablePopup = mapElement.getAttribute('data-disable-popup') === 'true';

        // Initialize the map
        var map = L.map(mapElementId, {
            zoomControl: false
        }).setView([centerLat, centerLng], zoom);

        // Add zoom control with translated tooltips
        L.control.zoom({
            zoomInTitle: i18n.zoomIn,
            zoomOutTitle: i18n.zoomOut
        }).addTo(map);

        // Add fullscreen control explicitly (more reliable than map option)
        if (L.Control.FullScreen) {
            new L.Control.FullScreen({
                position: 'topleft',
                title: i18n.fullscreen,
                titleCancel: i18n.exitFullscreen
            }).addTo(map);
        }

        // Add tile layer via leaflet-providers
        var basemapProvider = mapElement.getAttribute('data-basemap-provider') || 'OpenStreetMap.Mapnik';
        L.tileLayer.provider(basemapProvider).addTo(map);

        // Parse and add GeoJSON data if available
        var geoLayer = null;
        if (geojsonData) {
            try {
                var geojson = JSON.parse(geojsonData);
                var colourMap = {};

                // Pre-compute group keys and colour map
                if (colourPalette.length > 0 && colourGroupProp && geojson.features) {
                    // Tag each feature with a _groupKey derived from the
                    // requested property for deterministic colouring.
                    for (var i = 0; i < geojson.features.length; i++) {
                        var f = geojson.features[i];
                        if (f.properties) {
                            f.properties._groupKey = f.properties[colourGroupProp] || '';
                        }
                    }
                    colourMap = buildGroupColourMap(geojson.features, colourPalette);
                }

                // Determine which colour to use: palette-based or single feature colour
                var useFeatureColour = featureColourAttr;

                geoLayer = L.geoJSON(geojson, {
                    style: function(feature) {
                        var c = colourPalette.length > 0 ? featureColour(feature, colourMap) : useFeatureColour;
                        return {
                            color: c,
                            weight: 2,
                            opacity: Math.min(featureOpacity + 0.2, 1.0),
                            fillColor: c,
                            fillOpacity: featureOpacity * 0.5
                        };
                    },
                    pointToLayer: function(feature, latlng) {
                        var c = colourPalette.length > 0 ? featureColour(feature, colourMap) : useFeatureColour;
                        return L.circleMarker(latlng, {
                            radius: 8,
                            fillColor: c,
                            color: '#ffffff',
                            weight: 2,
                            opacity: 1,
                            fillOpacity: featureOpacity
                        });
                    },
                    onEachFeature: function(feature, layer) {
                        if (!disablePopup) {
                            bindFeaturePopup(feature, layer, i18n);
                        }
                    }
                }).addTo(map);

                // Fit bounds to the geometry
                var bounds = geoLayer.getBounds();
                if (bounds.isValid()) {
                    map.fitBounds(bounds, { padding: [20, 20], maxZoom: 12 });
                }

                // Build legend if we have group colours
                if (colourPalette.length > 0 && Object.keys(colourMap).length > 0) {
                    addColourLegend(map, colourMap);
                }
            } catch (e) {
                console.error('Error parsing GeoJSON:', e);
            }
        }

        return { map: map, geoLayer: geoLayer };
    }

    /**
     * Add a colour legend to the map.
     */
    function addColourLegend(map, colourMap) {
        var legend = L.control({ position: 'bottomright' });
        legend.onAdd = function() {
            var div = L.DomUtil.create('div', 'geometadata-legend');
            div.style.background = 'white';
            div.style.padding = '8px 12px';
            div.style.borderRadius = '4px';
            div.style.boxShadow = '0 1px 4px rgba(0,0,0,0.3)';
            div.style.maxHeight = '200px';
            div.style.overflowY = 'auto';
            div.style.fontSize = '12px';
            div.style.lineHeight = '1.6';

            var keys = Object.keys(colourMap).sort();
            for (var i = 0; i < keys.length; i++) {
                var swatch = '<span style="display:inline-block;width:12px;height:12px;' +
                    'border-radius:2px;margin-right:6px;vertical-align:middle;' +
                    'background:' + escapeHtml(colourMap[keys[i]]) + '"></span>';
                div.innerHTML += swatch + escapeHtml(keys[i]) + '<br>';
            }
            return div;
        };
        legend.addTo(map);
    }

    /**
     * Bind popup to features
     */
    function bindFeaturePopup(feature, layer, i18n) {
        if (feature.properties) {
            var content = buildPopupContent(feature.properties, i18n);
            if (content) {
                layer.bindPopup(content);
            }
        }
    }

    /**
     * Build popup HTML content from feature properties
     */
    function buildPopupContent(properties, i18n) {
        var parts = [];

        if (properties.title) {
            parts.push('<strong>' + escapeHtml(properties.title) + '</strong>');
        }

        if (properties.place_name) {
            parts.push('<p>' + escapeHtml(properties.place_name) + '</p>');
        }

        if (properties.admin_units) {
            parts.push('<p><em>' + escapeHtml(properties.admin_units) + '</em></p>');
        }

        if (properties.temporal_periods && properties.temporal_periods.length > 0) {
            properties.temporal_periods.forEach(function(period) {
                var start = (period[0] || '').trim();
                var end = (period[1] || '').trim();
                var temporal = '';
                if (start && end) {
                    temporal = start + ' \u2013 ' + end;
                } else if (start) {
                    temporal = start;
                } else if (end) {
                    temporal = end;
                }
                if (temporal) {
                    parts.push('<p class="geometadata-temporal">' + escapeHtml(temporal) + '</p>');
                }
            });
        }

        if (properties.url) {
            var viewText = (i18n && i18n.viewLink) ? i18n.viewLink : 'View';
            parts.push('<a href="' + escapeHtml(properties.url) + '">' + escapeHtml(viewText) + ' &rarr;</a>');
        }

        return parts.length > 0 ? '<div class="geometadata-popup">' + parts.join('') + '</div>' : null;
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        if (typeof text !== 'string') return '';
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Initialize all maps on the page with class 'geometadata-map'
     */
    function initAllMaps() {
        var mapElements = document.querySelectorAll('.geometadata-map');
        mapElements.forEach(function(element) {
            if (element.id) {
                initGeometadataMap(element.id);
            }
        });
    }

    // Export functions
    window.initGeometadataMap = initGeometadataMap;
    window.initAllGeometadataMaps = initAllMaps;

})(window);
