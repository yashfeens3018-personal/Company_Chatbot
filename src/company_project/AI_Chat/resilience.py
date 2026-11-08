"""
Retry + error classification for everything that can fail at runtime:
the LLM API, the embeddings / vector store, and the database.

Usage:
    result = call_with_retry(lambda: model.invoke(prompt), step="final answer")
On failure a ServiceError is raised whose .user_message is safe to show to the user.
"""
import json
import logging
import socket
import time

import httpx
from langchain_core.exceptions import OutputParserException
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError, SQLAlchemyError

logger = logging.getLogger(__name__)

MAX_RETRIES = 5         # retries after the first attempt (4 attempts in total)
RETRY_BASE_DELAY = 1.0   # seconds; doubles each retry: 1s, 2s, 4s
MAX_RETRY_WAIT = 20.0    # never sleep longer than this; if the API asks for more, tell the user instead

# Which kinds of failure are worth retrying
LLM_RETRY_KINDS = {"rate_limit", "connection", "timeout", "server", "bad_output"}
DB_RETRY_KINDS = {"database"}


def notify_user(message: str) -> None:
    """Shown while waiting between retries. Replace this if you have a UI/websocket."""
    print(f"[assistant] {message}")


class InvalidModelOutput(ValueError):
    """The model answered, but not with usable output (empty, or missing fields)."""


class ServiceError(Exception):
    def __init__(self, kind, user_message, original, attempts=1):
        super().__init__(user_message)
        self.kind = kind
        self.user_message = user_message
        self.original = original
        self.attempts = attempts


ERROR_TEXT = {
    "rate_limit":     "The {service} is receiving too many requests right now (rate limit reached).",
    "connection":     "I couldn't connect to the {service}. This is usually a network problem.",
    "timeout":        "The {service} took too long to respond.",
    "server":         "The {service} is having problems on its side (error {status}).",
    "auth":           "The {service} rejected our credentials (error {status}). This is a configuration problem, and retrying won't help.",
    "bad_request":    "The {service} rejected the request (error {status}).",
    "bad_output":     "The {service} returned a response I couldn't understand.",
    "database":       "I couldn't connect to the database right now.",
    "database_error": "The database returned an error while processing the lookup.",
    "unknown":        "Something unexpected went wrong while contacting the {service}.",
}

# Extra advice for errors that are NOT retried
ADVICE = {
    "auth":           "Please contact an administrator.",
    "bad_request":    "Try rephrasing your question or starting a new conversation.",
    "database_error": "Please contact an administrator.",
    "unknown":        "Please try again, and contact an administrator if it keeps happening.",
}


def classify_error(exc: Exception):
    """Return (kind, http_status, retry_after_seconds)."""
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if isinstance(status, int):
        retry_after = None
        try:
            raw = response.headers.get("retry-after")
            retry_after = float(raw) if raw else None
        except (ValueError, AttributeError):
            pass
        if status == 429:
            return "rate_limit", status, retry_after
        if status in (401, 403):
            return "auth", status, None
        if status == 408 or status >= 500:
            return "server", status, retry_after
        if status >= 400:
            return "bad_request", status, None

    if isinstance(exc, (httpx.TimeoutException, TimeoutError, socket.timeout)):
        return "timeout", None, None
    if isinstance(exc, (httpx.TransportError, ConnectionError, socket.gaierror)):
        return "connection", None, None
    if isinstance(exc, (OutputParserException, ValidationError, json.JSONDecodeError, InvalidModelOutput)):
        return "bad_output", None, None
    if isinstance(exc, OperationalError):
        return "database", None, None
    if isinstance(exc, SQLAlchemyError):
        return "database_error", None, None
    return "unknown", None, None


def call_with_retry(fn, *, step, service="AI service", retry_on=LLM_RETRY_KINDS,
                    validate=None, notify=None):
    """Run fn() with retries and exponential backoff.

    step     -> short name used in logs ("intent classification")
    service  -> name shown to the user ("AI service", "database", "document search")
    retry_on -> error kinds that are retried
    validate -> optional callable(result) -> bool; a falsy result counts as bad output
    """
    notify = notify or notify_user
    attempt = 0
    while True:
        try:
            result = fn()
            if validate is not None and not validate(result):
                raise InvalidModelOutput(f"Unusable output during {step}")
            return result
        except Exception as exc:
            kind, status, retry_after = classify_error(exc)
            text = ERROR_TEXT[kind].format(service=service, status=status)
            logger.warning("%s failed (%s, attempt %d): %r", step, kind, attempt + 1, exc)

            if kind in retry_on and attempt < MAX_RETRIES:
                wait = max(RETRY_BASE_DELAY * (2 ** attempt), retry_after or 0)
                if wait <= MAX_RETRY_WAIT:
                    attempt += 1
                    notify(f"{text} Retrying in {wait:g}s (retry {attempt} of {MAX_RETRIES})...")
                    time.sleep(wait)
                    continue
                # the provider wants us to wait much longer than is reasonable here
                message = f"{text} Please try again in about {int(retry_after)} seconds."
            elif kind in retry_on:
                message = f"{text} I retried {attempt} times without success. Please try again in a minute."
            else:
                message = f"{text} {ADVICE.get(kind, '')}".strip()

            logger.error("%s gave up (%s): %r", step, kind, exc)
            raise ServiceError(kind, message, exc, attempt + 1) from exc