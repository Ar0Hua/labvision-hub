import unittest
from pathlib import Path
from app.evaluation.p0_gate import run_cases

class P0GateTests(unittest.TestCase):
    def test_versioned_contract_golden_runs_actual_workflow(self):
        result=run_cases(Path(__file__).resolve().parents[1]/'evals'/'p0.contract-v1.json')
        self.assertEqual(result['failedCaseIds'],[])
        self.assertEqual(result['passed'],8)
        self.assertFalse(result['realModelBenchmark'])
