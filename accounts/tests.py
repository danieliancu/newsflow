import re
from datetime import timedelta

from django.core import mail
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import EmailChallenge, User


class UserTests(TestCase):
    def test_email_is_unique_and_password_is_hashed(self):
        user = User.objects.create_user(email="cititor@example.ro", password="o-parola-puternica")
        self.assertNotEqual(user.password, "o-parola-puternica")
        self.assertTrue(user.check_password("o-parola-puternica"))
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="cititor@example.ro", password="alta-parola")

    def test_account_dashboard_requires_login_and_links_to_user_sections(self):
        user = User.objects.create_user(
            email="meniu@example.ro", password="parola-test-123"
        )
        anonymous_response = self.client.get("/account/")
        self.assertEqual(anonymous_response.status_code, 302)

        self.client.force_login(user)
        response = self.client.get("/account/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/account/preferences/"')
        self.assertContains(response, 'href="/saved/"')
        self.assertContains(response, 'href="/recently-read/"')
        self.assertContains(response, 'href="/hidden/"')
        self.assertContains(response, 'href="/account/password/"')
        self.assertContains(response, 'href="/account/delete/"')
        self.assertContains(response, "meniu@example.ro")

    def test_user_can_change_password_and_stays_logged_in(self):
        user = User.objects.create_user(
            email="parola@example.ro", password="parola-veche-123"
        )
        self.client.force_login(user)

        response = self.client.post(
            "/account/password/",
            {
                "old_password": "parola-veche-123",
                "new_password1": "parola-noua-sigura-456",
                "new_password2": "parola-noua-sigura-456",
            },
        )

        self.assertRedirects(response, "/account/")
        user.refresh_from_db()
        self.assertTrue(user.check_password("parola-noua-sigura-456"))
        self.assertEqual(self.client.get("/account/").status_code, 200)

    def test_account_deletion_requires_correct_password(self):
        user = User.objects.create_user(
            email="stergere@example.ro", password="parola-test-123"
        )
        self.client.force_login(user)

        invalid = self.client.post(
            "/account/delete/",
            {"password": "gresita", "confirmation": "on"},
        )
        self.assertEqual(invalid.status_code, 200)
        self.assertTrue(User.objects.filter(pk=user.pk).exists())

        response = self.client.post(
            "/account/delete/",
            {"password": "parola-test-123", "confirmation": "on"},
        )
        self.assertRedirects(response, "/")
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertNotIn("_auth_user_id", self.client.session)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    APP_PUBLIC_URL="http://testserver",
    TWO_FACTOR_TOKEN_TTL_MINUTES=15,
    TWO_FACTOR_RESEND_COOLDOWN_SECONDS=60,
    TWO_FACTOR_MAX_SENDS_PER_HOUR=5,
)
class EmailTwoFactorTests(TestCase):
    password = "o-parola-puternica"

    def setUp(self):
        self.user = User.objects.create_user(
            email="cititor@example.ro",
            password=self.password,
        )

    def _login_request(self, **extra):
        data = {
            "email": self.user.email,
            "password": self.password,
            **extra,
        }
        return self.client.post(reverse("login"), data)

    def _verification_path(self, email_message=None):
        message = email_message or mail.outbox[-1]
        match = re.search(r"http://testserver(/[^\s]+)", message.body)
        self.assertIsNotNone(match)
        return match.group(1)

    def test_wrong_password_does_not_send_email_or_authenticate(self):
        response = self.client.post(
            reverse("login"),
            {"email": self.user.email, "password": "gresita"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Emailul sau parola nu sunt corecte.")
        self.assertEqual(len(mail.outbox), 0)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_correct_password_requires_email_link(self):
        response = self._login_request()
        self.assertRedirects(response, reverse("email_challenge_pending"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(EmailChallenge.objects.count(), 1)

    def test_valid_link_authenticates_once_and_preserves_next(self):
        self._login_request(next="/saved/")
        path = self._verification_path()
        response = self.client.get(path)
        self.assertRedirects(response, "/saved/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

        reused = self.client.get(path)
        self.assertEqual(reused.status_code, 400)
        self.assertContains(reused, "Link indisponibil", status_code=400)

    def test_expired_and_invalid_links_are_rejected(self):
        self._login_request()
        challenge = EmailChallenge.objects.get()
        challenge.expires_at = timezone.now() - timedelta(seconds=1)
        challenge.save(update_fields=["expires_at"])
        expired = self.client.get(self._verification_path())
        self.assertEqual(expired.status_code, 400)
        invalid = self.client.get(
            reverse(
                "verify_email_challenge",
                kwargs={"public_id": challenge.public_id, "token": "token-gresit"},
            )
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_registration_stays_inactive_until_confirmation(self):
        response = self.client.post(
            reverse("register"),
            {
                "email": "nou@example.ro",
                "password1": self.password,
                "password2": self.password,
            },
        )
        self.assertRedirects(response, reverse("email_challenge_pending"))
        new_user = User.objects.get(email="nou@example.ro")
        self.assertFalse(new_user.is_active)
        self.assertNotIn("_auth_user_id", self.client.session)

        response = self.client.get(self._verification_path())
        self.assertRedirects(response, reverse("preferences"))
        new_user.refresh_from_db()
        self.assertTrue(new_user.is_active)
        self.assertEqual(int(self.client.session["_auth_user_id"]), new_user.pk)

    def test_resend_obeys_cooldown_and_invalidates_previous_link(self):
        self._login_request()
        first_path = self._verification_path()
        blocked = self.client.post(reverse("resend_email_challenge"))
        self.assertRedirects(blocked, reverse("email_challenge_pending"))
        self.assertEqual(len(mail.outbox), 1)

        first = EmailChallenge.objects.get()
        first.sent_at = timezone.now() - timedelta(seconds=61)
        first.save(update_fields=["sent_at"])
        resent = self.client.post(reverse("resend_email_challenge"))
        self.assertRedirects(resent, reverse("email_challenge_pending"))
        self.assertEqual(len(mail.outbox), 2)
        first.refresh_from_db()
        self.assertIsNotNone(first.used_at)
        self.assertEqual(self.client.get(first_path).status_code, 400)

    @override_settings(TWO_FACTOR_RESEND_COOLDOWN_SECONDS=0)
    def test_hourly_send_limit_is_enforced(self):
        self._login_request()
        for _ in range(4):
            self.client.post(reverse("resend_email_challenge"))
        self.assertEqual(len(mail.outbox), 5)
        self.client.post(reverse("resend_email_challenge"))
        self.assertEqual(len(mail.outbox), 5)
        self.assertEqual(EmailChallenge.objects.count(), 5)

    def test_external_next_url_is_not_used(self):
        self._login_request(next="https://evil.example/phishing")
        response = self.client.get(self._verification_path())
        self.assertRedirects(response, reverse("feed"))
