import os
import socket
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from news.event_services import process_event_queue, synchronize_events
from news.models import (
    AIUsage,
    AutomaticUpdateLock,
    AutomaticUpdateSchedule,
    RefreshRun,
    Source,
)
from news.services import ingest_source


LOCK_NAME = "automatic_news_update"


class Command(BaseCommand):
    help = "Colectează automat știrile și procesează evenimentele eligibile."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Rulează imediat, chiar dacă ora este în afara programului din admin.",
        )

    def _acquire_lock(self):
        owner = f"{socket.gethostname()}:{os.getpid()}"
        stale_before = timezone.now() - timedelta(
            minutes=settings.NEWSFLOW_AUTOMATIC_LOCK_TIMEOUT_MINUTES
        )
        with transaction.atomic():
            lock, _ = AutomaticUpdateLock.objects.select_for_update().get_or_create(
                name=LOCK_NAME
            )
            if lock.acquired_at and lock.acquired_at > stale_before:
                return False, lock.owner
            lock.acquired_at = timezone.now()
            lock.owner = owner
            lock.save(update_fields=["acquired_at", "owner"])
        return True, owner

    def _release_lock(self, owner):
        AutomaticUpdateLock.objects.filter(name=LOCK_NAME, owner=owner).update(
            acquired_at=None, owner=""
        )

    def handle(self, *args, **options):
        schedule = AutomaticUpdateSchedule.get_solo()
        if not options["force"] and not schedule.is_due():
            self.stdout.write(
                self.style.WARNING(
                    "În afara programului automat; nu a fost pornită nicio rulare. "
                    "Folosește --force pentru execuție imediată."
                )
            )
            return
        acquired, owner = self._acquire_lock()
        if not acquired:
            run = RefreshRun.objects.create(
                trigger=RefreshRun.Trigger.AUTOMATIC,
                status=RefreshRun.Status.SKIPPED,
                finished_at=timezone.now(),
                note=f"Rulare automată deja activă: {owner}"[:300],
            )
            self.stdout.write(self.style.WARNING(f"Rularea a fost omisă ({run.pk})."))
            return

        run = RefreshRun.objects.create(trigger=RefreshRun.Trigger.AUTOMATIC)
        try:
            sources = Source.objects.filter(is_active=True)
            run.sources_attempted = sources.count()
            run.save(update_fields=["sources_attempted"])
            collected = 0
            failures = 0
            for source in sources:
                try:
                    collected += ingest_source(source, refresh_run=run)
                except Exception:
                    failures += 1

            synchronize_events()
            events_created, events_updated, events_blocked = process_event_queue(
                refresh_run=run
            )
            usage = run.ai_usage.aggregate(
                calls=Count("id"),
                input_tokens=Sum("input_tokens"),
                output_tokens=Sum("output_tokens"),
                cost_usd=Sum("total_cost_usd"),
                cost_gbp=Sum("total_cost_gbp"),
            )
            classification_cost = (
                run.ai_usage.filter(
                    usage_type=AIUsage.UsageType.ARTICLE_CLASSIFICATION
                ).aggregate(value=Sum("total_cost_gbp"))["value"]
                or 0
            )
            event_cost = (
                run.ai_usage.filter(event__isnull=False).aggregate(
                    value=Sum("total_cost_gbp")
                )["value"]
                or 0
            )
            run.status = (
                RefreshRun.Status.PARTIAL if failures else RefreshRun.Status.COMPLETED
            )
            run.finished_at = timezone.now()
            run.sources_succeeded = run.sources_attempted - failures
            run.sources_failed = failures
            run.articles_collected = collected
            run.ai_calls = usage["calls"] or 0
            run.input_tokens = usage["input_tokens"] or 0
            run.output_tokens = usage["output_tokens"] or 0
            run.cost_usd = usage["cost_usd"] or 0
            run.cost_gbp = usage["cost_gbp"] or 0
            run.classification_cost_gbp = classification_cost
            run.event_cost_gbp = event_cost
            run.events_created = events_created
            run.events_updated = events_updated
            run.events_budget_blocked = events_blocked
            run.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Rulare {run.pk}: {collected} articole, "
                    f"{events_created} evenimente noi, {events_updated} actualizate."
                )
            )
        except Exception as exc:
            run.status = RefreshRun.Status.FAILED
            run.finished_at = timezone.now()
            run.note = str(exc)[:300]
            run.save(update_fields=["status", "finished_at", "note"])
            raise
        finally:
            self._release_lock(owner)
