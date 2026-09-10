import unittest
from pydantic import ValidationError
from app.retrieval.intent import SearchIntent, IntentParser
from app.retrieval.visual_filters import rgb, matches_visual, vector_conditions
from app.runtime.java_client import PictureCandidate, PictureFeatures


class VisualFilterTests(unittest.TestCase):
    def test_strict_schema_and_memory(self):
        for values in ({"targetColor": "red"}, {"targetColor": "#ff0000;DROP"},
                       {"colorTolerance": -1}, {"colorTolerance": 256}, {"brightness": "unknown"}):
            with self.assertRaises(ValidationError):
                SearchIntent(searchText="图", **values)
        previous=SearchIntent(searchText="图", targetColor="#ff0000", brightness="dark").model_dump(mode="json")
        self.assertEqual(IntentParser._fallback("更高清", previous).brightness, "dark")
        self.assertIsNone(IntentParser._fallback("重置", previous).brightness)

    def test_color_normalization_and_channel_box(self):
        self.assertEqual(rgb("0xFF0080"), (255,0,128))
        self.assertIsNone(rgb("red"))
        intent=SearchIntent(searchText="图", targetColor="#ff0000", colorTolerance=10)
        self.assertTrue(matches_visual(PictureCandidate(pictureId="1", spaceId="9",color="0xf5080a"),intent))
        self.assertFalse(matches_visual(PictureCandidate(pictureId="1", spaceId="9",color="0xf4080a"),intent))
        self.assertFalse(matches_visual(PictureCandidate(pictureId="1", spaceId="9"),intent))
        conditions=vector_conditions(intent.model_dump())
        self.assertIn({"key":"colorR","range":{"gte":245,"lte":255}},conditions)

    def test_brightness_boundaries_and_unknown(self):
        for value, category in ((49.9,"dark"),(50,"normal"),(210,"normal"),(210.1,"bright")):
            picture=PictureCandidate(pictureId="1",spaceId="9",features=PictureFeatures(brightnessScore=value))
            for option in ("dark","normal","bright"):
                self.assertEqual(matches_visual(picture,SearchIntent(searchText="图",brightness=option)),category==option)
        self.assertFalse(matches_visual(PictureCandidate(pictureId="1",spaceId="9"),SearchIntent(searchText="图",brightness="dark")))
        self.assertEqual(vector_conditions({"brightness":"dark"}),[{"key":"brightnessScore","range":{"lt":50}}])
