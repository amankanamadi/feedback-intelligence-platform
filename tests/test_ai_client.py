import httpx
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)

from app.ai.client import describe_openai_error, get_openai_client
from app.core.config import get_settings


def _status_error(cls, status_code, code=None):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    body = {"error": {"message": "boom", "code": code}}
    response = httpx.Response(status_code, request=request, json=body)
    return cls(message="boom", response=response, body=body)


def test_describe_rate_limit_error():
    exc = _status_error(RateLimitError, 429, code="rate_limit_exceeded")
    assert "rate limit" in describe_openai_error(exc)


def test_describe_timeout_error():
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    exc = APITimeoutError(request=request)
    assert "timed out" in describe_openai_error(exc)


def test_describe_connection_error():
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    exc = APIConnectionError(message="conn failed", request=request)
    assert "connection" in describe_openai_error(exc)


def test_describe_auth_error():
    exc = _status_error(AuthenticationError, 401, code="invalid_api_key")
    assert "credentials" in describe_openai_error(exc)


def test_describe_context_length_exceeded():
    exc = _status_error(BadRequestError, 400, code="context_length_exceeded")
    assert "context length" in describe_openai_error(exc)


def test_describe_generic_bad_request():
    exc = _status_error(BadRequestError, 400, code="some_other_code")
    assert "invalid request" in describe_openai_error(exc)


def test_describe_server_error():
    exc = _status_error(InternalServerError, 500, code="server_error")
    assert "server error" in describe_openai_error(exc)


def test_describe_unknown_error():
    exc = ValueError("something else")
    assert "unexpected error" in describe_openai_error(exc)


def test_get_openai_client_configures_timeout_and_retries():
    settings = get_settings()
    client = get_openai_client()

    assert client.timeout == settings.openai_timeout_seconds
    assert client.max_retries == settings.openai_max_retries
