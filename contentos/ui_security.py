"""Small output-scrubbing helpers for local UI diagnostics."""
import os
import re

_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|authorization)\b(\s*[:=]\s*)(\S+)"
)
_BEARER = re.compile(r"(?i)\bBearer\s+\S+")


def redact_text(value):
    text = str(value or "")
    text = _BEARER.sub("Bearer [REDACTED]", text)
    text = _ASSIGNMENT.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", text)
    for name, secret in os.environ.items():
        if secret and len(secret) >= 8 and any(part in name.upper() for part in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
            text = text.replace(secret, "[REDACTED]")
    return text
