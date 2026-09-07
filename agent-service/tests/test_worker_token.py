import base64
import hashlib
import hmac
import json
import unittest

from app.security.worker_token import issue_worker_token


class WorkerTokenTests(unittest.TestCase):
    def test_java_compatible_worker_token(self):
        secret = "0123456789abcdef0123456789abcdef"
        token = issue_worker_token(secret, now=1000, nonce="11111111-1111-1111-1111-111111111111")
        body, signature = token.split(".")
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        supplied = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        self.assertEqual(payload["purpose"], "picture-index-worker")
        self.assertEqual(payload["expiresAt"] - payload["issuedAt"], 60)
        self.assertTrue(hmac.compare_digest(
            supplied, hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
        ))


if __name__ == "__main__":
    unittest.main()
