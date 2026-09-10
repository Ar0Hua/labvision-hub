import unittest
from app.evaluation.feedback import prepare

class FeedbackExportTests(unittest.TestCase):
    def test_review_draft_does_not_leak_query_or_promote_permission_reports(self):
        report={'version':'labvision-report-v1','query':'SECRET_PROMPT',
                'citations':[{'pictureId':'1'},{'pictureId':'2'}],
                'feedback':[{'pictureId':'1','label':'relevant'},{'pictureId':'2','label':'permission_issue'}]}
        result=prepare(report)
        self.assertTrue(result['requiresHumanReview'])
        self.assertNotIn('SECRET',str(result))
        self.assertEqual(result['suggestedRelevantPictureIds'],['1'])
        self.assertNotIn('forbiddenPictureIds',result)
        report['feedback'].append({'pictureId':'999','label':'relevant'})
        with self.assertRaises(ValueError):
            prepare(report)
