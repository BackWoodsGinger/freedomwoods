# Production deployment

## Getting the latest code to the server

1. **On your dev machine** — push to GitHub:
   ```bash
   git add .
   git commit -m "Your message"
   git push origin main
   ```

2. **On the host/server** — pull and update:
   ```bash
   cd /path/to/freedomwoods   # your project directory
   git pull origin main
   source venv/bin/activate
   pip install -r requirements.txt
   python manage.py collectstatic --noinput
   sudo systemctl restart gunicorn   # or however you run gunicorn
   ```

## Zero-config option (recommended)

You don’t need to set any environment variables for the site to run. On first run the app will:

- Create a random **secret key** and save it in `.secret_key` in the project root (so restarts use the same key).
- Use **DEBUG=0**, **ALLOWED_HOSTS** including `home.freedomwoods.online`, and **SECURE_SSL_REDIRECT=0** (suitable behind Cloudflare Tunnel).

## Contact form → receive submissions at your Gmail

To have contact form submissions emailed to you on the server:

1. **Create a Gmail App Password** (Gmail blocks normal passwords for SMTP):
   - Go to [Google App Passwords](https://myaccount.google.com/apppasswords).
   - Sign in, create an App Password for “Mail”, copy the 16-character password.

2. **On the server**, in the project root (same folder as `manage.py`), create a file named `.env`:
   ```bash
   cd /path/to/freedomwoods
   nano .env
   ```
   Add these lines (use your real Gmail and the App Password you copied):
   ```
   EMAIL_HOST_USER=yourname@gmail.com
   EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
   CONTACT_EMAIL=yourname@gmail.com
   ```
   Save and exit. **Do not commit `.env`** — it is in `.gitignore`. The app loads `.env` on startup.

3. **Restart the app** so it reads the new `.env`:
   ```bash
   sudo systemctl restart gunicorn
   ```
   Or restart gunicorn however you run it.

After this, when someone submits the contact form, you’ll receive the message at `CONTACT_EMAIL` (your Gmail).

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
