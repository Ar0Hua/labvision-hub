"""Deterministic coarse RGB and indexed-brightness filters (not perceptual confidence)."""
import re


def rgb(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    cleaned = value.strip().lower().removeprefix("#").removeprefix("0x")
    if not re.fullmatch(r"[0-9a-f]{6}", cleaned):
        return None
    return tuple(int(cleaned[i:i + 2], 16) for i in (0, 2, 4))


def matches_visual(picture, intent) -> bool:
    if intent.targetColor:
        actual, target = rgb(picture.color), rgb(intent.targetColor)
        if actual is None or any(abs(a - b) > intent.colorTolerance for a, b in zip(actual, target)):
            return False
    if intent.brightness:
        score = picture.features.brightnessScore if picture.features else None
        if score is None:
            return False
        if intent.brightness == "dark" and not score < 50:
            return False
        if intent.brightness == "bright" and not score > 210:
            return False
        if intent.brightness == "normal" and not 50 <= score <= 210:
            return False
    return True


def vector_conditions(values: dict) -> list[dict]:
    result = []
    if values.get("targetColor"):
        target = rgb(values["targetColor"])
        if target is None:
            raise ValueError("invalid target color")
        tolerance = values.get("colorTolerance", 48)
        for key, channel in zip(("colorR", "colorG", "colorB"), target):
            result.append({"key": key, "range": {"gte": max(0, channel - tolerance),
                                                   "lte": min(255, channel + tolerance)}})
    brightness = values.get("brightness")
    if brightness:
        ranges = {"dark": {"lt": 50}, "bright": {"gt": 210}, "normal": {"gte": 50, "lte": 210}}
        result.append({"key": "brightnessScore", "range": ranges[brightness]})
    return result
