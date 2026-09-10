import argparse
from urllib.parse import quote

import httpx

from app.config import Settings


class QdrantSchemaError(RuntimeError):
    pass


class QdrantSchemaManager:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.Client(
            base_url=settings.qdrant_url, timeout=settings.qdrant_timeout_seconds
        )
        self._owns_client = client is None

    def ensure(self) -> None:
        collection = quote(self._settings.qdrant_collection, safe="")
        headers = self._headers()
        current = self._client.get(f"/collections/{collection}", headers=headers)
        if current.status_code == 404:
            created = self._client.put(
                f"/collections/{collection}",
                headers=headers,
                json={
                    "vectors": {
                        "text_dense": {
                            "size": self._settings.embedding_dimensions,
                            "distance": "Cosine",
                        },
                        "image_dense": {
                            "size": self._settings.image_embedding_dimensions,
                            "distance": "Cosine",
                        },
                    }
                },
            )
            created.raise_for_status()
        else:
            current.raise_for_status()
            self._verify_existing(current.json())
        payload_indexes = {
            "scopeKey": "keyword", "pictureId": "keyword", "spaceId": "keyword",
            "userId": "keyword", "reviewStatus": "integer", "isDelete": "integer",
            "category": "keyword", "picFormat": "keyword", "createdAtEpoch": "integer",
            "sourceUpdatedAtEpoch": "integer", "contentHash": "keyword", "phash": "keyword",
            "aspectRatio": "float",
            "brightnessScore": "float", "colorR": "integer", "colorG": "integer", "colorB": "integer",
            "picWidth": "integer", "picHeight": "integer", "picSize": "integer",
        }
        for field, schema in payload_indexes.items():
            response = self._client.put(
                f"/collections/{collection}/index",
                headers=headers,
                json={"field_name": field, "field_schema": schema},
            )
            response.raise_for_status()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _verify_existing(self, body: dict) -> None:
        try:
            vectors = body["result"]["config"]["params"]["vectors"]
            text = vectors["text_dense"]
            image = vectors["image_dense"]
            text_size = int(text["size"])
            image_size = int(image["size"])
            text_distance = str(text["distance"]).lower()
            image_distance = str(image["distance"]).lower()
        except (KeyError, TypeError, ValueError) as error:
            raise QdrantSchemaError("cannot read existing Qdrant vector schema") from error
        if (text_size != self._settings.embedding_dimensions
                or image_size != self._settings.image_embedding_dimensions
                or text_distance != "cosine" or image_distance != "cosine"):
            raise QdrantSchemaError(
                "existing Qdrant collection is incompatible; use a new collection name or rebuild it"
            )

    def _headers(self) -> dict[str, str]:
        return {"api-key": self._settings.qdrant_api_key} if self._settings.qdrant_api_key else {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ensure LabVision Qdrant collection schema")
    parser.parse_args()
    settings = Settings.from_env()
    manager = QdrantSchemaManager(settings)
    try:
        manager.ensure()
    finally:
        manager.close()


if __name__ == "__main__":
    main()
