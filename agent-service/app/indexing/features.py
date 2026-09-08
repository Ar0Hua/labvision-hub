from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
import math

import httpx


MAX_IMAGE_BYTES = 12 * 1024 * 1024
PROMPT_VERSION = "picture-caption-v1"


@dataclass(frozen=True)
class ExtractedFeatures:
    content_hash: str
    phash: str
    dhash: str
    blur_score: float
    brightness_score: float
    quality_flags: list[str]


def download_image(client: httpx.Client, url: str) -> bytes:
    response = client.get(url, follow_redirects=False)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type not in {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}:
        raise ValueError("unsupported image content type")
    declared = int(response.headers.get("content-length", "0") or 0)
    if declared > MAX_IMAGE_BYTES or len(response.content) > MAX_IMAGE_BYTES:
        raise ValueError("image exceeds indexing size limit")
    return response.content


def extract_features(content: bytes) -> ExtractedFeatures:
    try:
        from PIL import Image, ImageStat
    except ImportError as error:
        raise RuntimeError("Pillow dependency is not installed") from error
    image = Image.open(BytesIO(content))
    image.verify()
    image = Image.open(BytesIO(content)).convert("L")
    if image.width * image.height > 80_000_000:
        raise ValueError("decoded image is too large")
    sample = image.copy()
    sample.thumbnail((256, 256))
    brightness = float(ImageStat.Stat(sample).mean[0])
    blur = _laplacian_variance(sample)
    flags = []
    if brightness < 50:
        flags.append("dark")
    elif brightness > 210:
        flags.append("overexposed")
    if blur < 45:
        flags.append("blurry")
    return ExtractedFeatures(
        content_hash=sha256(content).hexdigest(),
        phash=_perceptual_hash(image),
        dhash=_difference_hash(image),
        blur_score=round(blur, 4),
        brightness_score=round(brightness, 4),
        quality_flags=flags,
    )


def analyze_caption(client: httpx.Client, api_key: str, model: str, image_url: str) -> tuple[str, str]:
    if not api_key or not model:
        return "", ""
    response = client.post(
        "/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": (
                        "仅观察图片。返回JSON对象：caption为不超过300字的客观视觉描述，"
                        "ocrText为图片中可见文字（没有则为空字符串）。不要推断实验结论。"
                    )},
                ],
            }],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_completion_tokens": 512,
        },
    )
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"]
    parsed = json.loads(raw)
    caption = parsed.get("caption", "")
    ocr = parsed.get("ocrText", "")
    if not isinstance(caption, str) or not isinstance(ocr, str):
        raise ValueError("invalid caption response")
    return caption.strip()[:2000], ocr.strip()[:4000]


def _difference_hash(image) -> str:
    values = list(image.resize((9, 8)).getdata())
    bits = [values[row * 9 + col] > values[row * 9 + col + 1]
            for row in range(8) for col in range(8)]
    return _bits_to_hex(bits)


def _perceptual_hash(image) -> str:
    values = list(image.resize((32, 32)).getdata())
    coefficients = []
    for u in range(8):
        for v in range(8):
            total = 0.0
            for x in range(32):
                for y in range(32):
                    total += values[y * 32 + x] * math.cos((2 * x + 1) * u * math.pi / 64) \
                        * math.cos((2 * y + 1) * v * math.pi / 64)
            coefficients.append(total)
    median = sorted(coefficients[1:])[len(coefficients[1:]) // 2]
    return _bits_to_hex([value > median for value in coefficients])


def _laplacian_variance(image) -> float:
    width, height = image.size
    if width < 3 or height < 3:
        return 0.0
    pixels = image.load()
    values = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            values.append(4 * pixels[x, y] - pixels[x - 1, y] - pixels[x + 1, y]
                          - pixels[x, y - 1] - pixels[x, y + 1])
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def _bits_to_hex(bits: list[bool]) -> str:
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:016x}"
