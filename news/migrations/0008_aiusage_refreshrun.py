from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0007_source_seo_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RefreshRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("status", models.CharField(choices=[("running", "În desfășurare"), ("completed", "Finalizat"), ("partial", "Finalizat parțial"), ("skipped", "Omis"), ("failed", "Eșuat")], default="running", max_length=20)),
                ("started_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("sources_attempted", models.PositiveIntegerField(default=0)),
                ("sources_succeeded", models.PositiveIntegerField(default=0)),
                ("sources_failed", models.PositiveIntegerField(default=0)),
                ("articles_collected", models.PositiveIntegerField(default=0)),
                ("ai_calls", models.PositiveIntegerField(default=0)),
                ("input_tokens", models.PositiveBigIntegerField(default=0)),
                ("output_tokens", models.PositiveBigIntegerField(default=0)),
                ("cost_usd", models.DecimalField(decimal_places=6, default=0, max_digits=12)),
                ("cost_gbp", models.DecimalField(decimal_places=6, default=0, max_digits=12)),
                ("note", models.CharField(blank=True, max_length=300)),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="refresh_runs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-started_at",)},
        ),
        migrations.CreateModel(
            name="AIUsage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("model", models.CharField(db_index=True, max_length=100)),
                ("input_tokens", models.PositiveIntegerField(default=0)),
                ("cached_input_tokens", models.PositiveIntegerField(default=0)),
                ("output_tokens", models.PositiveIntegerField(default=0)),
                ("total_tokens", models.PositiveIntegerField(default=0)),
                ("input_cost_usd", models.DecimalField(decimal_places=8, default=0, max_digits=12)),
                ("output_cost_usd", models.DecimalField(decimal_places=8, default=0, max_digits=12)),
                ("total_cost_usd", models.DecimalField(decimal_places=8, default=0, max_digits=12)),
                ("usd_to_gbp_rate", models.DecimalField(decimal_places=6, default=0, max_digits=10)),
                ("total_cost_gbp", models.DecimalField(decimal_places=8, default=0, max_digits=12)),
                ("is_estimated", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("article", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_usage", to="news.article")),
                ("refresh_run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_usage", to="news.refreshrun")),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
