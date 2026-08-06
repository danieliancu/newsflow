from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_user_feed_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="events_display_mode",
            field=models.CharField(
                choices=[
                    ("auto", "Automat"),
                    ("cards", "Carduri"),
                    ("compact", "Compact"),
                ],
                default="auto",
                max_length=10,
            ),
        ),
    ]
