from .models import Interaction
from django.db.models import Max
from news.models import Article
from news.models import RefreshRun, Source
from taxonomy.models import Category


def saved_news_count(request):
    if not request.user.is_authenticated:
        return {"saved_news_count": 0}
    count = (
        Interaction.objects.filter(user=request.user, kind=Interaction.Kind.SAVED)
        .values("article_id")
        .distinct()
        .count()
    )
    return {"saved_news_count": count}


def navigation_categories(request):
    categories = Category.objects.filter(
        is_active=True,
        articles__processing_status=Article.ProcessingStatus.PROCESSED,
        articles__duplicate_of__isnull=True,
    ).distinct()
    return {"navigation_categories": categories}


def latest_news_refresh(request):
    latest = Source.objects.filter(is_active=True).aggregate(
        latest=Max("last_checked_at")
    )["latest"]
    running = RefreshRun.objects.filter(status=RefreshRun.Status.RUNNING).first()
    return {"latest_news_refresh": latest, "running_refresh": running}
