from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("news", "0018_alter_aiusage_usage_type"),
        ("recommendations", "0004_savedevent"),
    ]

    operations = [
        migrations.CreateModel(
            name="OpenedEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("event", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="opened_by", to="news.event")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="opened_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ("-updated_at",),
                "constraints": [models.UniqueConstraint(fields=("user", "event"), name="unique_user_opened_event")],
            },
        ),
    ]
