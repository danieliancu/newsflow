from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0018_alter_aiusage_usage_type"),
        ("recommendations", "0003_interaction_updated_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SavedEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_by", to="news.event")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ("-created_at",),
                "constraints": [models.UniqueConstraint(fields=("user", "event"), name="unique_user_saved_event")],
            },
        ),
    ]
