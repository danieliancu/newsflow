from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.account_dashboard, name="account_dashboard"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("email-verification/", views.email_challenge_pending, name="email_challenge_pending"),
    path("email-verification/resend/", views.resend_email_challenge, name="resend_email_challenge"),
    path(
        "email-verification/<uuid:public_id>/<str:token>/",
        views.verify_email_challenge,
        name="verify_email_challenge",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("preferences/", views.preferences, name="preferences"),
    path("password/", views.change_password, name="change_password"),
    path("delete/", views.delete_account, name="delete_account"),
]
