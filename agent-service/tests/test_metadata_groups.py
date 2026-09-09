import unittest
from app.analysis.group_analysis import PictureGroupAnalyzer
from app.runtime.java_client import PictureCandidate


class MetadataGroupsTests(unittest.TestCase):
    def test_groups_use_actual_uploader_tags_and_local_date(self):
        values = [
            PictureCandidate(pictureId="1", spaceId=None, uploaderId="9", tags='["标注"]',
                             createdAt="2026-09-08T17:00:00Z"),
            PictureCandidate(pictureId="2", spaceId=None, uploaderId="9", tags='["标注"]'),
        ]
        answer = PictureGroupAnalyzer.analyze(values).answer
        self.assertIn("上传人 ID / 9：[图片 ID: 1]、[图片 ID: 2]", answer)
        self.assertIn("上传日期（UTC+8） / 2026-09-09", answer)
        self.assertIn("标签 / 标注", answer)
