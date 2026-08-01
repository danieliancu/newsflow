from django.db import migrations, models


def remove_duplicate_interactions(apps, schema_editor):
    Interaction = apps.get_model("recommendations", "Interaction")
    duplicates = (
        Interaction.objects.values("user_id", "article_id", "kind")
        .annotate(total=models.Count("id"), keep_id=models.Min("id"))
        .filter(total__gt=1)
    )
    for duplicate in duplicates.iterator():
        Interaction.objects.filter(
            user_id=duplicate["user_id"],
            article_id=duplicate["article_id"],
            kind=duplicate["kind"],
        ).exclude(pk=duplicate["keep_id"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("recommendations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            remove_duplicate_interactions,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="interaction",
            constraint=models.UniqueConstraint(
                fields=("user", "article", "kind"),
                name="unique_user_article_interaction_kind",
            ),
        ),
    ]
