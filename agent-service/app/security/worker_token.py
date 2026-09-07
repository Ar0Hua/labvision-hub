import base64
import hashlib
import hmac
import json
import time
import uuid


def issue_worker_token(secret: str, *, now: int | None = None, nonce: str | None = None) -> str:
    if len(secret) < 32:
        raise RuntimeError("service secret is not configured")
    issued_at = int(time.time()) if now is None else now
    payload = {
        "purpose": "picture-index-worker",
        "nonce": nonce or str(uuid.uuid4()),
        "issuedAt": issued_at,
        "expiresAt": issued_at + 60,
    }
    body = _encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    return body + "." + _encode(signature)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()
