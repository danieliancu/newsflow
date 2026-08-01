from django.db import migrations, models


def make_slugs_unique(apps, schema_editor):
    Event = apps.get_model("news", "Event")
    used = set()
    for event in Event.objects.order_by("pk"):
        base = (event.slug or "eveniment")[:220]
        candidate = base
        suffix = 2
        while candidate in used:
            suffix_text = f"-{suffix}"
            candidate = f"{base[:220 - len(suffix_text)]}{suffix_text}"
            suffix += 1
        if event.slug != candidate:
            event.slug = candidate
            event.save(update_fields=["slug"])
        used.add(candidate)


class Migration(migrations.Migration):
    dependencies = [("news", "0010_eventaiusage")]

    operations = [
        migrations.RunPython(make_slugs_unique, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="event",
            name="slug",
            field=models.SlugField(blank=True, max_length=220, unique=True),
        ),
    ]
