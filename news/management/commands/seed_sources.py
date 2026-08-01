from django.core.management.base import BaseCommand

from news.models import Source


SOURCES = (
    ("HotNews", "hotnews.ro", "https://hotnews.ro/feed"),
    ("G4Media", "www.g4media.ro", "https://www.g4media.ro/feed"),
    ("Digi24", "www.digi24.ro", "https://www.digi24.ro/rss"),
    ("SpotMedia", "spotmedia.ro", "https://spotmedia.ro/feed"),
    ("Realitatea", "www.realitatea.net", "https://rss.realitatea.net/stiri.xml"),
    ("Adevărul", "adevarul.ro", "https://adevarul.ro/rss/index"),
    ("Libertatea", "www.libertatea.ro", "https://www.libertatea.ro/feed"),
    ("Economica", "www.economica.net", "https://www.economica.net/feed"),
    ("Profit.ro", "www.profit.ro", "https://www.profit.ro/rss"),
    (
        "Financial Intelligence",
        "financialintelligence.ro",
        "https://financialintelligence.ro/feed/",
    ),
    ("ProSport", "www.prosport.ro", "https://www.prosport.ro/feed"),
    ("DigiSport", "www.digisport.ro", "https://www.digisport.ro/rss"),
    ("Bursa", "www.bursa.ro", "https://www.bursa.ro/titluri-bursa.xml"),
    ("Europa FM", "www.europafm.ro", "https://www.europafm.ro/feed/"),
    ("Mediafax", "www.mediafax.ro", "https://www.mediafax.ro/rss"),
    ("RFI România", "www.rfi.fr", "https://www.rfi.fr/ro/rss"),
    ("StartupCafe", "startupcafe.ro", "https://startupcafe.ro/feed"),
    ("PressOne", "pressone.ro", "https://pressone.ro/feed"),
    ("Recorder", "recorder.ro", "https://recorder.ro/feed/"),
    ("Gândul", "www.gandul.ro", "https://www.gandul.ro/feed"),
    ("Fanatik", "www.fanatik.ro", "https://www.fanatik.ro/feed"),
)


class Command(BaseCommand):
    help = "Adauga lista initiala de surse RSS romanesti verificate."

    def handle(self, *args, **options):
        created_count = 0
        for name, domain, feed_url in SOURCES:
            _, created = Source.objects.update_or_create(
                domain=domain,
                defaults={"name": name, "feed_url": feed_url, "is_active": True},
            )
            created_count += int(created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Sursele sunt pregatite: {len(SOURCES)} active, {created_count} nou create."
            )
        )
