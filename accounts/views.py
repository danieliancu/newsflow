import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    DeleteAccountForm,
    EmailPasswordLoginForm,
    PreferenceForm,
    RegistrationForm,
)
from .models import EmailChallenge, User
from .two_factor import (
    ChallengeRateLimited,
    client_ip,
    create_and_send_challenge,
    token_hash,
)
from news.models import Article, Source
from recommendations.models import Interaction
from taxonomy.models import Category, Topic


@login_required
def account_dashboard(request):
    return render(
        request,
        "accounts/dashboard.html",
        {
            "saved_count": request.user.interactions.filter(kind="saved").count(),
            "preferred_sources_count": request.user.source_preferences.filter(
                is_blocked=False
            ).count(),
            "recent_count": request.user.interactions.filter(
                kind=Interaction.Kind.OPENED
            ).count(),
            "hidden_count": request.user.interactions.filter(
                kind=Interaction.Kind.HIDDEN
            ).count()
            + request.user.source_preferences.filter(is_blocked=True).count(),
        },
    )


@login_required
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Parola a fost schimbată.")
        return redirect("account_dashboard")
    return render(request, "accounts/change_password.html", {"form": form})


@login_required
def delete_account(request):
    form = DeleteAccountForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Contul și datele asociate au fost șterse.")
        return redirect("feed")
    return render(request, "accounts/delete_account.html", {"form": form})


def available_categories():
    return (
        Category.objects.filter(
            is_active=True,
            articles__processing_status=Article.ProcessingStatus.PROCESSED,
            articles__duplicate_of__isnull=True,
        )
        .distinct()
        .order_by("name")
    )


def preference_context(form):
    def selected_ids(field_name):
        values = form.data.getlist(field_name) if form.is_bound else form.initial.get(field_name, [])
        return {int(value) for value in values}

    selected_category_ids = selected_ids("categories")
    selected_source_ids = selected_ids("preferred_sources")
    selected_topic_ids = selected_ids("topics")
    blocked_source_ids = selected_ids("blocked_sources")
    if form.is_bound:
        followed_terms_value = form.data.get("followed_terms", "")
        followed_terms = [
            " ".join(value.strip().split())
            for value in followed_terms_value.replace("\r", "\n").replace(";", ",").replace("\n", ",").split(",")
            if value.strip()
        ]
    else:
        followed_terms = list(form.user.followed_terms.values_list("term", flat=True))

    return {
        "preference_form": form,
        "preference_categories": available_categories(),
        "preference_sources": Source.objects.filter(is_active=True).order_by("name"),
        "preference_topics": Topic.objects.filter(is_active=True)
        .select_related("category")
        .order_by("category__name", "name"),
        "selected_category_ids": selected_category_ids,
        "selected_source_ids": selected_source_ids,
        "selected_topic_ids": selected_topic_ids,
        "blocked_source_ids": blocked_source_ids,
        "has_selected_categories": bool(selected_category_ids),
        "has_selected_sources": bool(selected_source_ids),
        "has_selected_topics": bool(selected_topic_ids),
        "has_blocked_sources": bool(blocked_source_ids),
        "followed_terms": followed_terms,
        "has_followed_terms": bool(followed_terms),
    }


def register(request):
    if request.user.is_authenticated:
        return redirect("feed")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.is_active = False
        user.save()
        _set_pending_challenge(request, user, EmailChallenge.Purpose.REGISTRATION, "preferences")
        _send_pending_challenge(request, user, EmailChallenge.Purpose.REGISTRATION, "preferences")
        return redirect("email_challenge_pending")
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("feed")
    form = EmailPasswordLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        next_url = _safe_next_url(request, request.POST.get("next", ""))
        purpose = (
            EmailChallenge.Purpose.LOGIN
            if user.is_active
            else EmailChallenge.Purpose.REGISTRATION
        )
        destination = next_url or ("feed" if user.is_active else "preferences")
        _set_pending_challenge(request, user, purpose, destination)
        _send_pending_challenge(request, user, purpose, destination)
        return redirect("email_challenge_pending")
    return render(
        request,
        "accounts/login.html",
        {"form": form, "next": _safe_next_url(request, request.GET.get("next", ""))},
    )


def _safe_next_url(request, value):
    if value.startswith("/") and url_has_allowed_host_and_scheme(
        value, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return value
    return ""


def _set_pending_challenge(request, user, purpose, next_url):
    request.session["pending_email_challenge"] = {
        "user_id": user.pk,
        "purpose": purpose,
        "next_url": next_url,
    }


def _send_pending_challenge(request, user, purpose, next_url):
    try:
        create_and_send_challenge(
            user=user,
            purpose=purpose,
            ip_address=client_ip(request),
            next_url=next_url,
        )
        return True
    except ChallengeRateLimited:
        messages.error(
            request,
            "Ai solicitat prea multe linkuri. Încearcă din nou peste o oră.",
        )
        return False
    except Exception:
        messages.error(
            request,
            "Emailul nu a putut fi trimis momentan. Încearcă din nou mai târziu.",
        )
        return False


def email_challenge_pending(request):
    pending = request.session.get("pending_email_challenge")
    if not pending:
        return redirect("login")
    return render(request, "accounts/email_challenge_pending.html")


@require_POST
def resend_email_challenge(request):
    pending = request.session.get("pending_email_challenge")
    if not pending:
        return redirect("login")
    user = get_object_or_404(User, pk=pending["user_id"])
    latest = user.email_challenges.order_by("-sent_at").first()
    cooldown = settings.TWO_FACTOR_RESEND_COOLDOWN_SECONDS
    if latest and latest.sent_at > timezone.now() - timedelta(seconds=cooldown):
        messages.info(
            request,
            f"Poți solicita un alt link după {cooldown} de secunde.",
        )
        return redirect("email_challenge_pending")
    sent = _send_pending_challenge(
        request,
        user,
        pending["purpose"],
        pending.get("next_url", ""),
    )
    if sent:
        messages.success(request, "Dacă solicitarea este validă, un link nou a fost trimis.")
    return redirect("email_challenge_pending")


@transaction.atomic
def verify_email_challenge(request, public_id, token):
    challenge = (
        EmailChallenge.objects.select_for_update()
        .select_related("user")
        .filter(public_id=public_id)
        .first()
    )
    now = timezone.now()
    valid_token = challenge and secrets.compare_digest(
        challenge.token_hash, token_hash(token)
    )
    if (
        not challenge
        or not valid_token
        or challenge.used_at is not None
        or challenge.expires_at <= now
    ):
        return render(request, "accounts/email_challenge_invalid.html", status=400)

    challenge.used_at = now
    challenge.save(update_fields=["used_at"])
    user = challenge.user
    if challenge.purpose == EmailChallenge.Purpose.REGISTRATION and not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active", "updated_at"])
    if not user.is_active:
        return render(request, "accounts/email_challenge_invalid.html", status=400)

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session.pop("pending_email_challenge", None)
    destination = challenge.next_url or "feed"
    if destination.startswith("/"):
        return redirect(destination)
    return redirect(destination if destination in {"feed", "preferences"} else "feed")


@login_required
def preferences(request):
    form = PreferenceForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            form.save()
        messages.success(request, "Preferințele au fost salvate.")
        return redirect("feed")
    return render(request, "accounts/preferences.html", preference_context(form))
