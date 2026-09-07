from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    java_base_url: str
    service_secret: str
    dashscope_api_key: str
    qdrant_url: str
    qdrant_collection: str

    @classmethod
    def from_env(cls) -> "Settings":
        secret = os.getenv("AGENT_SERVICE_SECRET", "")
        if len(secret) < 32:
            raise RuntimeError("AGENT_SERVICE_SECRET must contain at least 32 characters")
        return cls(
            java_base_url=os.getenv("JAVA_BASE_URL", "http://127.0.0.1:8123/api").rstrip("/"),
            service_secret=secret,
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", ""),
            qdrant_url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333").rstrip("/"),
            qdrant_collection=os.getenv("QDRANT_COLLECTION", "labvision_picture_v1"),
        )
