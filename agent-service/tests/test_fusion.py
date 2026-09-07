import unittest

from app.retrieval.fusion import reciprocal_rank_fusion


class FusionTests(unittest.TestCase):
    def test_multi_channel_agreement_ranks_first(self):
        result = reciprocal_rank_fusion({"sql": ["a", "b"], "visual": ["b", "c"]})
        self.assertEqual(result[0].picture_id, "b")
        self.assertEqual(result[0].channel_ranks, {"sql": 2, "visual": 1})

    def test_duplicate_does_not_boost_score_or_shift_rank(self):
        self.assertEqual(
            reciprocal_rank_fusion({"sql": ["a", "a", "b"]}),
            reciprocal_rank_fusion({"sql": ["a", "b"]}),
        )

    def test_disabled_channel_returns_no_candidates(self):
        self.assertEqual(reciprocal_rank_fusion({"visual": ["a"]}, weights={"visual": 0}), [])

    def test_large_ids_remain_exact(self):
        picture_id = "2059881449783808001"
        self.assertEqual(reciprocal_rank_fusion({"sql": [picture_id]})[0].picture_id, picture_id)

    def test_invalid_limits_and_weights(self):
        for options in ({"top_k": 0}, {"top_k": 51}, {"rank_constant": 0},
                        {"weights": {"sql": float("nan")}}, {"weights": {"sql": -1}}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                reciprocal_rank_fusion({"sql": ["a"]}, **options)

    def test_empty_results(self):
        self.assertEqual(reciprocal_rank_fusion({}), [])


if __name__ == "__main__":
    unittest.main()
