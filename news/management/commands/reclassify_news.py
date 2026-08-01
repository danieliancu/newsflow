from django.core.management.base import BaseCommand

from news.models import Article
from news.services import classify_article


class Command(BaseCommand):
    help = "Reaplica taxonomia tuturor articolelor procesate."

    def handle(self, *args, **options):
        articles = Article.objects.filter(processing_status=Article.ProcessingStatus.PROCESSED)
        count = 0
        for article in articles.iterator():
            classify_article(article)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Reclasificare terminata: {count} articole."))
