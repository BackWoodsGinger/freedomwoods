# Production deployment

## Checklist before going live

1. **Environment variables** (e.g. in systemd, .env, or your host’s config):
   - `DJANGO_SECRET_KEY` – long random string (e.g. `python -c "import secrets; print(secrets.token_urlsafe(50))"`).
   - `DJANGO_DEBUG=0`
   - `DJANGO_ALLOWED_HOSTS` – comma-separated (e.g. `home.freedomwoods.online`).
   - `DJANGO_CSRF_TRUSTED_ORIGINS` – comma-separated HTTPS origins (e.g. `https://home.freedomwoods.online`).

2. **Static files**: run `python manage.py collectstatic --noinput` and serve the app with gunicorn (WhiteNoise will serve `/static/`).

3. **HTTPS**: Use TLS in front of the app (e.g. nginx or Caddy). With `DJANGO_DEBUG=0`, Django sets secure cookies and HSTS.

4. **Logs**: When `DEBUG` is off, logs go to `log/django.log` (create `log/` if needed and ensure the process can write there).

5. **Database**: Default is SQLite. For higher load or multi-process, consider PostgreSQL and set `DATABASES` in settings (e.g. from env).

6. **Run with gunicorn**, e.g.:
   ```bash
   gunicorn freedomwoods.wsgi:application --bind 0.0.0.0:8000
   ```

## What’s enabled in production (when `DJANGO_DEBUG=0`)

- Secret key and debug from environment (no hardcoded production secret).
- Security headers: XSS filter, X-Content-Type-Options, HSTS.
- Secure and HTTP-only behavior for session and CSRF cookies; HTTPS redirect (unless disabled).
- WhiteNoise serving static files with hashed names.
- Rotating file logging for errors.
