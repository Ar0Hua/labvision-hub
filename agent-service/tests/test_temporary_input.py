import json
import unittest
import httpx
from pydantic import ValidationError
from app.runtime.java_client import TemporaryInput, TaskContext
from app.retrieval.semantic import SemanticRetriever
from app.analysis.vision import VisionAnalyzer
from test_semantic import settings

ID = "01234567-1234-1234-1234-123456789012"

class TemporaryInputTests(unittest.TestCase):
    def image(self):
        return TemporaryInput(temporaryId=ID,width=10,height=20,dataUrl="data:image/jpeg;base64,YWJj")

    def test_never_serialize_image_bytes(self):
        image=self.image()
        context=TaskContext(taskId="t",conversationId="c",userId="1",spaceId=None,
                            query="分析",status="RUNNING",temporaryImageId=ID,temporaryImage=image)
        self.assertNotIn("YWJj",repr(context))
        self.assertNotIn("dataUrl",image.model_dump())
        self.assertNotIn("temporaryImage",context.model_dump())
        for url in ("https://evil.example/a", "data:image/svg+xml;base64,YWJj"):
            with self.assertRaises(ValidationError):
                TemporaryInput(temporaryId=ID,width=1,height=1,dataUrl=url)

    def test_image_query_is_read_only_scoped_and_bounded(self):
        configured=settings(); object.__setattr__(configured,"image_embedding_dimensions",3)
        embedding=httpx.Client(base_url="https://embedding.example",transport=httpx.MockTransport(
            lambda _:httpx.Response(200,json={"output":{"embeddings":[{"embedding":[.1,.2,.3]}]}})))
        captured=[]
        def handler(request):
            captured.append(request)
            return httpx.Response(200,json={"result":{"points":[{"payload":{"pictureId":"123"}}]}})
        qdrant=httpx.Client(base_url="http://qdrant",transport=httpx.MockTransport(handler))
        result=SemanticRetriever(configured,embedding,qdrant).search_by_image_data(
            self.image().dataUrl,["public","space:9"])
        self.assertEqual(result,["123"])
        self.assertTrue(all(str(r.url).endswith("/points/query") for r in captured))
        body=json.loads(captured[0].content)
        self.assertEqual(body["using"],"image_dense")
        self.assertEqual(len(body["filter"]["should"]),2)
        self.assertNotIn("YWJj",captured[0].content.decode())

    def test_temporary_analysis_rejects_permanent_citation(self):
        configured=settings(); object.__setattr__(configured,"vision_model","vision")
        client=httpx.Client(base_url="https://model.example",transport=httpx.MockTransport(
            lambda _:httpx.Response(200,json={"choices":[{"message":{"content":"pictureId=999"}}]})))
        self.assertIsNone(VisionAnalyzer(configured,client).analyze_temporary("分析",self.image()))
