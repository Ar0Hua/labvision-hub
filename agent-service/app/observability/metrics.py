from collections import Counter
from threading import Lock


class RuntimeMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._outcomes: Counter[str] = Counter()
        self._duration_sum = 0.0
        self._duration_count = 0
        self._empty_results = 0

    def observe_task(self, outcome: str, duration_seconds: float, empty_result: bool) -> None:
        safe_outcome = outcome if outcome in {
            "succeeded", "failed", "cancelled", "timeout", "unavailable", "ignored"
        } else "failed"
        with self._lock:
            self._outcomes[safe_outcome] += 1
            self._duration_sum += max(0.0, duration_seconds)
            self._duration_count += 1
            if empty_result:
                self._empty_results += 1

    def render(self) -> str:
        with self._lock:
            lines = [
                "# HELP labvision_agent_tasks_total Agent task runs by terminal outcome.",
                "# TYPE labvision_agent_tasks_total counter",
            ]
            for outcome in sorted(self._outcomes):
                lines.append(f'labvision_agent_tasks_total{{outcome="{outcome}"}} {self._outcomes[outcome]}')
            lines.extend([
                "# HELP labvision_agent_task_duration_seconds_sum Total Agent task wall time.",
                "# TYPE labvision_agent_task_duration_seconds_sum counter",
                f"labvision_agent_task_duration_seconds_sum {self._duration_sum:.6f}",
                "# HELP labvision_agent_task_duration_seconds_count Observed Agent task runs.",
                "# TYPE labvision_agent_task_duration_seconds_count counter",
                f"labvision_agent_task_duration_seconds_count {self._duration_count}",
                "# HELP labvision_agent_empty_results_total Successful retrievals with no candidates.",
                "# TYPE labvision_agent_empty_results_total counter",
                f"labvision_agent_empty_results_total {self._empty_results}",
            ])
            return "\n".join(lines) + "\n"


runtime_metrics = RuntimeMetrics()
