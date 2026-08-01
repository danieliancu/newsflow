from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_user_feed_experience"),
    ]

    operations = [
        migrations.CreateModel(
            name="FollowedTerm",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("term", models.CharField(max_length=80)),
                ("normalized_term", models.CharField(max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="followed_terms",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("term",),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "normalized_term"),
                        name="unique_user_followed_term",
                    )
                ],
            },
        ),
    ]
