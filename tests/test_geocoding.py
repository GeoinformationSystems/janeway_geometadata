"""
Tests for geocoding functionality.

Tests reverse geocoding API with mocked external services.
"""

import json
from unittest.mock import patch, MagicMock

from django.test import override_settings

from plugins.geometadata.tests.base import GeometadataTestCase


@override_settings(
    URL_CONFIG="domain",
    ROOT_URLCONF="plugins.geometadata.tests.urls",
)
class ReverseGeocodeAPITests(GeometadataTestCase):
    """Tests for reverse geocode API endpoint."""

    def setUp(self):
        """Log in as editor for all tests."""
        self.client.force_login(self.editor)

    def _post_geocode(self, data):
        """Helper to POST to reverse geocode endpoint."""
        return self.client.post(
            "/plugins/geometadata/api/reverse-geocode/",
            data=json.dumps(data),
            content_type="application/json",
            SERVER_NAME=self.journal.domain,
        )

    @patch("plugins.geometadata.geocoding.reverse_geocode_wkt")
    @patch("plugins.geometadata.views._get_plugin_setting")
    def test_reverse_geocode_returns_place_name(self, mock_setting, mock_geocode):
        """Successful geocode returns place_name and admin_units."""
        # Enable geocoding
        setting_mock = MagicMock()
        setting_mock.value = "on"
        mock_setting.return_value = setting_mock
        mock_geocode.return_value = {
            "place_name": "Berlin",
            "admin_units": "Berlin, Germany",
        }

        response = self._post_geocode({"wkt": "POINT(13.4 52.5)"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["place_name"], "Berlin")
        self.assertEqual(data["admin_units"], "Berlin, Germany")

    @patch("plugins.geometadata.geocoding.reverse_geocode_wkt")
    @patch("plugins.geometadata.views._get_plugin_setting")
    def test_reverse_geocode_handles_api_error(self, mock_setting, mock_geocode):
        """API failure returns 500 with error message."""
        setting_mock = MagicMock()
        setting_mock.value = "on"
        mock_setting.return_value = setting_mock
        mock_geocode.side_effect = Exception("Network error")

        response = self._post_geocode({"wkt": "POINT(13.4 52.5)"})

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("error", data)

    @patch("plugins.geometadata.views._get_plugin_setting")
    def test_reverse_geocode_requires_geometry(self, mock_setting):
        """Request without WKT returns 400 error."""
        setting_mock = MagicMock()
        setting_mock.value = "on"
        mock_setting.return_value = setting_mock

        response = self._post_geocode({"wkt": ""})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
