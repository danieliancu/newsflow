from django.db import migrations


OLD_TEXT = (
    "După accident, Diana Șoșoacă a fost transportată la spital pentru îngrijiri "
    "sau investigații medicale, iar o relatare precizează Spitalul Universitar și răni ușoare."
)
NEW_TEXT = (
    "După accident, Diana Șoșoacă a fost transportată la spital pentru îngrijiri "
    "sau investigații medicale."
)


def clean_reporting_language(apps, schema_editor):
    Event = apps.get_model("news", "Event")
    for event in Event.objects.exclude(confirmed_facts=[]).iterator():
        changed = False
        facts = []
        for fact in event.confirmed_facts:
            updated = dict(fact)
            if updated.get("text") == OLD_TEXT:
                updated["text"] = NEW_TEXT
                changed = True
            facts.append(updated)
        if changed:
            event.confirmed_facts = facts
            event.save(update_fields=["confirmed_facts"])


class Migration(migrations.Migration):
    dependencies = [("news", "0013_subject_focused_confirmed_facts")]

    operations = [
        migrations.RunPython(clean_reporting_language, migrations.RunPython.noop)
    ]
