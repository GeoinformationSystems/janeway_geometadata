__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__author__ = "Daniel Nüst & KOMET Team"
__license__ = "AGPL v3"

import json
import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from plugins.geometadata.models import ArticleGeometadata, PreprintGeometadata


DATE_PATTERNS = [
    (re.compile(r"^\d{4}$"), "%Y"),
    (re.compile(r"^\d{4}-\d{2}$"), "%Y-%m"),
    (re.compile(r"^\d{4}-\d{2}-\d{2}$"), "%Y-%m-%d"),
]


def parse_date_text(text):
    """Try to parse text as a date. Returns comparable tuple or None."""
    text = text.strip()
    for pattern, fmt in DATE_PATTERNS:
        if pattern.match(text):
            parts = text.split("-")
            return tuple(int(p) for p in parts)
    return None


def validate_temporal_periods(periods):
    """Validate a list of [start, end] text pairs."""
    if not isinstance(periods, list):
        raise ValidationError(_("Temporal periods must be a list."))
    for i, period in enumerate(periods):
        if not isinstance(period, list) or len(period) != 2:
            raise ValidationError(
                _("Period %(num)s must be a [start, end] pair.") % {"num": i + 1}
            )
        start_text = period[0].strip() if isinstance(period[0], str) else ""
        end_text = period[1].strip() if isinstance(period[1], str) else ""
        if not start_text and not end_text:
            raise ValidationError(
                _("Period %(num)s must have at least a start or end value.")
                % {"num": i + 1}
            )
        start_date = parse_date_text(start_text) if start_text else None
        end_date = parse_date_text(end_text) if end_text else None
        if start_date and end_date and start_date > end_date:
            raise ValidationError(
                _("Period %(num)s: start must be before or equal to end.")
                % {"num": i + 1}
            )


class GeometadataForm(forms.ModelForm):
    """
    Form for editing geospatial and temporal metadata.

    The geometry field uses a textarea that will be enhanced with a
    Leaflet map widget via JavaScript.
    """

    temporal_periods_json = forms.CharField(
        required=False,
        widget=forms.HiddenInput(
            attrs={"id": "id_temporal_periods_json"},
        ),
        help_text=_(
            "Enter time periods as text. Recognised date formats: "
            "YYYY, YYYY-MM, YYYY-MM-DD (validated for ordering)."
        ),
    )

    class Meta:
        fields = [
            "geometry_wkt",
            "place_name",
            "admin_units",
        ]
        widgets = {
            "geometry_wkt": forms.Textarea(
                attrs={
                    "class": "geometadata-wkt-input",
                    "rows": 4,
                    "placeholder": _(
                        "Enter WKT geometry or use the map to draw. "
                        "Example: POLYGON((-10 35, 40 35, 40 70, -10 70, -10 35))"
                    ),
                }
            ),
            "place_name": forms.TextInput(
                attrs={
                    "class": "geometadata-place-input",
                    "placeholder": _("e.g., Vienna, Austria"),
                }
            ),
            "admin_units": forms.Textarea(
                attrs={
                    "class": "geometadata-admin-units",
                    "rows": 2,
                    "placeholder": _("Comma-separated administrative units"),
                }
            ),
        }
        help_texts = {
            "geometry_wkt": _(
                "Geographic coverage in Well-Known Text (WKT) format. "
                "You can draw on the map or enter WKT directly."
            ),
            "place_name": _(
                "Human-readable name(s) of the location(s) covered by this work."
            ),
            "admin_units": _(
                "Administrative units for machine-readable coverage "
                "(auto-populated when available)."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["temporal_periods_json"].initial = json.dumps(
                self.instance.temporal_periods or []
            )
        else:
            self.fields["temporal_periods_json"].initial = "[]"

    def clean_geometry_wkt(self):
        """Validate WKT geometry format."""
        wkt = self.cleaned_data.get("geometry_wkt")
        if not wkt:
            return wkt

        wkt = wkt.strip()

        valid_types = [
            "POINT",
            "LINESTRING",
            "POLYGON",
            "MULTIPOINT",
            "MULTILINESTRING",
            "MULTIPOLYGON",
            "GEOMETRYCOLLECTION",
        ]

        wkt_upper = wkt.upper()
        is_valid_type = any(wkt_upper.startswith(t) for t in valid_types)

        if not is_valid_type:
            raise forms.ValidationError(
                _(
                    "Invalid WKT format. Must start with a valid geometry type: "
                    "POINT, LINESTRING, POLYGON, MULTIPOINT, MULTILINESTRING, "
                    "MULTIPOLYGON, or GEOMETRYCOLLECTION."
                )
            )

        if wkt.count("(") != wkt.count(")"):
            raise forms.ValidationError(
                _("Invalid WKT format: unbalanced parentheses.")
            )

        return wkt

    def clean_temporal_periods_json(self):
        """Parse and validate the temporal periods JSON."""
        raw = self.cleaned_data.get("temporal_periods_json", "").strip()
        if not raw or raw == "[]":
            return []
        try:
            periods = json.loads(raw)
        except json.JSONDecodeError:
            raise forms.ValidationError(_("Invalid JSON for temporal periods."))
        validate_temporal_periods(periods)
        return periods

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.temporal_periods = self.cleaned_data.get("temporal_periods_json", [])
        if commit:
            instance.save()
        return instance


class ArticleGeometadataForm(GeometadataForm):
    """Form for Article geometadata."""

    class Meta(GeometadataForm.Meta):
        model = ArticleGeometadata


class PreprintGeometadataForm(GeometadataForm):
    """Form for Preprint geometadata."""

    class Meta(GeometadataForm.Meta):
        model = PreprintGeometadata
