import unittest
import httpx
import json
from app.retrieval.semantic import SemanticRetriever
from test_semantic import settings

class VisualTextTests(unittest.TestCase):
    def test_text_queries_image_dense_using_index_model(self):
        configured=settings(); object.__setattr__(configured,'image_embedding_dimensions',3)
        embeddings=[]; queries=[]
        def embed(request):
            embeddings.append(json.loads(request.content))
            return httpx.Response(200,json={'output':{'embeddings':[{'embedding':[.1,.2,.3]}]}})
        def query(request):
            queries.append(json.loads(request.content))
            return httpx.Response(200,json={'result':{'points':[]}})
        retriever=SemanticRetriever(configured,
            httpx.Client(base_url='https://embedding.example',transport=httpx.MockTransport(embed)),
            httpx.Client(base_url='http://qdrant',transport=httpx.MockTransport(query)))
        retriever.search_visual_text('显微镜细胞','space:9')
        self.assertEqual(embeddings[0]['model'],configured.image_embedding_model)
        self.assertEqual(embeddings[0]['input']['contents'],[{'text':'显微镜细胞'}])
        self.assertEqual(queries[0]['using'],'image_dense')
        self.assertEqual(queries[0]['filter']['must'][0]['match']['value'],'space:9')
