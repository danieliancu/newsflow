# Deploy Newsflow on Coolify

This branch is prepared for a Nixpacks deployment on Coolify.

## Application configuration

- Build pack: `Nixpacks`
- Base directory: `/`
- Port: `8000`
- Domain: `https://www.newsflow.ro`
- Branch: `coolify-deploy`
- Install, build and start commands: leave empty; `nixpacks.toml` starts `scripts/start.sh`.

## Persistent storage

Create a persistent volume in Coolify:

- Name: `newsflow-data`
- Destination path: `/app/data`

Then set:

```env
SQLITE_DATABASE_PATH=/app/data/db.sqlite3
```

Without this volume, the SQLite database can be lost when the application is rebuilt.

## Required environment variables

Set these as runtime environment variables in Coolify. Do not commit real secrets.

```env
DJANGO_SETTINGS_MODULE=config.production
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_ALLOWED_HOSTS=newsflow.ro,www.newsflow.ro
DJANGO_CSRF_TRUSTED_ORIGINS=https://newsflow.ro,https://www.newsflow.ro
APP_PUBLIC_URL=https://www.newsflow.ro
PUBLIC_CONTACT_EMAIL=office@newsflow.ro
GOOGLE_ANALYTICS_ID=G-DDT1Z5SD9L
TIME_ZONE=Europe/London

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=replace-with-your-resend-api-key
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
DEFAULT_FROM_EMAIL=Newsflow <no-reply@newsflow.ro>

OPENAI_API_KEY=replace-with-your-openai-api-key
OPENAI_CLASSIFICATION_ENABLED=true

SQLITE_DATABASE_PATH=/app/data/db.sqlite3
PORT=8000
GUNICORN_WORKERS=2
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=120
```

Generate a Django secret locally with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## First deployment

The startup script runs these automatically on every container start:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

After the first successful deployment, open the Coolify terminal for the application and run once:

```bash
python manage.py seed_taxonomy
python manage.py seed_sources
python manage.py createsuperuser
```

## Scheduled news collection

Create a Coolify scheduled task that runs once per hour:

```bash
python manage.py automatic_news_update
```

Do not expose news collection as a public web endpoint.
