"""Wrappers around Gnani's speech services: Prisma (speech to text) and Timbre (text to speech)."""


class GnaniNotConfigured(RuntimeError):
    """Raised when a wrapper is called in real mode before its API shape is known.

    Mock mode always works; real mode waits for the human to paste the Gnani docs.
    """
