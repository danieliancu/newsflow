from django.db import migrations, models


def lower_legacy_indexing_threshold(apps, schema_editor):
    EventBudget = apps.get_model("news", "EventBudget")
    EventBudget.objects.filter(minimum_sources_for_indexing=3).update(
        minimum_sources_for_indexing=2
    )


class Migration(migrations.Migration):
    dependencies = [("news", "0021_remove_legacy_gandul_events")]

    operations = [
        migrations.AlterField(
            model_name="eventbudget",
            name="minimum_sources_for_indexing",
            field=models.PositiveSmallIntegerField(default=2),
        ),
        migrations.RunPython(
            lower_legacy_indexing_threshold,
            migrations.RunPython.noop,
        ),
    ]
