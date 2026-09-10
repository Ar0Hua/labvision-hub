"""P0 deterministic reranking; channel rank signals are NOT cosine similarities."""
import json
import re

from app.runtime.java_client import PictureCandidate
from app.retrieval.intent import SearchIntent


VERSION = "rank-metadata-quality-v1"


def rerank(candidates: list[PictureCandidate], channels: dict[str, list[str]], intent: SearchIntent):
    ranks = {name: {pid: i + 1 for i, pid in enumerate(dict.fromkeys(ids))}
             for name, ids in channels.items()}
    weights = {"image": .45, "vector": .25, "keyword": .15, "metadata": .10, "quality": .05}
    active = {key: value for key, value in weights.items() if key in {"metadata", "quality"} or ranks.get(key)}
    denominator = sum(active.values())
    breakdown = {}
    tokens = list(dict.fromkeys(re.findall(r"[\w-]+", intent.searchText.casefold())))[:20]
    for picture in candidates:
        pid = picture.pictureId
        signals = {key: (1 / ranks[key][pid] if pid in ranks.get(key, {}) else 0)
                   for key in ("image", "vector", "keyword")}
        text = " ".join(value or "" for value in (picture.name, picture.introduction, picture.category, picture.tags)).casefold()
        checks = [token in text for token in tokens]
        if intent.category:
            checks.append(picture.category == intent.category)
        signals["metadata"] = sum(checks) / len(checks) if checks else 0
        feature = picture.features
        quality = []
        if feature and feature.blurScore is not None:
            quality.append(min(1., feature.blurScore / 45))
        # Deliberately requested dark/bright images must not be penalized for that property.
        if feature and feature.brightnessScore is not None and not intent.brightness:
            quality.append(float(50 <= feature.brightnessScore <= 210))
        signals["quality"] = sum(quality) / len(quality) if quality else .5
        score = sum(signals[key] * weight for key, weight in active.items()) / denominator
        breakdown[pid] = {
            "version": VERSION, "basis": "reciprocal-channel-rank; not cosine or probability",
            "visualScore": signals["image"], "textScore": signals["vector"],
            "keywordScore": signals["keyword"], "metadataScore": signals["metadata"],
            "qualityScore": signals["quality"] if quality else None,
            "qualityMissingDefault": .5 if not quality else None,
            "rerankScore": score, "weights": active,
            "channelRanks": {key: values[pid] for key, values in ranks.items() if pid in values},
        }
    # Stable ties preserve RRF rank. Missing quality is explicitly neutral, never invented.
    return sorted(candidates, key=lambda p: -breakdown[p.pictureId]["rerankScore"]), breakdown


def score_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
