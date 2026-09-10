from dataclasses import dataclass
import os
from urllib.parse import urlsplit


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
    task_timeout_seconds: float = 120
    image_embedding_model: str = "multimodal-embedding-v1"
    image_embedding_dimensions: int = 1024
    image_embedding_base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    caption_model: str = "qwen-vl-plus"
    feature_version: str = "image-v1+text-v1+caption-v1"

    max_tool_calls: int = 100
    max_model_calls: int = 10
    max_output_tokens: int = 8000
    max_input_tokens: int = 262144
    max_task_cost: str = "0"
    model_prices_json: str = "{}"
    image_token_reservation: int = 8192
    max_graph_steps: int = 6

    @classmethod
    def from_env(cls) -> "Settings":
        secret = os.getenv("AGENT_INTERNAL_SECRET") or os.getenv("AGENT_SERVICE_SECRET", "")
        if len(secret) < 32:
            raise RuntimeError("AGENT_INTERNAL_SECRET must contain at least 32 characters")
        configured = cls(
            max_graph_steps=max(4, min(20, int(os.getenv("AGENT_MAX_STEPS", "6")))),
            max_input_tokens=max(1024, min(1000000, int(os.getenv("AGENT_MAX_INPUT_TOKENS", "262144")))),
            max_task_cost=os.getenv("AGENT_MAX_TASK_COST", "0"),
            model_prices_json=os.getenv("AGENT_MODEL_PRICES_JSON", "{}"),
            image_token_reservation=max(1024, min(65536, int(os.getenv("AGENT_IMAGE_TOKEN_RESERVATION", "8192")))),
            max_tool_calls=max(1, min(500, int(os.getenv("AGENT_MAX_TOOL_CALLS", "100")))),
            max_model_calls=max(1, min(30, int(os.getenv("AGENT_MAX_MODEL_CALLS", "10")))),
            max_output_tokens=max(256, min(30000, int(os.getenv("AGENT_MAX_OUTPUT_TOKENS", "8000")))),
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
            task_timeout_seconds=max(10, float(os.getenv("AGENT_TASK_TIMEOUT_SECONDS", "120"))),
            image_embedding_model=os.getenv(
                "AGENT_IMAGE_EMBEDDING_MODEL", "multimodal-embedding-v1"
            ).strip(),
            image_embedding_dimensions=int(os.getenv(
                "AGENT_IMAGE_EMBEDDING_DIMENSIONS", "1024"
            )),
            image_embedding_base_url=os.getenv(
                "DASHSCOPE_MULTIMODAL_BASE_URL", "https://dashscope.aliyuncs.com/api/v1"
            ).rstrip("/"),
            caption_model=os.getenv("AGENT_CAPTION_MODEL", "qwen-vl-plus").strip(),
            feature_version=os.getenv(
                "AGENT_FEATURE_VERSION", "image-v1+text-v1+caption-v1"
            ).strip(),
        )
        allowed = {value.strip().lower() for value in os.getenv(
            "AGENT_MODEL_ALLOWED_HOSTS", "dashscope.aliyuncs.com").split(',') if value.strip()}
        validate_model_endpoints((configured.dashscope_base_url, configured.image_embedding_base_url), allowed)
        return configured


def validate_model_endpoints(endpoints, allowed_hosts):
    """Operator-managed allowlist, never accepted from user prompts or task JSON."""
    for endpoint in endpoints:
        parsed = urlsplit(endpoint)
        if (parsed.scheme != 'https' or parsed.hostname not in allowed_hosts or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.port not in (None,443)):
            raise RuntimeError('model endpoint is not an approved HTTPS provider')
