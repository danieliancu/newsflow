from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import path, reverse
from django.views.generic import RedirectView

from . import views


def legacy_verify_email_challenge(request, public_id, token):
    return redirect(
        reverse(
            "verify_email_challenge",
            kwargs={"public_id": public_id, "token": token},
        ),
        permanent=True,
    )


urlpatterns = [
    path(
        "inregistrare/",
        RedirectView.as_view(pattern_name="register", permanent=True),
    ),
    path(
        "autentificare/",
        RedirectView.as_view(pattern_name="login", permanent=True),
    ),
    path(
        "verificare-email/",
        RedirectView.as_view(pattern_name="email_challenge_pending", permanent=True),
    ),
    path(
        "verificare-email/retrimite/",
        views.resend_email_challenge,
    ),
    path(
        "verificare-email/<uuid:public_id>/<str:token>/",
        legacy_verify_email_challenge,
    ),
    path("iesire/", auth_views.LogoutView.as_view()),
    path("preferinte/", views.preferences),
]
