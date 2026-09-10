from collections import Counter
from threading import Lock


class RuntimeMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._outcomes: Counter[str] = Counter()
        self._duration_sum = 0.0
        self._duration_count = 0
        self._empty_results = 0
        self._operations = {}
        self._buckets = (.1, .5, 1, 3, 5, 10, 30, 60, 120, 300)

    def observe_operation(self, operation: str, duration: float, failed: bool = False):
        if operation not in {'agent.dispatch','agent.task','java.callback','model.intent','model.vision_stream',
                             'model.vision_reduce','retrieval.text_dense','retrieval.image_example',
                             'retrieval.multimodal','retrieval.image_matrix','agent.first_answer'}:
            operation = 'other'
        with self._lock:
            record = self._operations.setdefault(operation, {'count':0,'sum':0.,'errors':0,'buckets':[0]*len(self._buckets)})
            record['count'] += 1; record['sum'] += max(0.,duration); record['errors'] += int(failed)
            for i,bound in enumerate(self._buckets):
                if duration <= bound:
                    record['buckets'][i] += 1

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
            lines.extend(['# TYPE labvision_agent_operation_seconds histogram',
                          '# TYPE labvision_agent_operation_errors_total counter'])
            for name,record in sorted(self._operations.items()):
                for bound,count in zip(self._buckets,record['buckets']):
                    lines.append(f'labvision_agent_operation_seconds_bucket{{operation="{name}",le="{bound}"}} {count}')
                lines.append(f'labvision_agent_operation_seconds_bucket{{operation="{name}",le="+Inf"}} {record["count"]}')
                lines.append(f'labvision_agent_operation_seconds_count{{operation="{name}"}} {record["count"]}')
                lines.append(f'labvision_agent_operation_seconds_sum{{operation="{name}"}} {record["sum"]:.6f}')
                lines.append(f'labvision_agent_operation_errors_total{{operation="{name}"}} {record["errors"]}')
            return "\n".join(lines) + "\n"


runtime_metrics = RuntimeMetrics()
