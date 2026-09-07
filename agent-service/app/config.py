from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    java_base_url: str
    service_secret: str
    java_timeout_seconds: float
    dashscope_api_key: str
    dashscope_base_url: str
    chat_model: str
    model_timeout_seconds: float
    embedding_model: str
    embedding_dimensions: int
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str
    qdrant_timeout_seconds: float
    checkpoint_redis_url: str = "redis://127.0.0.1:6379/1"
    checkpoint_ttl_minutes: int = 1440
    vision_model: str = ""
    max_vision_pictures: int = 4

    @classmethod
    def from_env(cls) -> "Settings":
        secret = os.getenv("AGENT_INTERNAL_SECRET") or os.getenv("AGENT_SERVICE_SECRET", "")
        if len(secret) < 32:
            raise RuntimeError("AGENT_INTERNAL_SECRET must contain at least 32 characters")
        return cls(
            java_base_url=os.getenv("JAVA_BASE_URL", "http://127.0.0.1:8123/api").rstrip("/"),
            service_secret=secret,
            java_timeout_seconds=float(os.getenv("JAVA_REQUEST_TIMEOUT_SECONDS", "10")),
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", ""),
            dashscope_base_url=os.getenv(
                "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ).rstrip("/"),
            chat_model=os.getenv("AGENT_CHAT_MODEL", "qwen-plus"),
            model_timeout_seconds=float(os.getenv("AGENT_MODEL_TIMEOUT_SECONDS", "20")),
            embedding_model=os.getenv("AGENT_EMBEDDING_MODEL", "text-embedding-v4"),
            embedding_dimensions=int(os.getenv("AGENT_EMBEDDING_DIMENSIONS", "1024")),
            qdrant_url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333").rstrip("/"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY", ""),
            qdrant_collection=os.getenv("QDRANT_COLLECTION", "labvision_picture_v1"),
            qdrant_timeout_seconds=float(os.getenv("QDRANT_TIMEOUT_SECONDS", "5")),
            checkpoint_redis_url=os.getenv(
                "AGENT_CHECKPOINT_REDIS_URL", "redis://127.0.0.1:6379/1"
            ),
            checkpoint_ttl_minutes=int(os.getenv("AGENT_CHECKPOINT_TTL_MINUTES", "1440")),
            vision_model=os.getenv("AGENT_VISION_MODEL", "").strip(),
            max_vision_pictures=min(8, max(1, int(os.getenv("AGENT_MAX_VISION_PICTURES", "4")))),
        )
