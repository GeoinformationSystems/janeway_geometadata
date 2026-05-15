/**
 * geometadata-overlap.js
 *
 * Multi-article overlap picker for the journal-, press- and issue-wide
 * Leaflet maps. On a map click, finds every article whose geometry contains
 * the click and either opens that article's popup directly (1 hit) or a
 * paginated popup with wrap-around prev/next controls (2+ hits).
 *
 * Adapted from the OJS geoMetadata plugin's js/lib/map_overlap.js (GPL-3.0,
 * KOMET / OPTIMETA / Daniel Nüst, Tom Niers), itself inspired by OPTIMAP's
 * MapInteractionManager. Marker hit-testing uses the icon's visible
 * footprint (iconSize / iconAnchor) and LineString hit-testing uses pixel
 * tolerance, both per the bug-fix commit
 * https://github.com/TIBHannover/geoMetadata/commit/d486562 — fixing the
 * original implementation where small markers and very short / very long
 * lines routinely missed clicks the cursor had clearly landed on.
 *
 * Pure helpers and the manager factory are exposed on `window.*` for
 * unit-style testing from the E2E suite (see tests/e2e/test_maps.py).
 */

(function (global) {
    'use strict';

    // Tolerances are in CSS pixels so the click target matches the visible
    // stroke width / icon footprint at every zoom level.
    var POINT_TOLERANCE_PX = 10;
    var LINE_TOLERANCE_PX  = 10;

    // -----------------------------------------------------------------
    // Pure geometry helpers (no DOM, no map state mutation)
    // -----------------------------------------------------------------

    function pointInRing(latlng, ring) {
        var x = latlng.lng, y = latlng.lat, inside = false;
        for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
            var xi = ring[i][0], yi = ring[i][1];
            var xj = ring[j][0], yj = ring[j][1];
            var intersect = ((yi > y) !== (yj > y)) &&
                            (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
            if (intersect) inside = !inside;
        }
        return inside;
    }

    function pointInPolygon(latlng, polygonCoords) {
        if (!polygonCoords || polygonCoords.length === 0) return false;
        if (!pointInRing(latlng, polygonCoords[0])) return false;
        // Holes
        for (var i = 1; i < polygonCoords.length; i++) {
            if (pointInRing(latlng, polygonCoords[i])) return false;
        }
        return true;
    }

    function distanceToSegmentPx(map, latlng, a, b) {
        // Parametrise the segment in lat/lng space (round-tripping through
        // pixel space loses precision at low zoom), then measure the cursor's
        // distance in pixels — that matches the visible stroke width, so the
        // click target lines up with where Leaflet shows the pointer cursor.
        var dlat = b.lat - a.lat, dlng = b.lng - a.lng;
        var lenSq = dlat * dlat + dlng * dlng;
        var t = lenSq === 0 ? 0
            : ((latlng.lat - a.lat) * dlat + (latlng.lng - a.lng) * dlng) / lenSq;
        if (t < 0) t = 0; else if (t > 1) t = 1;
        var nearestLatLng = L.latLng(a.lat + t * dlat, a.lng + t * dlng);
        var p  = map.latLngToLayerPoint(latlng);
        var pn = map.latLngToLayerPoint(nearestLatLng);
        var dx = p.x - pn.x, dy = p.y - pn.y;
        return Math.sqrt(dx * dx + dy * dy);
    }

    function pointOnLineString(map, latlng, coords) {
        for (var i = 0; i < coords.length - 1; i++) {
            var a = L.latLng(coords[i][1],     coords[i][0]);
            var b = L.latLng(coords[i + 1][1], coords[i + 1][0]);
            if (distanceToSegmentPx(map, latlng, a, b) <= LINE_TOLERANCE_PX) return true;
        }
        return false;
    }

    function pointOnMarker(map, latlng, pointCoords, iconSize, iconAnchor) {
        var p   = map.latLngToLayerPoint(latlng);
        var mp  = map.latLngToLayerPoint(L.latLng(pointCoords[1], pointCoords[0]));
        // Treat the icon's visible footprint as the hit zone:
        //   [mp.x - anchorX, mp.x + (iconW - anchorX)] ×
        //   [mp.y - anchorY, mp.y + (iconH - anchorY)]
        // Without icon dimensions (e.g. circleMarker), fall back to a small
        // circular tolerance.
        if (iconSize && iconAnchor) {
            var dx = p.x - mp.x, dy = p.y - mp.y;
            return dx >= -iconAnchor[0] && dx <= (iconSize[0] - iconAnchor[0])
                && dy >= -iconAnchor[1] && dy <= (iconSize[1] - iconAnchor[1]);
        }
        var ddx = p.x - mp.x, ddy = p.y - mp.y;
        return Math.sqrt(ddx * ddx + ddy * ddy) <= POINT_TOLERANCE_PX;
    }

    function geometryContainsPoint(map, geometry, latlng, iconSize, iconAnchor) {
        if (!geometry) return false;
        var t = geometry.type, c = geometry.coordinates;
        if (t === 'Point')           return pointOnMarker(map, latlng, c, iconSize, iconAnchor);
        if (t === 'LineString')      return pointOnLineString(map, latlng, c);
        if (t === 'Polygon')         return pointInPolygon(latlng, c);
        if (t === 'MultiPoint') {
            for (var i = 0; i < c.length; i++) {
                if (pointOnMarker(map, latlng, c[i], iconSize, iconAnchor)) return true;
            }
            return false;
        }
        if (t === 'MultiLineString') {
            for (var j = 0; j < c.length; j++) {
                if (pointOnLineString(map, latlng, c[j])) return true;
            }
            return false;
        }
        if (t === 'MultiPolygon') {
            for (var k = 0; k < c.length; k++) {
                if (pointInPolygon(latlng, c[k])) return true;
            }
            return false;
        }
        if (t === 'GeometryCollection') {
            for (var l = 0; l < geometry.geometries.length; l++) {
                if (geometryContainsPoint(map, geometry.geometries[l], latlng, iconSize, iconAnchor)) return true;
            }
            return false;
        }
        return false;
    }

    function layerContainsPoint(map, layer, latlng) {
        if (!layer || !layer.feature || !layer.feature.geometry) return false;
        var iconOpts = layer.options && layer.options.icon && layer.options.icon.options;
        var iconSize   = iconOpts ? iconOpts.iconSize   : null;
        var iconAnchor = iconOpts ? iconOpts.iconAnchor : null;
        return geometryContainsPoint(
            map, layer.feature.geometry, latlng, iconSize, iconAnchor
        );
    }

    function findOverlappingArticles(map, articleLayersMap, latlng) {
        var hits = [];
        articleLayersMap.forEach(function (layers, articleId) {
            // First containing layer wins — don't add an article twice when
            // it's split across multiple Leaflet layers (e.g. antimeridian-
            // split MultiPolygons).
            for (var i = 0; i < layers.length; i++) {
                if (layerContainsPoint(map, layers[i], latlng)) {
                    hits.push({ articleId: articleId, layers: layers });
                    return;
                }
            }
        });
        return hits;
    }

    function escapeHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    // -----------------------------------------------------------------
    // Manager factory
    // -----------------------------------------------------------------

    function createOverlapManager(map, options) {
        var articleLayersMap = options.articleLayersMap;
        var getArticleMeta   = options.getArticleMeta;
        var highlight        = options.highlight        || function () {};
        var resetHighlight   = options.resetHighlight   || function () {};
        var i18n             = options.i18n             || {};

        var paginatedPopup = null;
        var singlePopup    = null;
        var overlap        = [];
        var pageIndex      = 0;
        var activeHighlight = null;

        function closeAnyManagerPopup() {
            if (paginatedPopup) { map.closePopup(paginatedPopup); paginatedPopup = null; }
            if (singlePopup)    { map.closePopup(singlePopup);    singlePopup    = null; }
        }

        function clearActiveHighlight() {
            if (activeHighlight !== null) {
                resetHighlight(activeHighlight);
                activeHighlight = null;
            }
        }

        function setActiveHighlight(articleId) {
            if (activeHighlight === articleId) return;
            clearActiveHighlight();
            highlight(articleId);
            activeHighlight = articleId;
        }

        function counterText(i, n) {
            // Default uses {i}/{n} placeholders; templates can override via
            // data-i18n-overlap-counter='{i} von {n} Artikeln' etc.
            var tpl = i18n.counter || '{i} of {n} articles';
            return tpl.replace('{i}', i).replace('{n}', n);
        }

        function renderHeader() {
            var n = overlap.length;
            var counter = escapeHtml(counterText(pageIndex + 1, n));
            var prevTitle = escapeHtml(i18n.prev || 'Previous article');
            var nextTitle = escapeHtml(i18n.next || 'Next article');
            return '<div class="geometadata-overlap-header">' +
                     '<button type="button" class="geometadata-overlap-prev" ' +
                     'title="' + prevTitle + '" aria-label="' + prevTitle + '">&#8249;</button>' +
                     '<span class="geometadata-overlap-counter">' + counter + '</span>' +
                     '<button type="button" class="geometadata-overlap-next" ' +
                     'title="' + nextTitle + '" aria-label="' + nextTitle + '">&#8250;</button>' +
                   '</div>';
        }

        function renderBody(articleId) {
            var meta = getArticleMeta(articleId) || {};
            return '<div class="geometadata-overlap-body">' + (meta.popupHtml || '') + '</div>';
        }

        function renderContent() {
            var current = overlap[pageIndex];
            return '<div class="geometadata-overlap-popup">' + renderHeader() +
                   renderBody(current.articleId) + '</div>';
        }

        function bindControls() {
            var el = paginatedPopup && paginatedPopup.getElement();
            if (!el) return;
            var prev = el.querySelector('.geometadata-overlap-prev');
            var next = el.querySelector('.geometadata-overlap-next');
            // Stop propagation so the click isn't picked up by the map's
            // own click handler (which would re-trigger overlap detection).
            if (prev) {
                L.DomEvent.on(prev, 'click', function (e) {
                    L.DomEvent.stopPropagation(e);
                    L.DomEvent.preventDefault(e);
                    goPrev();
                });
            }
            if (next) {
                L.DomEvent.on(next, 'click', function (e) {
                    L.DomEvent.stopPropagation(e);
                    L.DomEvent.preventDefault(e);
                    goNext();
                });
            }
        }

        function refresh() {
            if (!paginatedPopup) return;
            paginatedPopup.setContent(renderContent());
            setActiveHighlight(overlap[pageIndex].articleId);
            bindControls();
        }

        function goPrev() {
            if (overlap.length === 0) return;
            pageIndex = (pageIndex - 1 + overlap.length) % overlap.length;
            refresh();
        }

        function goNext() {
            if (overlap.length === 0) return;
            pageIndex = (pageIndex + 1) % overlap.length;
            refresh();
        }

        function openPaginated(hits, latlng) {
            closeAnyManagerPopup();
            overlap   = hits;
            pageIndex = 0;
            paginatedPopup = L.popup({
                maxWidth: 360,
                minWidth: 240,
                closeButton: true,
                autoClose: false,
                closeOnClick: false,
                className: 'geometadata-overlap-leaflet-popup'
            }).setLatLng(latlng).setContent(renderContent()).openOn(map);
            setActiveHighlight(overlap[pageIndex].articleId);
            bindControls();
        }

        function openSingle(articleId, latlng) {
            var meta = getArticleMeta(articleId) || {};
            var layers = meta.layers || [];
            if (!layers.length) return;
            singlePopup = L.popup({
                maxWidth: 360,
                minWidth: 240,
                closeButton: true
            }).setLatLng(latlng).setContent(meta.popupHtml || '').openOn(map);
            setActiveHighlight(articleId);
        }

        function onMapClick(e) {
            if (e.originalEvent && e.originalEvent.defaultPrevented) return;
            var hits = findOverlappingArticles(map, articleLayersMap, e.latlng);
            closeAnyManagerPopup();
            if (hits.length === 0) {
                clearActiveHighlight();
                return;
            }
            if (hits.length === 1) {
                openSingle(hits[0].articleId, e.latlng);
                return;
            }
            openPaginated(hits, e.latlng);
        }

        function onPopupClose(e) {
            if (paginatedPopup && e.popup === paginatedPopup) {
                paginatedPopup = null;
                overlap = [];
                pageIndex = 0;
            }
            if (singlePopup && e.popup === singlePopup) {
                singlePopup = null;
            }
            clearActiveHighlight();
        }

        function onKeyDown(e) {
            if (e.key === 'Escape' && (paginatedPopup || singlePopup)) {
                closeAnyManagerPopup();
                return;
            }
            if (!paginatedPopup) return;
            if (e.key === 'ArrowLeft')  { goPrev(); }
            else if (e.key === 'ArrowRight') { goNext(); }
        }

        map.on('click', onMapClick);
        map.on('popupclose', onPopupClose);
        document.addEventListener('keydown', onKeyDown);

        return {
            destroy: function () {
                map.off('click', onMapClick);
                map.off('popupclose', onPopupClose);
                document.removeEventListener('keydown', onKeyDown);
                closeAnyManagerPopup();
                clearActiveHighlight();
            }
        };
    }

    // -----------------------------------------------------------------
    // Exports
    // -----------------------------------------------------------------
    global.geometadata_pointInRing            = pointInRing;
    global.geometadata_pointInPolygon         = pointInPolygon;
    global.geometadata_pointOnLineString      = pointOnLineString;
    global.geometadata_pointOnMarker          = pointOnMarker;
    global.geometadata_geometryContainsPoint  = geometryContainsPoint;
    global.geometadata_layerContainsPoint     = layerContainsPoint;
    global.geometadata_findOverlappingArticles = findOverlappingArticles;
    global.geometadata_createOverlapManager   = createOverlapManager;

})(window);
