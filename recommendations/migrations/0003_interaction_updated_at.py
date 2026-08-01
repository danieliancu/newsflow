import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("recommendations", "0002_unique_interaction_kind"),
    ]

    operations = [
        migrations.AddField(
            model_name="interaction",
            name="updated_at",
            field=models.DateTimeField(
                db_index=True,
                default=django.utils.timezone.now,
            ),
        ),
    ]
