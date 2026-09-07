"""Reciprocal rank fusion of already-authorized retrieval channels.

Authorization MUST be applied by each recall provider before producing ranks.
This function is not an authorization filter. Scores are ranking signals, not
probabilities or scientific confidence values.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Sequence


@dataclass(frozen=True)
class FusedCandidate:
    picture_id: str
    score: float
    channel_ranks: Mapping[str, int]


def reciprocal_rank_fusion(
    channels: Mapping[str, Sequence[str]],
    *,
    top_k: int = 20,
    rank_constant: int = 60,
    weights: Mapping[str, float] | None = None,
) -> list[FusedCandidate]:
    """Fuse channels, preserving IDs as strings to avoid browser precision loss."""
    if not 1 <= top_k <= 50:
        raise ValueError("top_k must be between 1 and 50")
    if rank_constant < 1:
        raise ValueError("rank_constant must be positive")
    if weights is not None and set(weights) - set(channels):
        raise ValueError("unknown channel weight")
    scores: dict[str, float] = {}
    ranks: dict[str, dict[str, int]] = {}
    for channel, picture_ids in channels.items():
        weight = (weights or {}).get(channel, 1.0)
        if not isfinite(weight) or weight < 0:
            raise ValueError("weights must be finite and nonnegative")
        if weight == 0:
            continue
        seen: set[str] = set()
        for picture_id in picture_ids:
            if not isinstance(picture_id, str) or not picture_id:
                raise ValueError("picture IDs must be nonempty strings")
            if picture_id in seen:
                continue
            seen.add(picture_id)
            rank = len(seen)
            scores[picture_id] = scores.get(picture_id, 0.0) + weight / (rank_constant + rank)
            ranks.setdefault(picture_id, {})[channel] = rank
    ordered = sorted(scores, key=lambda picture_id: (-scores[picture_id], picture_id))
    return [FusedCandidate(pid, scores[pid], ranks[pid]) for pid in ordered[:top_k]]
