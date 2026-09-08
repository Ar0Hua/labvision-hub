from io import BytesIO
import unittest

import httpx
from PIL import Image

from app.indexing.features import download_image, extract_features


class ImageFeatureTests(unittest.TestCase):
    def _png(self, color: int = 20) -> bytes:
        output = BytesIO()
        Image.new("L", (16, 16), color=color).save(output, format="PNG")
        return output.getvalue()

    def test_extracts_hashes_and_explainable_quality(self):
        result = extract_features(self._png())
        self.assertEqual(len(result.content_hash), 64)
        self.assertEqual(len(result.phash), 16)
        self.assertEqual(len(result.dhash), 16)
        self.assertIn("dark", result.quality_flags)
        self.assertIn("blurry", result.quality_flags)

    def test_download_rejects_non_image_response(self):
        client = httpx.Client(transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, content=b"hello",
                                            headers={"content-type": "text/plain"})))
        with self.assertRaises(ValueError):
            download_image(client, "https://cos/file")


if __name__ == "__main__":
    unittest.main()
