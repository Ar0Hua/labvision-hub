import unittest

from app.evaluation.retrieval import GoldenCase, Prediction, evaluate


class RetrievalEvaluationTests(unittest.TestCase):
    def test_metrics_and_permission_leakage_are_deterministic(self):
        golden = [GoldenCase(queryId="q1", relevantPictureIds=["1", "2"], forbiddenPictureIds=["9"])]
        predictions = [Prediction(queryId="q1", rankedPictureIds=["1", "9", "3", "2"])]

        result = evaluate(golden, predictions)

        self.assertEqual(result["recallAt20"], 1.0)
        self.assertEqual(result["precisionAt10"], 0.2)
        self.assertEqual(result["mrr"], 1.0)
        self.assertEqual(result["unauthorizedResultCount"], 1)
        self.assertEqual(result["unauthorizedLeakageRate"], 0.25)

    def test_missing_prediction_is_counted_instead_of_ignored(self):
        result = evaluate([GoldenCase(queryId="q1", relevantPictureIds=["1"])], [])
        self.assertEqual(result["queryCount"], 1)
        self.assertEqual(result["missingPredictionCount"], 1)
        self.assertEqual(result["recallAt20"], 0.0)

    def test_duplicate_or_non_numeric_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            Prediction(queryId="q", rankedPictureIds=["1", "1"])
        with self.assertRaises(ValueError):
            GoldenCase(queryId="q", relevantPictureIds=["not-an-id"])


if __name__ == "__main__":
    unittest.main()
