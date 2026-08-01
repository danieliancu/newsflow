from decimal import Decimal
from math import ceil

from django.conf import settings
from django.core.management.base import BaseCommand

from news.models import AIUsage, Article


class Command(BaseCommand):
    help = "Creează estimări de cost pentru clasificările AI istorice fără usage salvat."

    def handle(self, *args, **options):
        created = 0
        million = Decimal("1000000")
        input_rate = Decimal(settings.OPENAI_INPUT_USD_PER_MILLION)
        output_rate = Decimal(settings.OPENAI_OUTPUT_USD_PER_MILLION)
        gbp_rate = Decimal(settings.OPENAI_USD_TO_GBP_RATE)
        articles = Article.objects.exclude(ai_classified_at=None).exclude(ai_usage__isnull=False)
        for article in articles.iterator():
            input_chars = 660 + len(article.title or "") + len(
                article.first_paragraph or article.lead or "(lipsește)"
            )
            output_chars = 70 + len(article.ai_reason or "")
            input_tokens = ceil(input_chars / 3)
            output_tokens = ceil(output_chars / 3)
            input_cost = Decimal(input_tokens) * input_rate / million
            output_cost = Decimal(output_tokens) * output_rate / million
            total_cost = input_cost + output_cost
            usage = AIUsage.objects.create(
                article=article,
                model=article.ai_model or settings.OPENAI_CLASSIFICATION_MODEL,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                input_cost_usd=input_cost,
                output_cost_usd=output_cost,
                total_cost_usd=total_cost,
                usd_to_gbp_rate=gbp_rate,
                total_cost_gbp=total_cost * gbp_rate,
                is_estimated=True,
            )
            AIUsage.objects.filter(pk=usage.pk).update(created_at=article.ai_classified_at)
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Estimari create: {created}."))
