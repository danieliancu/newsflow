from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_followedterm"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="feed_display_mode",
            field=models.CharField(
                choices=[("cards", "Carduri"), ("compact", "Compact")],
                default="compact",
                max_length=10,
            ),
        ),
    ]
