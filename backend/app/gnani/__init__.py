"""Wrappers around Gnani's speech services: Prisma (speech to text) and Timbre (text to speech).

Shared plumbing lives here: the error types, the language-code mapping, and the
one place that reads (never prints) the API key.
"""

from .. import config


class GnaniNotConfigured(RuntimeError):
    """Raised when a wrapper cannot run: missing settings, or a known gap.

    Mock mode always works; real mode needs a base URL and an API key in `.env`.
    """


class GnaniAPIError(GnaniNotConfigured):
    """Gnani answered, but with an error (bad audio, quota, bad key, ...)."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type


# Gnani expects regional codes ("kn-IN"); the rest of the app stores the short
# code ("kn"). Unknown codes pass through unchanged.
LANGUAGE_CODES = {"kn": "kn-IN"}

REQUEST_TIMEOUT_SECONDS = 30.0


def require_settings(service: str) -> tuple[str, str]:
    """Return (base_url, api_key) or explain what is missing. Never logs the key."""
    if not config.GNANI_BASE_URL.strip():
        raise GnaniNotConfigured(f"{service}: GNANI_BASE_URL is not set in .env")
    if not config.GNANI_API_KEY.strip():
        raise GnaniNotConfigured(f"{service}: GNANI_API_KEY is not set in .env")
    return config.GNANI_BASE_URL.strip().rstrip("/"), config.GNANI_API_KEY.strip()


def language_code(lang: str) -> str:
    return LANGUAGE_CODES.get(lang, lang)


def network_error(service: str, exc: Exception) -> GnaniAPIError:
    """Wrap a transport failure (timeout, DNS, connection reset) as one error type."""
    return GnaniAPIError(f"{service} request failed: {exc.__class__.__name__}: {exc}")


def error_from_response(response, service: str) -> GnaniAPIError:
    """Turn any documented Gnani error body into one GnaniAPIError.

    Handles all three shapes: {"success": false, "error": {...}},
    {"success": false, "message", "status_code"}, and
    {"detail": {"error_code", "message", "status_code"}}.
    """
    status = response.status_code
    error_type: str | None = None
    message = ""

    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, dict):
            error_type = detail.get("error_code") or error_type
            message = detail.get("message") or ""
            status = detail.get("status_code") or status
        error = payload.get("error")
        if isinstance(error, dict):
            error_type = error.get("type") or error_type
            message = error.get("message") or message
        if not message:
            message = payload.get("message") or ""
        status = payload.get("status_code") or status

    if not message:
        message = (response.text or "").strip()[:200] or response.reason_phrase

    label = f"HTTP {status}" + (f", {error_type}" if error_type else "")
    return GnaniAPIError(
        f"{service} error ({label}): {message}",
        status_code=status,
        error_type=error_type,
    )
