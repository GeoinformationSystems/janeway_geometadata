"""
Test URL configuration for geometadata plugin.

Includes the main Janeway URLs plus plugin URLs explicitly,
since the plugin loader may not find the plugin during test startup.
"""

from django.urls import include, path

from core.include_urls import urlpatterns as core_urlpatterns

# Start with core Janeway URLs
urlpatterns = list(core_urlpatterns)

# Explicitly add geometadata plugin URLs
urlpatterns += [
    path("plugins/geometadata/", include("plugins.geometadata.urls")),
]

# Add debug toolbar URLs to avoid 'djdt' namespace errors in templates
try:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
except ImportError:
    pass
