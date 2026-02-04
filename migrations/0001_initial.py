from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("submission", "0001_initial"),
        ("repository", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArticleGeometadata",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "geometry_wkt",
                    models.TextField(
                        blank=True,
                        help_text="Geographic coverage in Well-Known Text (WKT) format. Example: POLYGON((-10 35, 40 35, 40 70, -10 70, -10 35))",
                        null=True,
                        verbose_name="Geometry (WKT)",
                    ),
                ),
                (
                    "bbox_north",
                    models.FloatField(
                        blank=True,
                        help_text="Northern latitude boundary (-90 to 90)",
                        null=True,
                        verbose_name="Bounding Box North",
                    ),
                ),
                (
                    "bbox_south",
                    models.FloatField(
                        blank=True,
                        help_text="Southern latitude boundary (-90 to 90)",
                        null=True,
                        verbose_name="Bounding Box South",
                    ),
                ),
                (
                    "bbox_east",
                    models.FloatField(
                        blank=True,
                        help_text="Eastern longitude boundary (-180 to 180)",
                        null=True,
                        verbose_name="Bounding Box East",
                    ),
                ),
                (
                    "bbox_west",
                    models.FloatField(
                        blank=True,
                        help_text="Western longitude boundary (-180 to 180)",
                        null=True,
                        verbose_name="Bounding Box West",
                    ),
                ),
                (
                    "place_name",
                    models.CharField(
                        blank=True,
                        help_text="Human-readable name(s) of the location(s), e.g., 'Vienna, Austria' or 'North Atlantic Ocean'",
                        max_length=500,
                        null=True,
                        verbose_name="Place Name",
                    ),
                ),
                (
                    "admin_units",
                    models.TextField(
                        blank=True,
                        help_text="Comma-separated list of administrative units covering this geometry, e.g., 'Austria, Vienna, Wien Stadt'",
                        null=True,
                        verbose_name="Administrative Units",
                    ),
                ),
                (
                    "temporal_periods",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text='List of time periods, each as [start, end] text pairs. Example: [["2020-01", "2021-06"], ["Holocene", ""]]',
                        verbose_name="Temporal Periods",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                (
                    "article",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="geometadata",
                        to="submission.article",
                        verbose_name="Article",
                    ),
                ),
            ],
            options={
                "verbose_name": "Article Geometadata",
                "verbose_name_plural": "Article Geometadata",
            },
        ),
        migrations.CreateModel(
            name="PreprintGeometadata",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "geometry_wkt",
                    models.TextField(
                        blank=True,
                        help_text="Geographic coverage in Well-Known Text (WKT) format. Example: POLYGON((-10 35, 40 35, 40 70, -10 70, -10 35))",
                        null=True,
                        verbose_name="Geometry (WKT)",
                    ),
                ),
                (
                    "bbox_north",
                    models.FloatField(
                        blank=True,
                        help_text="Northern latitude boundary (-90 to 90)",
                        null=True,
                        verbose_name="Bounding Box North",
                    ),
                ),
                (
                    "bbox_south",
                    models.FloatField(
                        blank=True,
                        help_text="Southern latitude boundary (-90 to 90)",
                        null=True,
                        verbose_name="Bounding Box South",
                    ),
                ),
                (
                    "bbox_east",
                    models.FloatField(
                        blank=True,
                        help_text="Eastern longitude boundary (-180 to 180)",
                        null=True,
                        verbose_name="Bounding Box East",
                    ),
                ),
                (
                    "bbox_west",
                    models.FloatField(
                        blank=True,
                        help_text="Western longitude boundary (-180 to 180)",
                        null=True,
                        verbose_name="Bounding Box West",
                    ),
                ),
                (
                    "place_name",
                    models.CharField(
                        blank=True,
                        help_text="Human-readable name(s) of the location(s), e.g., 'Vienna, Austria' or 'North Atlantic Ocean'",
                        max_length=500,
                        null=True,
                        verbose_name="Place Name",
                    ),
                ),
                (
                    "admin_units",
                    models.TextField(
                        blank=True,
                        help_text="Comma-separated list of administrative units covering this geometry, e.g., 'Austria, Vienna, Wien Stadt'",
                        null=True,
                        verbose_name="Administrative Units",
                    ),
                ),
                (
                    "temporal_periods",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text='List of time periods, each as [start, end] text pairs. Example: [["2020-01", "2021-06"], ["Holocene", ""]]',
                        verbose_name="Temporal Periods",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                (
                    "preprint",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="geometadata",
                        to="repository.preprint",
                        verbose_name="Preprint",
                    ),
                ),
            ],
            options={
                "verbose_name": "Preprint Geometadata",
                "verbose_name_plural": "Preprint Geometadata",
            },
        ),
    ]
