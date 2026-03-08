# Production deployment

## Zero-config option (recommended)

You don’t need to set any environment variables. On first run the app will:

- Create a random **secret key** and save it in `.secret_key` in the project root (so restarts use the same key).
- Use **DEBUG=0**, **ALLOWED_HOSTS** including `home.freedomwoods.online`, and **SECURE_SSL_REDIRECT=0** (suitable behind Cloudflare Tunnel).

Just pull, install, collect static, and run gunicorn.

## Checklist before going live

1. **Pull and install**
   ```bash
   git pull
   source venv/bin/activate   # or your venv path
   pip install -r requirements.txt
   ```

2. **Static files**
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Log directory** (optional; for `log/django.log`)
   ```bash
   mkdir -p log
   ```

4. **Run with gunicorn**
   ```bash
   gunicorn freedomwoods.wsgi:application --bind 0.0.0.0:8000
   ```
   Or restart your systemd service if you use one.

5. **HTTPS** is handled by Cloudflare (or your reverse proxy). Django is configured for that (secure cookies, no HTTP redirect).

## Optional overrides

Set these only if you need to change defaults (e.g. different domain, or local dev):

- `DJANGO_DEBUG=1` – enable debug mode (local only).
- `DJANGO_SECRET_KEY` – use this instead of the auto-generated `.secret_key` file.
- `DJANGO_ALLOWED_HOSTS` – comma-separated hosts (default already includes `home.freedomwoods.online`).
- `DJANGO_CSRF_TRUSTED_ORIGINS` – comma-separated HTTPS origins.
- `DJANGO_SECURE_SSL_REDIRECT=1` – if Django terminates TLS (not needed behind Cloudflare Tunnel).

## What’s enabled in production (when DEBUG is off)

- Auto secret key (from env or `.secret_key` file).
- Security headers: XSS filter, X-Content-Type-Options, HSTS.
- Secure session and CSRF cookies; no HTTPS redirect when behind a proxy.
- WhiteNoise serving static files with hashed names.
- Rotating file logging for errors.
