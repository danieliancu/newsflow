from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("news", "0016_alter_aiusage_usage_type")]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="slug",
            field=models.SlugField(
                blank=True,
                editable=False,
                max_length=220,
                unique=True,
            ),
        )
    ]
