from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_emailchallenge"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="feed_display_mode",
            field=models.CharField(
                choices=[("cards", "Carduri"), ("compact", "Compact")],
                default="cards",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="last_feed_seen_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
