import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0004_article_source_sections"),
        ("taxonomy", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="ai_classified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="article",
            name="ai_confidence",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="article",
            name="ai_model",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="article",
            name="ai_reason",
            field=models.CharField(blank=True, max_length=300),
        ),
        migrations.AddField(
            model_name="article",
            name="ai_suggested_category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ai_suggested_articles",
                to="taxonomy.category",
            ),
        ),
    ]
