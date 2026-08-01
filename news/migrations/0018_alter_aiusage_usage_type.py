from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("news", "0017_alter_event_slug")]

    operations = [
        migrations.AlterField(
            model_name="aiusage",
            name="usage_type",
            field=models.CharField(
                choices=[
                    ("article_classification", "Clasificare articol"),
                    ("event_claim_extraction", "Extragere afirmații"),
                    ("event_merge_check", "Verificare unire evenimente"),
                    ("event_update_check", "Verificare noutate eveniment"),
                    ("event_summary", "Sinteză eveniment"),
                    ("event_update", "Actualizare eveniment"),
                ],
                db_index=True,
                default="article_classification",
                max_length=40,
            ),
        )
    ]
