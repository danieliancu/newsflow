from urllib.parse import urlparse

from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def public_site_configuration(app_configs, **kwargs):
    if settings.DEBUG:
        return []

    errors = []
    public_url = settings.APP_PUBLIC_URL.rstrip("/")
    parsed = urlparse(public_url)
    if parsed.scheme != "https" or parsed.hostname in {None, "localhost", "127.0.0.1"}:
        errors.append(
            Error(
                "APP_PUBLIC_URL must be an external HTTPS origin in production.",
                hint="Set APP_PUBLIC_URL=https://your-public-domain.example.",
                id="newsflow.E001",
            )
        )
    if parsed.hostname and parsed.hostname not in settings.ALLOWED_HOSTS:
        errors.append(
            Error(
                "The APP_PUBLIC_URL hostname is missing from ALLOWED_HOSTS.",
                hint=f"Add {parsed.hostname} to DJANGO_ALLOWED_HOSTS.",
                id="newsflow.E002",
            )
        )
    if not settings.PUBLIC_CONTACT_EMAIL:
        errors.append(
            Error(
                "A public editorial contact email is required for launch.",
                hint="Set PUBLIC_CONTACT_EMAIL to the address shown on the Contact page.",
                id="newsflow.E003",
            )
        )
    if not settings.SECRET_KEY or settings.SECRET_KEY.startswith("django-insecure-"):
        errors.append(
            Error("DJANGO_SECRET_KEY is unsafe for production.", id="newsflow.E004")
        )
    if settings.EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend":
        errors.append(
            Error("Production email must use the SMTP backend.", id="newsflow.E005")
        )
    public_origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else ""
    if public_origin and public_origin not in settings.CSRF_TRUSTED_ORIGINS:
        errors.append(
            Error(
                "APP_PUBLIC_URL origin is missing from CSRF_TRUSTED_ORIGINS.",
                id="newsflow.E006",
            )
        )
    return errors
