from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages

from .context_processors import nav_apps
from .forms import ContactForm


def index(request):
    """Homepage with project cards; uses same app list as nav dropdown."""
    return render(request, "pages/index.html", {"apps": nav_apps(request)["nav_apps"]})


def about(request):
    """Professional about / developer platform page."""
    return render(request, "pages/about.html")


def contact(request):
    """Contact form; on POST sends email to configured Gmail."""
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        name = form.cleaned_data["name"]
        email = form.cleaned_data["email"]
        subject = form.cleaned_data["subject"]
        message = form.cleaned_data["message"]
        body = f"From: {name} <{email}>\n\n{message}"
        recipient = getattr(settings, "CONTACT_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)
        if not recipient:
            messages.error(request, "Email is not configured. Please set CONTACT_EMAIL or EMAIL_HOST_USER.")
        else:
            try:
                send_mail(
                    subject=f"[Freedom Woods Contact] {subject}",
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    fail_silently=False,
                )
                messages.success(request, "Your message was sent. We'll get back to you soon.")
                form = ContactForm()
            except Exception as e:
                messages.error(request, f"Could not send message: {e}")
    return render(request, "pages/contact.html", {"form": form})