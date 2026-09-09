import unittest
from app.analysis.vector_groups import summarize_vector_groups
from app.retrieval.semantic import PictureSimilarityMatrix


class VectorGroupsTests(unittest.TestCase):
    def test_chain_does_not_merge_dissimilar_endpoints(self):
        result = summarize_vector_groups(PictureSimilarityMatrix(
            ["1", "2", "3"], [[1, .95, .2], [.95, 1, .9], [.2, .9, 1]]))
        self.assertIn("相似组 1：[图片 ID: 1]、[图片 ID: 2]", result)
        self.assertNotIn("相似组 2", result)
        self.assertNotIn("离群候选：[图片 ID:", result)

    def test_isolation_requires_complete_evidence(self):
        matrix = PictureSimilarityMatrix(
            ["1", "2", "3"], [[1, .95, .1], [.95, 1, .2], [.1, .2, 1]])
        self.assertIn("离群候选：[图片 ID: 3]", summarize_vector_groups(matrix))
        matrix.scores[0][2] = matrix.scores[2][0] = None
        self.assertNotIn("离群候选：[图片 ID:", summarize_vector_groups(matrix))

    def test_rejects_invalid_evidence(self):
        for scores in ([[1, .9], [.8, 1]], [[1, 2], [2, 1]],
                       [[1, True], [True, 1]], [[1, float("nan")], [float("nan"), 1]]):
            with self.subTest(scores=scores), self.assertRaises(ValueError):
                summarize_vector_groups(PictureSimilarityMatrix(["1", "2"], scores))

    def test_answer_integration(self):
        from app.analysis.group_analysis import PictureGroupAnalyzer
        from app.runtime.java_client import PictureCandidate
        answer = PictureGroupAnalyzer.analyze_similarity(
            [PictureCandidate(pictureId="1", spaceId=None), PictureCandidate(pictureId="2", spaceId=None)],
            PictureSimilarityMatrix(["1", "2"], [[1, .95], [.95, 1]])).answer
        self.assertIn("组内最低相似度 0.950", answer)
