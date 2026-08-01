from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections
from django.db.models import Count, Sum
from django.utils import timezone

from .models import RefreshRun, Source
from .services import ingest_source


_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="newsflow-refresh")


def process_refresh_run(refresh_run_id):
    close_old_connections()
    try:
        refresh_run = RefreshRun.objects.get(pk=refresh_run_id)
        sources = Source.objects.filter(is_active=True)
        refresh_run.sources_attempted = sources.count()
        refresh_run.save(update_fields=["sources_attempted"])
        collected = 0
        failures = 0
        for source in sources:
            try:
                collected += ingest_source(source, refresh_run=refresh_run)
            except Exception:
                failures += 1
        usage = refresh_run.ai_usage.aggregate(
            calls=Count("id"),
            input_tokens=Sum("input_tokens"),
            output_tokens=Sum("output_tokens"),
            cost_usd=Sum("total_cost_usd"),
            cost_gbp=Sum("total_cost_gbp"),
        )
        refresh_run.status = (
            RefreshRun.Status.PARTIAL if failures else RefreshRun.Status.COMPLETED
        )
        refresh_run.finished_at = timezone.now()
        refresh_run.sources_succeeded = refresh_run.sources_attempted - failures
        refresh_run.sources_failed = failures
        refresh_run.articles_collected = collected
        refresh_run.ai_calls = usage["calls"] or 0
        refresh_run.input_tokens = usage["input_tokens"] or 0
        refresh_run.output_tokens = usage["output_tokens"] or 0
        refresh_run.cost_usd = usage["cost_usd"] or 0
        refresh_run.cost_gbp = usage["cost_gbp"] or 0
        refresh_run.save()
    except Exception as exc:
        RefreshRun.objects.filter(pk=refresh_run_id).update(
            status=RefreshRun.Status.FAILED,
            finished_at=timezone.now(),
            note=str(exc)[:300],
        )
    finally:
        close_old_connections()


def enqueue_refresh(refresh_run_id):
    return _executor.submit(process_refresh_run, refresh_run_id)
