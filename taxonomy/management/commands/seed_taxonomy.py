from django.core.management.base import BaseCommand
from django.utils.text import slugify

from taxonomy.models import Category, KeywordRule, Topic


TAXONOMY = {
    "Politică": {
        "Guvern": ["guvern", "guvernul", "executiv", "premier", "minister"],
        "Parlament": [
            "parlament",
            "parlamentul",
            "senat",
            "senatul",
            "camera deputaților",
            "deputat",
            "senator",
        ],
        "Alegeri": ["alegeri", "electoral", "candidat", "vot"],
        "Partide și politică": [
            "PSD",
            "PNL",
            "USR",
            "UDMR",
            "AUR",
            "politică",
            "politice",
        ],
    },
    "Economie": {
        "Finanțe": ["finanțe", "bancă", "dobândă", "inflație", "curs valutar"],
        "Companii": ["companie", "afaceri", "investiție", "angajați"],
        "Energie": [
            "energie",
            "electricitate",
            "gaze",
            "petrol",
            "petrolier",
            "petrolieră",
            "petrolieri",
            "petroliere",
        ],
        "Fonduri europene": ["fonduri UE", "fonduri europene", "granturi", "finanțare europeană"],
        "Agricultură": ["agricultură", "agricol", "fermă", "ferme", "fermier", "fermieri"],
    },
    "Societate": {
        "Educație": ["educație", "școală", "universitate", "elev", "student"],
        "Sănătate": ["sănătate", "spital", "medic", "pacient"],
        "Justiție": ["justiție", "instanță", "procuror", "judecător"],
    },
    "Tehnologie": {
        "Inteligență artificială": ["inteligență artificială", "AI", "machine learning"],
        "Securitate cibernetică": ["securitate cibernetică", "atac cibernetic", "malware", "ransomware"],
        "Produse digitale": ["aplicație", "software", "platformă digitală", "startup"],
    },
    "Internațional": {
        "Rusia": ["Rusia", "Kremlin", "Moscova", "Putin"],
        "Uniunea Europeană": ["Uniunea Europeană", "Bruxelles"],
        "Statele Unite": ["Statele Unite", "SUA", "Washington"],
        "Ucraina": ["Ucraina", "Kiev", "Zelenski"],
    },
    "Mediu": {
        "Climă": ["climă", "schimbări climatice", "emisii", "încălzire globală"],
        "Vreme": ["vreme", "meteo", "furtună", "caniculă", "ninsoare"],
    },
    "Sport": {
        "Fotbal": ["fotbal", "liga 1", "superliga", "gol", "meci"],
        "Tenis": ["tenis", "wta", "atp", "turneu"],
        "Alte sporturi": [
            "scrimă",
            "scrimer",
            "scrimeră",
            "atletism",
            "handbal",
            "baschet",
            "volei",
            "natație",
            "gimnastică",
            "ciclism",
            "formula 1",
        ],
    },
    "Cultură": {
        "Film": ["film", "cinema", "regizor", "actor"],
        "Carte": ["carte", "literatură", "autor", "editură"],
        "Muzică": ["muzică", "concert", "artist", "album"],
    },
}


class Command(BaseCommand):
    help = "Creează taxonomia inițială românească și regulile de clasificare."

    def handle(self, *args, **options):
        KeywordRule.objects.filter(phrase="ai").delete()
        KeywordRule.objects.filter(topic__name="Uniunea Europeană", phrase="UE").delete()
        rules_created = 0
        for category_name, topics in TAXONOMY.items():
            category, _ = Category.objects.get_or_create(
                name=category_name, defaults={"slug": slugify(category_name)}
            )
            for topic_name, keywords in topics.items():
                topic, _ = Topic.objects.get_or_create(
                    category=category,
                    name=topic_name,
                    defaults={"slug": slugify(topic_name)},
                )
                for phrase in keywords:
                    _, created = KeywordRule.objects.get_or_create(topic=topic, phrase=phrase)
                    rules_created += int(created)
        self.stdout.write(self.style.SUCCESS(f"Taxonomia este pregatita; {rules_created} reguli noi."))
