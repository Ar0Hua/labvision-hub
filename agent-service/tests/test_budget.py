import unittest
from concurrent.futures import ThreadPoolExecutor
from app.runtime.budget import TaskBudget, BudgetExceeded, active_budget, reserve


class BudgetTests(unittest.TestCase):
    def test_reservations_stop_before_excess_call_and_remain_exhausted(self):
        budget = TaskBudget(max_tools=3, max_models=1, max_output_tokens=800)
        token = active_budget.set(budget)
        try:
            reserve(model=True, output_tokens=800)
            with self.assertRaises(BudgetExceeded):
                reserve(model=True, output_tokens=1)
            self.assertEqual(budget.models, 1)
            self.assertEqual(budget.output_tokens, 800)
            with self.assertRaises(BudgetExceeded):
                reserve()
        finally:
            active_budget.reset(token)

    def test_parallel_tasks_do_not_share_budget(self):
        def run(_):
            budget = TaskBudget(max_tools=1)
            token = active_budget.set(budget)
            try:
                reserve()
                return budget.tools
            finally:
                active_budget.reset(token)
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(run, range(4))), [1, 1, 1, 1])
        self.assertIsNone(active_budget.get())
