from dataclasses import dataclass
import base64
import hashlib
import hmac
import json
import time


class InvalidServiceToken(ValueError):
    pass


@dataclass(frozen=True)
class ServiceContext:
    task_id: str
    conversation_id: str
    user_id: str
    space_id: str | None
    issued_at: int
    expires_at: int


def verify_service_token(
    token: str, expected_task_id: str, secret: str, *, now: int | None = None
) -> ServiceContext:
    if len(secret) < 32:
        raise RuntimeError("service secret is not configured")
    try:
        payload_part, signature_part = token.split(".")
        expected = hmac.new(secret.encode(), payload_part.encode(), hashlib.sha256).digest()
        supplied = _decode(signature_part)
        if not hmac.compare_digest(expected, supplied):
            raise InvalidServiceToken("signature mismatch")
        payload = json.loads(_decode(payload_part))
        current = int(time.time()) if now is None else now
        issued_at = int(payload["issuedAt"])
        expires_at = int(payload["expiresAt"])
        if (
            payload["taskId"] != expected_task_id
            or expires_at < current
            or issued_at > current + 30
            or expires_at - issued_at != 300
        ):
            raise InvalidServiceToken("token scope or lifetime is invalid")
        return ServiceContext(
            task_id=str(payload["taskId"]),
            conversation_id=str(payload["conversationId"]),
            user_id=str(payload["userId"]),
            space_id=None if payload.get("spaceId") is None else str(payload["spaceId"]),
            issued_at=issued_at,
            expires_at=expires_at,
        )
    except InvalidServiceToken:
        raise
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise InvalidServiceToken("malformed token") from error


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
