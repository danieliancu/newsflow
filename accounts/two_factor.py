import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import EmailChallenge


class ChallengeRateLimited(Exception):
    pass


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def client_ip(request):
    return request.META.get("REMOTE_ADDR") or None


def _check_rate_limit(user, ip_address):
    since = timezone.now() - timedelta(hours=1)
    recent = EmailChallenge.objects.filter(created_at__gte=since)
    limit = settings.TWO_FACTOR_MAX_SENDS_PER_HOUR
    if recent.filter(user=user).count() >= limit:
        raise ChallengeRateLimited
    if ip_address and recent.filter(ip_address=ip_address).count() >= limit:
        raise ChallengeRateLimited


def _verification_url(challenge, raw_token):
    path = reverse(
        "verify_email_challenge",
        kwargs={"public_id": challenge.public_id, "token": raw_token},
    )
    return urljoin(settings.APP_PUBLIC_URL.rstrip("/") + "/", path.lstrip("/"))


@transaction.atomic
def create_and_send_challenge(*, user, purpose, ip_address=None, next_url=""):
    _check_rate_limit(user, ip_address)
    now = timezone.now()
    EmailChallenge.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
    raw_token = secrets.token_urlsafe(32)
    challenge = EmailChallenge.objects.create(
        user=user,
        token_hash=token_hash(raw_token),
        purpose=purpose,
        next_url=next_url[:500],
        ip_address=ip_address,
        expires_at=now + timedelta(minutes=settings.TWO_FACTOR_TOKEN_TTL_MINUTES),
        sent_at=now,
    )
    verification_url = _verification_url(challenge, raw_token)
    subject = (
        "Confirmă contul Newsflow"
        if purpose == EmailChallenge.Purpose.REGISTRATION
        else "Confirmă autentificarea în Newsflow"
    )
    message = (
        "Accesează linkul de mai jos pentru a continua. "
        f"Linkul expiră în {settings.TWO_FACTOR_TOKEN_TTL_MINUTES} minute și poate fi folosit o singură dată.\n\n"
        f"{verification_url}\n\n"
        "Dacă nu ai solicitat acest email, îl poți ignora."
    )
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception:
        challenge.used_at = timezone.now()
        challenge.save(update_fields=["used_at"])
        raise
    return challenge
