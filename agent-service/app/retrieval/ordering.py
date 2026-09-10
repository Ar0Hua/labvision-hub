"""Stable time ordering within the authorized retrieval pool."""
from datetime import datetime, timedelta, timezone

from app.runtime.java_client import PictureCandidate


def order_candidates(candidates: list[PictureCandidate], sort: str) -> list[PictureCandidate]:
    if sort == "relevance":
        return list(candidates)
    if sort not in {"newest", "oldest"}:
        raise ValueError("unsupported sort")

    def key(picture: PictureCandidate):
        try:
            raw = picture.createdAt
            if isinstance(raw, int):
                # Java date serialization uses Unix milliseconds.
                value = datetime.fromtimestamp(raw / 1000, timezone.utc)
            else:
                value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone(timedelta(hours=8)))
            timestamp = value.timestamp()
            return (False, -timestamp if sort == "newest" else timestamp)
        except (AttributeError, ValueError, OverflowError, OSError):
            return (True, 0)

    # Equal or unknown timestamps preserve fusion order; unknowns go last.
    return sorted(candidates, key=key)
