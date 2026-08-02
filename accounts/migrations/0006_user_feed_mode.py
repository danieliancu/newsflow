from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_alter_user_feed_display_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="feed_mode",
            field=models.CharField(
                choices=[("for-you", "Pentru tine"), ("latest", "Cele mai noi")],
                default="for-you",
                max_length=10,
            ),
        ),
    ]
