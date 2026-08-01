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
    return errors
