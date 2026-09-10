import unittest
from app.runtime.model_usage import ModelUsageBudget, BudgetExceeded
from app.runtime.budget import TaskBudget, active_budget, reserve_model, record_usage


class ModelUsageTests(unittest.TestCase):
    def test_unknown_price_fails_closed_when_cost_cap_enabled(self):
        budget=ModelUsageBudget.configured(64000,"1","{}",8192)
        with self.assertRaises(BudgetExceeded): budget.reserve("unknown","hi",0,20)
        self.assertEqual(budget.reserved_input,0)

    def test_input_visual_preflight_and_no_zero_billing_for_missing_usage(self):
        budget=ModelUsageBudget.configured(1000,"0","{}",8192)
        with self.assertRaises(BudgetExceeded): budget.reserve("vl","hi",1,20)
        budget=ModelUsageBudget.configured(64000,"0","{}",8192)
        budget.reserve("vl","hi",1,20)
        budget.record("vl",{})
        self.assertIsNone(budget.snapshot()["reportedCost"])
        self.assertIsNone(budget.snapshot()["reportedVisualTokens"])

    def test_reported_tokens_and_configured_cost_are_separate(self):
        prices='{"vl":{"inputPerMillion":2,"outputPerMillion":4}}'
        budget=ModelUsageBudget.configured(64000,"1",prices,8192)
        budget.reserve("vl","hello",1,800)
        budget.record("vl",{"usage":{"prompt_tokens":100,"completion_tokens":20,"prompt_tokens_details":{"image_tokens":80}}})
        result=budget.snapshot()
        self.assertEqual(result["reportedInputTokens"],100)
        self.assertEqual(result["reportedVisualTokens"],80)
        self.assertEqual(result["reportedCost"],"0.00028")
        self.assertGreater(result["reservedInputTokens"],100)

    def test_actual_output_overage_stops_next_call(self):
        budget=TaskBudget(max_output_tokens=20)
        token=active_budget.set(budget)
        try:
            reserve_model("model","hi",output_tokens=20)
            with self.assertRaises(BudgetExceeded): record_usage("model",{"usage":{"prompt_tokens":1,"completion_tokens":21}})
            with self.assertRaises(BudgetExceeded): reserve_model("model","again")
        finally: active_budget.reset(token)
