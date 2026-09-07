import httpx

from app.config import Settings
from app.runtime.java_client import VisionInput


class VisionAnalyzer:
    SYSTEM_PROMPT = (
        "你是 LabVision Hub 的实验室视觉资产分析器。只描述图片中可见的对象、布局、文字、"
        "图表类型、清晰度和图片之间的可观察差异。不得把视觉猜测写成实验事实，不得推断"
        "无法从图像或给定元数据确认的模型性能、因果关系或科研结论。低置信判断明确写可能或不确定。"
    )

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = client

    @property
    def enabled(self) -> bool:
        return bool(self._settings.dashscope_api_key and self._settings.vision_model)

    def analyze(self, query: str, pictures: list[VisionInput]) -> str | None:
        selected = pictures[: self._settings.max_vision_pictures]
        if not self.enabled or not selected:
            return None
        labels = [
            f"{index}. pictureId={item.pictureId}，名称={item.name or '未命名'}，"
            f"分类={item.category or '未分类'}"
            for index, item in enumerate(selected, start=1)
        ]
        text = (
            self.SYSTEM_PROMPT + "\n用户检索目标：" + query[:500] + "\n"
            "图片顺序与站内标识：\n" + "\n".join(labels) + "\n"
            "请给出简洁的视觉匹配依据；逐条引用 pictureId，并把已知元数据与视觉观察分开。"
        )
        content = [{"type": "text", "text": text}]
        content.extend(
            {"type": "image_url", "image_url": {"url": item.temporaryUrl}}
            for item in selected
        )
        client = self._client or httpx.Client(
            base_url=self._settings.dashscope_base_url,
            timeout=self._settings.model_timeout_seconds,
        )
        try:
            response = client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {self._settings.dashscope_api_key}"},
                json={
                    "model": self._settings.vision_model,
                    "messages": [
                        {"role": "user", "content": content},
                    ],
                    "temperature": 0.1,
                    "max_completion_tokens": 800,
                },
            )
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"]
            if not isinstance(answer, str) or not answer.strip():
                return None
            return answer.strip()[:6000]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            return None
        finally:
            if self._client is None:
                client.close()
