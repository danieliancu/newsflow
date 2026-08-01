import re

from django.db import migrations


REWRITES = {
    "Primăria Sectorului 1 și Primăria Municipiului București apar ca fiind vizate în cauza relatată de publicațiile Adevărul, Europa FM și Libertatea.":
        "Primăria Sectorului 1 și Primăria Municipiului București sunt vizate în cauza privind despăgubirile acordate după incident.",
    "G4Media și Europa FM indică faptul că NATO are în vedere consolidarea sau extinderea descurajării nucleare în Europa.":
        "NATO are în vedere consolidarea sau extinderea descurajării nucleare în Europa.",
    "G4Media și Europa FM leagă această posibilă evoluție de amenințările atribuite președintelui rus Vladimir Putin.":
        "Posibila consolidare a descurajării nucleare este legată de amenințările atribuite președintelui rus Vladimir Putin.",
    "G4Media și Europa FM atribuie informațiile agenției dpa.":
        "Informațiile despre această posibilă evoluție sunt atribuite agenției dpa.",
}

GENERIC_SOURCE_WORDS = re.compile(
    r"\b(?:sursă|surse|sursa|sursele|articol|articolul|articole|articolele|publicația|publicațiile)\b",
    re.IGNORECASE,
)


def clean_confirmed_facts(apps, schema_editor):
    Event = apps.get_model("news", "Event")
    for event in Event.objects.exclude(confirmed_facts=[]).iterator():
        publication_names = {
            source.get("source__name", "").casefold()
            for source in (event.source_snapshot or [])
            if source.get("source__name")
        }
        cleaned = []
        for fact in event.confirmed_facts:
            updated = dict(fact)
            text = REWRITES.get(updated.get("text", ""), updated.get("text", ""))
            lowered = text.casefold()
            if GENERIC_SOURCE_WORDS.search(text):
                continue
            if any(name in lowered for name in publication_names):
                continue
            updated["text"] = text
            cleaned.append(updated)
        if cleaned != event.confirmed_facts:
            event.confirmed_facts = cleaned
            event.save(update_fields=["confirmed_facts"])


class Migration(migrations.Migration):
    dependencies = [("news", "0012_publication_names_in_event_differences")]

    operations = [
        migrations.RunPython(clean_confirmed_facts, migrations.RunPython.noop)
    ]
