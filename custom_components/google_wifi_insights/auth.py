"""Normalize user-entered Google credentials without inspecting or logging secrets."""

import re
from urllib.parse import unquote

COOKIE_PREFIX = "oauth2_4/"
MASTER_PREFIXES = ("aas_et/", "oauth2rt_1/")


class CredentialInputError(ValueError):
    """A fixed translation key, never the submitted credential."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def normalize_email(value):
    """Keep account identity stable and reject obvious copy/paste mistakes."""
    email = value.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise CredentialInputError("invalid_email")
    return email


def normalize_google_token(value, method):
    """Accept copied quotes, a cookie assignment and one URL-encoding layer."""
    token = value.strip()
    if len(token) > 16384:
        raise CredentialInputError("invalid_token")
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        token = token[1:-1].strip()
    if token.startswith("oauth_token="):
        token = token.removeprefix("oauth_token=").strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        token = token[1:-1].strip()
    token = unquote(token)
    if re.fullmatch(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token):
        raise CredentialInputError("wrong_service_token")
    if not token or any(not 33 <= ord(char) <= 126 or char in "\"';\\" for char in token):
        raise CredentialInputError("invalid_token")
    prefixes = (COOKIE_PREFIX,) if method == "cookie" else MASTER_PREFIXES
    other = MASTER_PREFIXES if method == "cookie" else (COOKIE_PREFIX,)
    if token.startswith(other):
        raise CredentialInputError("wrong_token_type")
    if not any(token.startswith(prefix) and len(token) > len(prefix) for prefix in prefixes):
        raise CredentialInputError("invalid_token")
    return token
