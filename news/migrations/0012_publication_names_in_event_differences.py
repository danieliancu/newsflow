import re

from django.db import migrations


def replace_internal_references(apps, schema_editor):
    Event = apps.get_model("news", "Event")
    for event in Event.objects.exclude(differences=[]).iterator():
        sources = event.source_snapshot or []
        id_to_name = {
            str(source.get("id")): source.get("source__name", "publicația")
            for source in sources
            if source.get("id") is not None
        }
        cleaned = []
        for difference in event.differences:
            text = str(difference)
            for article_id in sorted(id_to_name, key=len, reverse=True):
                text = re.sub(
                    rf"\b{re.escape(article_id)}\b", id_to_name[article_id], text
                )
            text = re.sub(
                r"\b(?:articolul|articolele|sursa|sursele)\s+(?=[A-ZĂÂÎȘȚ])",
                "",
                text,
                flags=re.IGNORECASE,
            )
            cleaned.append(text)
        if cleaned != event.differences:
            event.differences = cleaned
            event.save(update_fields=["differences"])


class Migration(migrations.Migration):
    dependencies = [("news", "0011_event_unique_slug")]

    operations = [
        migrations.RunPython(replace_internal_references, migrations.RunPython.noop)
    ]
