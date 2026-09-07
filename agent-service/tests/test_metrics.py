import unittest

from app.observability.metrics import RuntimeMetrics


class RuntimeMetricsTests(unittest.TestCase):
    def test_prometheus_output_has_only_bounded_labels_and_aggregates(self):
        metrics = RuntimeMetrics()
        metrics.observe_task("succeeded", 1.25, True)
        metrics.observe_task("unexpected-user-content", -3, False)
        output = metrics.render()

        self.assertIn('labvision_agent_tasks_total{outcome="succeeded"} 1', output)
        self.assertIn('labvision_agent_tasks_total{outcome="failed"} 1', output)
        self.assertIn("labvision_agent_task_duration_seconds_sum 1.250000", output)
        self.assertIn("labvision_agent_empty_results_total 1", output)
        self.assertNotIn("unexpected-user-content", output)


if __name__ == "__main__":
    unittest.main()
