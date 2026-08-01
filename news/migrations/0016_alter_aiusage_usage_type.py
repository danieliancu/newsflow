from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("news", "0015_automatic_schedule_and_budget_limits")]

    operations = [
        migrations.AlterField(
            model_name="aiusage",
            name="usage_type",
            field=models.CharField(
                choices=[
                    ("article_classification", "Clasificare articol"),
                    ("event_claim_extraction", "Extragere afirmații"),
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
