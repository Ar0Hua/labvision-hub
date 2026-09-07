import base64
import hashlib
import hmac
import json
import unittest

from app.security.service_token import InvalidServiceToken, verify_service_token


SECRET = "0123456789abcdef0123456789abcdef"


def token(payload: dict, secret: str = SECRET) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    body = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    return body + "." + base64.urlsafe_b64encode(signature).rstrip(b"=").decode()


class ServiceTokenTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "taskId": "task",
            "conversationId": "conversation",
            "userId": "2059881449783808001",
            "spaceId": "2060208764149547009",
            "issuedAt": 1000,
            "expiresAt": 1300,
        }

    def test_valid_token_preserves_string_ids(self):
        context = verify_service_token(token(self.payload), "task", SECRET, now=1100)
        self.assertEqual(context.user_id, "2059881449783808001")
        self.assertEqual(context.space_id, "2060208764149547009")

    def test_tampering_scope_and_expiry_are_rejected(self):
        value = token(self.payload)
        with self.assertRaises(InvalidServiceToken):
            verify_service_token("a" + value[1:], "task", SECRET, now=1100)
        with self.assertRaises(InvalidServiceToken):
            verify_service_token(value, "other", SECRET, now=1100)
        with self.assertRaises(InvalidServiceToken):
            verify_service_token(value, "task", SECRET, now=1301)

    def test_malformed_or_weak_secret_is_rejected(self):
        with self.assertRaises(InvalidServiceToken):
            verify_service_token("bad", "task", SECRET, now=1100)
        with self.assertRaises(RuntimeError):
            verify_service_token(token(self.payload), "task", "short", now=1100)


if __name__ == "__main__":
    unittest.main()
