from django.db import migrations


def remove_already_detached_gandul_events(apps, schema_editor):
    Event = apps.get_model("news", "Event")
    for event in Event.objects.filter(generated_source_count__gt=0).iterator():
        eligible_count = event.articles.values("source_id").distinct().count()
        if event.generated_source_count > eligible_count:
            event.delete()


class Migration(migrations.Migration):
    dependencies = [("news", "0020_remove_excluded_event_articles")]
    operations = [
        migrations.RunPython(
            remove_already_detached_gandul_events,
            migrations.RunPython.noop,
        )
    ]
