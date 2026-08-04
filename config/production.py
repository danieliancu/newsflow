"""Production settings used by the Coolify deployment."""

import os
from pathlib import Path

from .settings import *  # noqa: F403


# Serve static files directly from the application container.
if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:  # noqa: F405
    security_middleware_index = MIDDLEWARE.index(  # noqa: F405
        "django.middleware.security.SecurityMiddleware"
    )
    MIDDLEWARE.insert(  # noqa: F405
        security_middleware_index + 1,
        "whitenoise.middleware.WhiteNoiseMiddleware",
    )

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # Compress static assets without manifest URL rewriting. A vendored
        # Lucide bundle references an optional source map that is not shipped,
        # which makes ManifestStaticFilesStorage fail during collectstatic.
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}


# Keep SQLite outside the disposable application filesystem when a persistent
# Coolify volume is mounted and SQLITE_DATABASE_PATH is configured.
sqlite_database_path = os.getenv("SQLITE_DATABASE_PATH", "").strip()
if sqlite_database_path:
    database_path = Path(sqlite_database_path)
    if not database_path.is_absolute():
        database_path = BASE_DIR / database_path  # noqa: F405
    DATABASES["default"]["NAME"] = database_path  # noqa: F405
