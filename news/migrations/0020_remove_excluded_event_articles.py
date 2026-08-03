from django.db import migrations


def remove_gandul_from_events(apps, schema_editor):
    Event = apps.get_model("news", "Event")
    Event.objects.filter(event_articles__article__source__slug="gandul").distinct().delete()


class Migration(migrations.Migration):
    dependencies = [("news", "0019_remove_event_confirmed_facts")]
    operations = [migrations.RunPython(remove_gandul_from_events, migrations.RunPython.noop)]
