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
                        "size": self._settings.embedding_dimensions,
                        "distance": "Cosine",
                    }
                },
            )
            created.raise_for_status()
        else:
            current.raise_for_status()
            self._verify_existing(current.json())
        for field in ("scopeKey", "pictureId"):
            response = self._client.put(
                f"/collections/{collection}/index",
                headers=headers,
                json={"field_name": field, "field_schema": "keyword"},
            )
            response.raise_for_status()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _verify_existing(self, body: dict) -> None:
        try:
            vectors = body["result"]["config"]["params"]["vectors"]
            size = int(vectors["size"])
            distance = str(vectors["distance"]).lower()
        except (KeyError, TypeError, ValueError) as error:
            raise QdrantSchemaError("cannot read existing Qdrant vector schema") from error
        if size != self._settings.embedding_dimensions or distance != "cosine":
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
