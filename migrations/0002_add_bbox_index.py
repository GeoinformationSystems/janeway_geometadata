from django.db import migrations, models


class Migration(migrations.Migration):
    """Add composite index for bounding box spatial queries."""

    dependencies = [
        ("geometadata", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="articlegeometadata",
            index=models.Index(
                fields=["bbox_south", "bbox_north", "bbox_west", "bbox_east"],
                name="articlegeom_bbox_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="preprintgeometadata",
            index=models.Index(
                fields=["bbox_south", "bbox_north", "bbox_west", "bbox_east"],
                name="preprintgeo_bbox_idx",
            ),
        ),
    ]
