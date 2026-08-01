from django.core.management.base import BaseCommand

from news.models import Article
from news.services import assign_duplicate


class Command(BaseCommand):
    help = "Grupeaza articolele existente care descriu acelasi eveniment."

    def handle(self, *args, **options):
        articles = Article.objects.filter(
            processing_status=Article.ProcessingStatus.PROCESSED
        ).order_by("published_at", "collected_at")
        Article.objects.update(duplicate_of=None, duplicate_score=0)
        duplicates = 0
        for article in articles.iterator():
            if assign_duplicate(article):
                duplicates += 1
        self.stdout.write(
            self.style.SUCCESS(f"Deduplicare terminata: {duplicates} articole grupate.")
        )
