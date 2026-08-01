import json
from django.conf import settings
from django.utils import timezone
from openai import OpenAI

from taxonomy.models import Category
from .ai_usage import record_ai_usage
from .models import AIUsage


def classify_article_with_ai(article, refresh_run=None):
    if not settings.OPENAI_CLASSIFICATION_ENABLED or not settings.OPENAI_API_KEY:
        return False

    categories = list(Category.objects.filter(is_active=True).order_by("name"))
    if not categories:
        return False

    category_names = [category.name for category in categories]
    category_by_name = {category.name: category for category in categories}
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.responses.create(
            model=settings.OPENAI_CLASSIFICATION_MODEL,
            store=False,
            instructions=(
                "Clasifică știrea în exact una dintre categoriile permise. "
                "Folosește sensul editorial al titlului și paragrafului, nu doar cuvinte-cheie. "
                "Confidence trebuie să fie între 0 și 1. Dacă nicio categorie nu este potrivită, "
                "alege cea mai apropiată și setează confidence sub 0.55. "
                "Reason trebuie să fie în limba română, factual și sub 180 de caractere."
            ),
            input=(
                f"Categorii permise: {', '.join(category_names)}\n"
                f"Titlu: {article.title}\n"
                f"Primul paragraf: {article.first_paragraph or article.lead or '(lipsește)'}"
            ),
            max_output_tokens=200,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "news_classification",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "enum": category_names},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "reason": {"type": "string"},
                        },
                        "required": ["category", "confidence", "reason"],
                        "additionalProperties": False,
                    },
                }
            },
        )
        record_ai_usage(
            response,
            article=article,
            refresh_run=refresh_run,
            model=settings.OPENAI_CLASSIFICATION_MODEL,
            input_rate=settings.OPENAI_INPUT_USD_PER_MILLION,
            cached_input_rate=settings.OPENAI_CACHED_INPUT_USD_PER_MILLION,
            output_rate=settings.OPENAI_OUTPUT_USD_PER_MILLION,
            usage_type=AIUsage.UsageType.ARTICLE_CLASSIFICATION,
        )
        result = json.loads(response.output_text)
        category = category_by_name[result["category"]]
        confidence = max(0.0, min(1.0, float(result["confidence"])))
        article.ai_suggested_category = category
        article.ai_confidence = confidence
        article.ai_reason = result["reason"][:300]
        article.ai_model = settings.OPENAI_CLASSIFICATION_MODEL
        article.ai_classified_at = timezone.now()
        update_fields = [
            "ai_suggested_category",
            "ai_confidence",
            "ai_reason",
            "ai_model",
            "ai_classified_at",
        ]
        if confidence >= settings.OPENAI_CLASSIFICATION_AUTO_THRESHOLD:
            article.primary_category = category
            update_fields.append("primary_category")
        article.save(update_fields=update_fields)
        return article.primary_category_id is not None
    except Exception:
        return False
