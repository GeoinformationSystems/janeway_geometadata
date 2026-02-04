/**
 * Geometadata Edit Module
 * Handles map editing with drawing tools for articles and preprints
 */

(function(window) {
    'use strict';

    /**
     * Initialize the edit map with drawing controls
     * @param {string} mapElementId - The ID of the map container
     * @param {object} options - Configuration options
     * @param {string} options.wktInputId - ID of the WKT textarea
     * @param {number} options.centerLat - Initial center latitude
     * @param {number} options.centerLng - Initial center longitude
     * @param {number} options.zoom - Initial zoom level
     * @param {string} options.basemapProvider - leaflet-providers key
     */
    function initGeometadataEditMap(mapElementId, options) {
        options = options || {};

        var mapElement = document.getElementById(mapElementId);
        if (!mapElement) {
            console.warn('Map element not found:', mapElementId);
            return null;
        }

        var wktInput = document.getElementById(options.wktInputId);
        var centerLat = options.centerLat || 0;
        var centerLng = options.centerLng || 0;
        var zoom = options.zoom || 2;

        // i18n strings from data attributes
        var i18n = {
            zoomIn: mapElement.getAttribute('data-i18n-zoom-in') || 'Zoom in',
            zoomOut: mapElement.getAttribute('data-i18n-zoom-out') || 'Zoom out',
            fullscreen: mapElement.getAttribute('data-i18n-fullscreen') || 'Full Screen',
            exitFullscreen: mapElement.getAttribute('data-i18n-exit-fullscreen') || 'Exit Full Screen'
        };

        // Initialize map
        var map = L.map(mapElementId, {
            zoomControl: false,
            fullscreenControl: {
                title: i18n.fullscreen,
                titleCancel: i18n.exitFullscreen
            }
        }).setView([centerLat, centerLng], zoom);

        L.control.zoom({
            zoomInTitle: i18n.zoomIn,
            zoomOutTitle: i18n.zoomOut
        }).addTo(map);

        // Add tile layer via leaflet-providers
        var basemapProvider = options.basemapProvider || 'OpenStreetMap.Mapnik';
        L.tileLayer.provider(basemapProvider).addTo(map);

        // Create feature group for drawn items
        var drawnItems = new L.FeatureGroup();
        map.addLayer(drawnItems);

        // Initialize draw control
        var drawControl = new L.Control.Draw({
            position: 'topright',
            draw: {
                polyline: {
                    shapeOptions: {
                        color: '#3388ff',
                        weight: 3
                    }
                },
                polygon: {
                    allowIntersection: false,
                    showArea: true,
                    shapeOptions: {
                        color: '#3388ff',
                        weight: 2
                    }
                },
                rectangle: {
                    shapeOptions: {
                        color: '#3388ff',
                        weight: 2
                    }
                },
                circle: false, // Circles don't convert well to WKT
                circlemarker: false,
                marker: true  // Use default Leaflet markers
            },
            edit: {
                featureGroup: drawnItems,
                remove: true
            }
        });
        map.addControl(drawControl);

        // Load existing WKT if present
        if (wktInput && wktInput.value.trim()) {
            loadWktToMap(wktInput.value, drawnItems, map);
        }

        // Handle draw events
        map.on(L.Draw.Event.CREATED, function(e) {
            drawnItems.addLayer(e.layer);
            updateWktFromLayers(drawnItems, wktInput);
        });

        map.on(L.Draw.Event.EDITED, function(e) {
            updateWktFromLayers(drawnItems, wktInput);
        });

        map.on(L.Draw.Event.DELETED, function(e) {
            updateWktFromLayers(drawnItems, wktInput);
        });

        // Update map when WKT input changes manually
        if (wktInput) {
            wktInput.addEventListener('change', function() {
                drawnItems.clearLayers();
                if (wktInput.value.trim()) {
                    loadWktToMap(wktInput.value, drawnItems, map);
                }
            });
        }

        return {
            map: map,
            drawnItems: drawnItems,
            drawControl: drawControl
        };
    }

    /**
     * Parse WKT and add to feature group
     */
    function loadWktToMap(wkt, featureGroup, map) {
        wkt = wkt.trim();
        if (!wkt) return;

        try {
            var geojson = wktToGeoJSON(wkt);
            if (geojson) {
                var layer = L.geoJSON(geojson, {
                    pointToLayer: function(feature, latlng) {
                        return L.marker(latlng);
                    }
                });

                layer.eachLayer(function(l) {
                    featureGroup.addLayer(l);
                });

                // Fit map to bounds
                var bounds = featureGroup.getBounds();
                if (bounds.isValid()) {
                    map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
                }
            }
        } catch (e) {
            console.error('Error parsing WKT:', e);
        }
    }

    /**
     * Convert layers to WKT and update input
     */
    function updateWktFromLayers(featureGroup, wktInput) {
        if (!wktInput) return;

        var layers = featureGroup.getLayers();
        if (layers.length === 0) {
            wktInput.value = '';
            return;
        }

        var wktParts = [];
        layers.forEach(function(layer) {
            var wkt = layerToWkt(layer);
            if (wkt) {
                wktParts.push(wkt);
            }
        });

        if (wktParts.length === 1) {
            wktInput.value = wktParts[0];
        } else if (wktParts.length > 1) {
            // Create a GEOMETRYCOLLECTION
            wktInput.value = 'GEOMETRYCOLLECTION(' + wktParts.join(', ') + ')';
        } else {
            wktInput.value = '';
        }
    }

    /**
     * Convert a Leaflet layer to WKT
     */
    function layerToWkt(layer) {
        if (layer instanceof L.Marker) {
            var latlng = layer.getLatLng();
            return 'POINT(' + latlng.lng + ' ' + latlng.lat + ')';
        } else if (layer instanceof L.Polygon) {
            // Check if it's a rectangle or polygon
            var latlngs = layer.getLatLngs()[0]; // Get outer ring
            var coords = latlngs.map(function(ll) {
                return ll.lng + ' ' + ll.lat;
            });
            // Close the ring
            coords.push(coords[0]);
            return 'POLYGON((' + coords.join(', ') + '))';
        } else if (layer instanceof L.Polyline) {
            var latlngs = layer.getLatLngs();
            var coords = latlngs.map(function(ll) {
                return ll.lng + ' ' + ll.lat;
            });
            return 'LINESTRING(' + coords.join(', ') + ')';
        }
        return null;
    }

    /**
     * Simple WKT to GeoJSON converter
     */
    function wktToGeoJSON(wkt) {
        wkt = wkt.trim().toUpperCase();

        // Handle GEOMETRYCOLLECTION
        if (wkt.startsWith('GEOMETRYCOLLECTION')) {
            return parseGeometryCollection(wkt);
        }

        // Handle POINT
        if (wkt.startsWith('POINT')) {
            return parsePoint(wkt);
        }

        // Handle MULTIPOINT
        if (wkt.startsWith('MULTIPOINT')) {
            return parseMultiPoint(wkt);
        }

        // Handle LINESTRING
        if (wkt.startsWith('LINESTRING')) {
            return parseLineString(wkt);
        }

        // Handle MULTILINESTRING
        if (wkt.startsWith('MULTILINESTRING')) {
            return parseMultiLineString(wkt);
        }

        // Handle POLYGON
        if (wkt.startsWith('POLYGON')) {
            return parsePolygon(wkt);
        }

        // Handle MULTIPOLYGON
        if (wkt.startsWith('MULTIPOLYGON')) {
            return parseMultiPolygon(wkt);
        }

        return null;
    }

    function parsePoint(wkt) {
        var match = wkt.match(/POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)/);
        if (match) {
            return {
                type: 'Point',
                coordinates: [parseFloat(match[1]), parseFloat(match[2])]
            };
        }
        return null;
    }

    function parseMultiPoint(wkt) {
        var content = wkt.replace(/MULTIPOINT\s*\(\s*/, '').replace(/\s*\)$/, '');
        // Handle both (x y, x y) and ((x y), (x y)) formats
        content = content.replace(/\(\s*/g, '').replace(/\s*\)/g, '');
        var points = content.split(',').map(function(coord) {
            var parts = coord.trim().split(/\s+/);
            return [parseFloat(parts[0]), parseFloat(parts[1])];
        });
        return {
            type: 'MultiPoint',
            coordinates: points
        };
    }

    function parseLineString(wkt) {
        var match = wkt.match(/LINESTRING\s*\(\s*(.+)\s*\)/);
        if (match) {
            var coords = parseCoordinateString(match[1]);
            return {
                type: 'LineString',
                coordinates: coords
            };
        }
        return null;
    }

    function parseMultiLineString(wkt) {
        var content = wkt.replace(/MULTILINESTRING\s*\(\s*/, '').replace(/\s*\)$/, '');
        var lines = [];
        var depth = 0;
        var current = '';

        for (var i = 0; i < content.length; i++) {
            var char = content[i];
            if (char === '(') {
                depth++;
                if (depth === 1) continue;
            } else if (char === ')') {
                depth--;
                if (depth === 0) {
                    lines.push(parseCoordinateString(current));
                    current = '';
                    continue;
                }
            }
            if (depth > 0) {
                current += char;
            }
        }

        return {
            type: 'MultiLineString',
            coordinates: lines
        };
    }

    function parsePolygon(wkt) {
        var content = wkt.replace(/POLYGON\s*\(\s*/, '').replace(/\s*\)$/, '');
        var rings = [];
        var depth = 0;
        var current = '';

        for (var i = 0; i < content.length; i++) {
            var char = content[i];
            if (char === '(') {
                depth++;
                continue;
            } else if (char === ')') {
                depth--;
                if (depth === 0) {
                    rings.push(parseCoordinateString(current));
                    current = '';
                    continue;
                }
            }
            if (depth > 0) {
                current += char;
            }
        }

        return {
            type: 'Polygon',
            coordinates: rings
        };
    }

    function parseMultiPolygon(wkt) {
        var content = wkt.replace(/MULTIPOLYGON\s*\(\s*/, '').replace(/\s*\)$/, '');
        var polygons = [];
        var depth = 0;
        var current = '';

        for (var i = 0; i < content.length; i++) {
            var char = content[i];
            if (char === '(') {
                depth++;
                if (depth === 1) continue;
            } else if (char === ')') {
                depth--;
                if (depth === 0) {
                    // Parse as polygon
                    var polygon = parsePolygon('POLYGON(' + current + ')');
                    if (polygon) {
                        polygons.push(polygon.coordinates);
                    }
                    current = '';
                    continue;
                }
            }
            if (depth > 0) {
                current += char;
            }
        }

        return {
            type: 'MultiPolygon',
            coordinates: polygons
        };
    }

    function parseGeometryCollection(wkt) {
        var content = wkt.replace(/GEOMETRYCOLLECTION\s*\(\s*/, '').replace(/\s*\)$/, '');
        var geometries = [];
        var depth = 0;
        var current = '';

        for (var i = 0; i < content.length; i++) {
            var char = content[i];
            if (char === '(') depth++;
            else if (char === ')') depth--;

            if (char === ',' && depth === 0) {
                var geom = wktToGeoJSON(current.trim());
                if (geom) geometries.push(geom);
                current = '';
            } else {
                current += char;
            }
        }

        // Don't forget the last geometry
        if (current.trim()) {
            var geom = wktToGeoJSON(current.trim());
            if (geom) geometries.push(geom);
        }

        return {
            type: 'GeometryCollection',
            geometries: geometries
        };
    }

    function parseCoordinateString(str) {
        return str.split(',').map(function(coord) {
            var parts = coord.trim().split(/\s+/);
            return [parseFloat(parts[0]), parseFloat(parts[1])];
        });
    }

    /**
     * Temporal Periods add/remove UI.
     * Reads/writes a hidden JSON field and renders editable rows.
     */
    function initTemporalPeriodsUI(hiddenFieldId, containerId, addButtonId, i18nOpts) {
        i18nOpts = i18nOpts || {};
        var hiddenField = document.getElementById(hiddenFieldId);
        var container = document.getElementById(containerId);
        var addBtn = document.getElementById(addButtonId);
        if (!hiddenField || !container || !addBtn) return;

        var periods = [];
        try {
            periods = JSON.parse(hiddenField.value || '[]');
        } catch (e) {
            periods = [];
        }

        function sync() {
            hiddenField.value = JSON.stringify(periods);
        }

        function renderAll() {
            container.innerHTML = '';
            periods.forEach(function(period, idx) {
                container.appendChild(buildRow(idx));
            });
        }

        function buildRow(idx) {
            var row = document.createElement('div');
            row.className = 'row temporal-period-row';
            row.style.marginBottom = '0.5rem';

            var col1 = document.createElement('div');
            col1.className = 'large-5 columns';
            var startInput = document.createElement('input');
            startInput.type = 'text';
            startInput.placeholder = i18nOpts.startPlaceholder || 'Start (e.g. 2020-01, Holocene)';
            startInput.value = periods[idx][0] || '';
            startInput.addEventListener('input', function() {
                periods[idx][0] = this.value;
                sync();
            });
            var startLabel = document.createElement('label');
            startLabel.textContent = i18nOpts.startLabel || 'Start';
            startLabel.appendChild(startInput);
            col1.appendChild(startLabel);

            var col2 = document.createElement('div');
            col2.className = 'large-5 columns';
            var endInput = document.createElement('input');
            endInput.type = 'text';
            endInput.placeholder = i18nOpts.endPlaceholder || 'End (e.g. 2021-06)';
            endInput.value = periods[idx][1] || '';
            endInput.addEventListener('input', function() {
                periods[idx][1] = this.value;
                sync();
            });
            var endLabel = document.createElement('label');
            endLabel.textContent = i18nOpts.endLabel || 'End';
            endLabel.appendChild(endInput);
            col2.appendChild(endLabel);

            var col3 = document.createElement('div');
            col3.className = 'large-2 columns';
            col3.style.paddingTop = '1.6rem';
            var removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'button small alert';
            removeBtn.innerHTML = '<i class="fa fa-trash"></i>';
            removeBtn.title = i18nOpts.removeTitle || 'Remove';
            removeBtn.addEventListener('click', function() {
                periods.splice(idx, 1);
                sync();
                renderAll();
            });
            col3.appendChild(removeBtn);

            row.appendChild(col1);
            row.appendChild(col2);
            row.appendChild(col3);
            return row;
        }

        addBtn.addEventListener('click', function() {
            periods.push(['', '']);
            sync();
            container.appendChild(buildRow(periods.length - 1));
        });

        renderAll();
    }

    /**
     * Initialize reverse geocoding button behaviour.
     * @param {string} buttonId - ID of the lookup button
     * @param {string} wktInputId - ID of the WKT textarea
     * @param {string} placeNameInputId - ID of the place_name input
     * @param {string} adminUnitsInputId - ID of the admin_units input
     * @param {string} apiUrl - URL of the reverse-geocode API endpoint
     */
    function initReverseGeocoding(buttonId, wktInputId, placeNameInputId, adminUnitsInputId, apiUrl) {
        var btn = document.getElementById(buttonId);
        if (!btn) return;

        var wktInput = document.getElementById(wktInputId);
        var placeNameInput = document.getElementById(placeNameInputId);
        var adminUnitsInput = document.getElementById(adminUnitsInputId);

        btn.addEventListener('click', function() {
            if (!wktInput || !wktInput.value.trim()) {
                showMessage(btn.getAttribute('data-i18n-no-geometry') || 'Please draw a geometry on the map first.', 'warning');
                return;
            }

            // Confirm if fields already have values
            if ((placeNameInput && placeNameInput.value.trim()) || (adminUnitsInput && adminUnitsInput.value.trim())) {
                var confirmMsg = btn.getAttribute('data-i18n-confirm') || 'Place name or administrative units already have values. Overwrite?';
                if (!window.confirm(confirmMsg)) {
                    return;
                }
            }

            // Loading state
            var originalHtml = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> ' + (btn.getAttribute('data-i18n-loading') || 'Looking up...');

            var csrfToken = getCsrfToken();

            fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ wkt: wktInput.value })
            })
            .then(function(response) {
                return response.json().then(function(data) {
                    return { ok: response.ok, data: data };
                });
            })
            .then(function(result) {
                btn.disabled = false;
                btn.innerHTML = originalHtml;

                if (result.ok && result.data.success) {
                    if (placeNameInput) placeNameInput.value = result.data.place_name || '';
                    if (adminUnitsInput) adminUnitsInput.value = result.data.admin_units || '';
                    showMessage(btn.getAttribute('data-i18n-success') || 'Location names updated.', 'success');
                } else {
                    showMessage(result.data.error || (btn.getAttribute('data-i18n-error') || 'Geocoding failed.'), 'alert');
                }
            })
            .catch(function() {
                btn.disabled = false;
                btn.innerHTML = originalHtml;
                showMessage(btn.getAttribute('data-i18n-error') || 'Geocoding failed.', 'alert');
            });
        });
    }

    function getCsrfToken() {
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }

    function showMessage(msg, type) {
        var callout = document.createElement('div');
        callout.className = 'callout ' + (type || 'info');
        callout.textContent = msg;
        callout.style.marginTop = '0.5rem';

        var form = document.getElementById('geometadata-form');
        if (form) {
            form.parentNode.insertBefore(callout, form);
        } else {
            document.body.appendChild(callout);
        }

        setTimeout(function() {
            if (callout.parentNode) {
                callout.parentNode.removeChild(callout);
            }
        }, 5000);
    }

    // Export
    window.initGeometadataEditMap = initGeometadataEditMap;
    window.wktToGeoJSON = wktToGeoJSON;
    window.initTemporalPeriodsUI = initTemporalPeriodsUI;
    window.initReverseGeocoding = initReverseGeocoding;

})(window);
