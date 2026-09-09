import unittest
from app.analysis.quality import summarize_features
from app.runtime.java_client import PictureCandidate, PictureFeatures


class QualityTests(unittest.TestCase):
    def test_exact_and_near_duplicate_are_separate(self):
        a = PictureCandidate(pictureId="1", spaceId=None, features=PictureFeatures(
            contentHash="a"*64, phash="0"*16, dhash="0"*16, brightnessScore=20))
        b = a.model_copy(update={"pictureId": "2"})
        c = PictureCandidate(pictureId="3", spaceId=None, features=PictureFeatures(
            contentHash="b"*64, phash="0"*15+"1", dhash="0"*15+"1"))
        answer = summarize_features([a, b, c])
        self.assertIn("索引图像字节相同：[图片 ID: 1]、[图片 ID: 2]", answer)
        self.assertIn("pHash 距离 1/64", answer)
        self.assertIn("偏暗", answer)

    def test_absent_features_are_not_assumed_healthy(self):
        answer = summarize_features([PictureCandidate(pictureId="1", spaceId=None)])
        self.assertIn("覆盖 0/1", answer)
        self.assertIn("尚无", answer)
