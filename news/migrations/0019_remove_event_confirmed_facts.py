from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("news", "0018_alter_aiusage_usage_type")]

    operations = [
        migrations.RemoveField(
            model_name="event",
            name="confirmed_facts",
        ),
    ]
