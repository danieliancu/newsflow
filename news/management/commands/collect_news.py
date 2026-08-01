from django.core.management.base import BaseCommand, CommandError

from news.models import Source
from news.services import ingest_source


class Command(BaseCommand):
    help = "Colecteaza articole noi din feedurile RSS active."

    def add_arguments(self, parser):
        parser.add_argument("--source", type=int, help="Colecteaza doar sursa cu acest ID.")
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Reextrage si articolele deja procesate din cele mai recente intrari RSS.",
        )

    def handle(self, *args, **options):
        sources = Source.objects.filter(is_active=True)
        if options["source"]:
            sources = sources.filter(pk=options["source"])
        if not sources.exists():
            raise CommandError("Nu exista surse active pentru criteriile primite.")

        total = 0
        failures = 0
        result_label = "articole actualizate" if options["refresh"] else "articole noi"
        for source in sources:
            try:
                count = ingest_source(source, refresh=options["refresh"])
                total += count
                self.stdout.write(self.style.SUCCESS(f"Sursa {source.pk}: {count} {result_label}"))
            except Exception as exc:
                failures += 1
                self.stderr.write(self.style.ERROR(f"Sursa {source.pk}: colectarea a esuat"))
        self.stdout.write(f"Total: {total} {result_label}; {failures} surse cu erori.")
