from django.conf import settings
from django.core.management.base import BaseCommand

from news.models import Article
from news.http_client import SafeHTTPClient
from news.services import _can_fetch, decode_response_text, extract_image_url_from_html


class Command(BaseCommand):
    help = "Completează URL-urile imaginilor pentru articolele care nu au imagine."

    def handle(self, *args, **options):
        articles = (
            Article.objects.filter(
                processing_status=Article.ProcessingStatus.PROCESSED,
                image_url="",
            )
            .select_related("source")
            .order_by("pk")
        )
        client = SafeHTTPClient()
        robots_cache = {}
        updated = 0
        without_image = 0
        blocked = 0
        failed = 0

        for article in articles.iterator():
            try:
                if not _can_fetch(article.canonical_url, client, robots_cache):
                    blocked += 1
                    continue
                response = client.get(
                    article.canonical_url,
                    max_bytes=settings.NEWSFLOW_MAX_PAGE_BYTES,
                )
                image_url = extract_image_url_from_html(
                    decode_response_text(response),
                    article.canonical_url,
                )
                if image_url:
                    article.image_url = image_url
                    article.save(update_fields=["image_url"])
                    updated += 1
                else:
                    without_image += 1
            except Exception:
                failed += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Backfill imagini terminat: "
                f"{updated} actualizate, {without_image} fără imagine, "
                f"{blocked} blocate de robots.txt, {failed} erori."
            )
        )
