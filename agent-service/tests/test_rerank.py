import unittest
from app.retrieval.rerank import rerank, score_json
from app.retrieval.intent import SearchIntent
from app.runtime.java_client import PictureCandidate, PictureFeatures


class RerankTests(unittest.TestCase):
    def test_combines_channels_and_exposes_versioned_evidence(self):
        values=[PictureCandidate(pictureId=str(i),spaceId="9",name="cell") for i in (1,2)]
        ordered,scores=rerank(values,{"keyword":["1","2"],"image":["2"]},SearchIntent(searchText="cell"))
        self.assertEqual(ordered[0].pictureId,"2")
        self.assertEqual(scores["2"]["channelRanks"],{"keyword":2,"image":1})
        self.assertIsNone(scores["1"]["qualityScore"])
        self.assertIn("not cosine",score_json(scores["1"]))

    def test_dark_intent_does_not_penalize_requested_darkness(self):
        values=[PictureCandidate(pictureId=str(i),spaceId="9",features=PictureFeatures(brightnessScore=b))
                for i,b in ((1,10),(2,100))]
        _,scores=rerank(values,{},SearchIntent(searchText="图",brightness="dark"))
        self.assertEqual(scores["1"]["rerankScore"],scores["2"]["rerankScore"])
        self.assertIsNone(scores["1"]["qualityScore"])

    def test_only_authorized_candidates_produce_scores(self):
        values=[PictureCandidate(pictureId="1",spaceId="9")]
        _,scores=rerank(values,{"image":["99","1"]},SearchIntent(searchText="图"))
        self.assertEqual(set(scores),{"1"})
