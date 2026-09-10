"""Bounded provider SSE parsing. Never publish reasoning or unchecked citations."""
import json
import re
from app.runtime.budget import record_usage


def read_observations(response, model, allowed_ids, emit, check_active):
    buffer = ""
    published = []
    total = 0
    done = False
    usage_seen = False

    def flush(text):
        if not text.strip():
            return
        ids = re.findall(r"(?:pictureId|图片\s*ID)\s*[=:：]\s*(\d+)", text, re.I)
        if (any(value not in allowed_ids for value in ids) or
                (allowed_ids and not ids) or re.search(r"https?://|/picture/|\]\(", text, re.I)):
            raise ValueError("unverified visual citation")
        check_active()
        published.append(text)
        emit(text)

    for line in response.iter_lines():
        check_active()
        if len(line) > 65536:
            raise ValueError("oversized provider event")
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            done = True
            break
        body = json.loads(data)
        if body.get("error"):
            raise ValueError("provider stream error")
        if body.get("usage") and not usage_seen:
            record_usage(model, body)
            usage_seen = True
        choices = body.get("choices") or []
        if not choices:
            continue
        text = choices[0].get("delta", {}).get("content") or ""
        if not isinstance(text, str):
            raise ValueError("invalid provider text")
        total += len(text)
        if total > 6000:
            raise ValueError("visual output too long")
        buffer += text
        while "\n\n" in buffer:
            paragraph, buffer = buffer.split("\n\n", 1)
            flush(paragraph + "\n\n")
    if not done:
        raise ValueError("incomplete provider stream")
    flush(buffer)
    return "".join(published)
