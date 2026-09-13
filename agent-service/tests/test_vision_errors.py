import unittest
import httpx
from app.analysis.vision import check_vision_response, VisionServiceError


class VisionErrorTests(unittest.TestCase):
    def test_download_failure_is_classified_without_exposing_signed_url(self):
        response = httpx.Response(400, json={'error': {
            'code': 'invalid_parameter_error',
            'message': 'Failed to download multimodal content https://private.example/image?secret=hidden',
        }})
        with self.assertLogs('labvision.trace', level='WARNING') as logs:
            with self.assertRaises(VisionServiceError) as failure:
                check_vision_response(response)
        self.assertEqual(failure.exception.code, 'VISION_IMAGE_UNAVAILABLE')
        self.assertNotIn('private.example', str(failure.exception) + str(logs.output))
        self.assertNotIn('hidden', str(logs.output))

    def test_auth_limit_and_invalid_error_body(self):
        for status, body, expected in [
            (401, b'{}', 'VISION_AUTH_FAILED'),
            (429, b'{}', 'VISION_RATE_LIMITED'),
            (500, b'not json', 'VISION_PROVIDER_ERROR'),
            (400, b'{"error":null}', 'VISION_PROVIDER_ERROR'),
        ]:
            with self.subTest(status=status, body=body):
                with self.assertRaises(VisionServiceError) as failure:
                    check_vision_response(httpx.Response(status, content=body))
                self.assertEqual(failure.exception.code, expected)

    def test_success_does_not_consume_stream(self):
        class Stream(httpx.SyncByteStream):
            def __iter__(self):
                raise AssertionError('success stream must remain unread')
        check_vision_response(httpx.Response(200, stream=Stream()))
