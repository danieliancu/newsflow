from django.db import migrations, models
from django.utils.text import slugify


def populate_source_slugs(apps, schema_editor):
    Source = apps.get_model("news", "Source")
    used = set()
    for source in Source.objects.order_by("pk"):
        base = slugify(source.name) or "sursa"
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}-{suffix}"
            suffix += 1
        source.slug = candidate
        source.save(update_fields=["slug"])
        used.add(candidate)


class Migration(migrations.Migration):
    dependencies = [("news", "0006_article_image_url")]

    operations = [
        migrations.AddField(
            model_name="source",
            name="slug",
            field=models.SlugField(blank=True, max_length=170, null=True),
        ),
        migrations.AddField(
            model_name="source",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="source",
            name="seo_title",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="source",
            name="seo_description",
            field=models.CharField(blank=True, max_length=320),
        ),
        migrations.RunPython(populate_source_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="source",
            name="slug",
            field=models.SlugField(blank=True, max_length=170, unique=True),
        ),
    ]
