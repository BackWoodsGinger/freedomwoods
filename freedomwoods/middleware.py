"""
Middleware to prevent HTML pages from being cached, so users always get
fresh HTML (and thus the latest static asset URLs with ?v=STATIC_VERSION).
Static files can still be cached by the browser; only page content is no-cache.
"""


class NoCacheHtmlMiddleware:
    """Set Cache-Control so HTML responses are not cached by browser or proxy."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get("Content-Type", "")
        if "text/html" in content_type and response.status_code == 200:
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
        return response
