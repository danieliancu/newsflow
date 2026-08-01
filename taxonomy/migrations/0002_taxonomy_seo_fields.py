from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("taxonomy", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="category",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="category",
            name="seo_title",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="category",
            name="seo_description",
            field=models.CharField(blank=True, max_length=320),
        ),
        migrations.AddField(
            model_name="topic",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="topic",
            name="seo_title",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="topic",
            name="seo_description",
            field=models.CharField(blank=True, max_length=320),
        ),
    ]
