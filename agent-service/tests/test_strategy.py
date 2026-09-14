from unittest.mock import Mock
import json
import httpx
import pytest
from app.retrieval.intent import SearchIntent, IntentParser
from app.retrieval.strategy import select_profile, weights_for, matches_metadata
from app.retrieval.rerank import rerank
from app.retrieval.keyword_executor import KeywordSearchExecutor
from app.runtime.java_client import PictureCandidate, PictureFeatures
from test_task_planner import context
from test_intent import settings


@pytest.mark.parametrize('query,profile',[
    ('查找某地区拍摄的河道图片','text'),('查找苏州市河道图片','text'),
    ('检索实验编号EXP-123的图片','text'),('找构图相似的图片','visual'),
    ('查找明暗度对比的图片','visual'),('查找苏州市构图相似的河道图','mixed')])
def test_explicit_query_strategy(query,profile):
    assert select_profile(SearchIntent(searchText='河道'),query)==profile


def test_rank_reverses_with_intent_and_reports_real_weights():
    pictures=[PictureCandidate(pictureId=i,spaceId=None,name='河道') for i in ['1','2']]
    channels={'keyword':['1','2'],'vector':['1','2'],'image':['2','1']}
    text,text_scores=rerank(pictures,channels,SearchIntent(searchText='河道',retrievalProfile='text'))
    visual,visual_scores=rerank(pictures,channels,SearchIntent(searchText='河道',retrievalProfile='visual'))
    assert text[0].pictureId=='1' and visual[0].pictureId=='2'
    assert text_scores['1']['weights']['image']==0
    assert visual_scores['2']['weights']['image']==.75


def test_text_strategy_skips_all_image_vector_calls():
    parser,semantic=Mock(),Mock()
    parser.parse.return_value=SearchIntent(searchText='苏州',retrievalProfile='text',metadataTerms=['苏州'])
    semantic.enabled=True
    semantic.search.return_value=[]
    p=PictureCandidate(pictureId='1',spaceId=None,name='苏州河道')
    result=KeywordSearchExecutor(parser,semantic).execute(context('苏州地区图片'),lambda *args:[p],lambda ids:[p],lambda:None)
    semantic.search_visual_text.assert_not_called()
    semantic.search_by_pictures.assert_not_called()
    semantic.search_by_image_data.assert_not_called()
    semantic.search.assert_called_once()
    assert result.intent_state['retrievalProfile']=='text'


def test_location_must_match_business_metadata_not_model_caption():
    intent=SearchIntent(searchText='河道',retrievalProfile='mixed',metadataTerms=['苏州'])
    wrong=PictureCandidate(pictureId='1',spaceId=None,name='杭州河道',features=PictureFeatures(caption='像苏州'))
    right=PictureCandidate(pictureId='2',spaceId=None,introduction='苏州河道巡检')
    assert not matches_metadata(wrong,intent) and matches_metadata(right,intent)
    parser,semantic=Mock(),Mock()
    parser.parse.return_value=intent
    semantic.enabled=True
    semantic.search_visual_text.return_value=['1','2']
    semantic.search.return_value=['1','2']
    result=KeywordSearchExecutor(parser,semantic).execute(context('苏州地区构图相似的河道图'),
        lambda *args:[right],lambda ids:[p for p in [wrong,right] if p.pictureId in ids],lambda:None)
    assert [c['pictureId'] for c in result.citations]==['2']


def test_model_can_classify_place_without_keyword_and_cannot_invent_weights():
    def parse(output):
        client=httpx.Client(base_url='https://dashscope.example/v1',transport=httpx.MockTransport(
            lambda req:httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(output)}}]})))
        return IntentParser(settings(),client).parse('查找苏州河道图')
    assert parse({'searchText':'河道','retrievalProfile':'text','metadataTerms':['苏州']}).retrievalProfile=='text'
    assert not parse({'searchText':'河道','retrievalProfile':'text','metadataTerms':['杭州']}).metadataTerms
    with pytest.raises(ValueError):SearchIntent(searchText='河道',retrievalProfile='execute')
    with pytest.raises(ValueError):SearchIntent(searchText='河道',weights={'image':999})


def test_followup_inherits_profile_and_supplement_does_not_reinterpret():
    intent=SearchIntent(searchText='河道',retrievalProfile='text',metadataTerms=['苏州'])
    assert select_profile(intent,'时间再近一点')=='text'
    assert select_profile(intent,'构图再相似一点')=='mixed'
    parser=Mock()
    result=KeywordSearchExecutor(parser).execute_with_state(context('构图'),lambda *args:[],lambda ids:[],
        lambda:None,None,[],frozen_intent=intent.model_dump(mode='json'))
    parser.parse.assert_not_called()
    assert result.intent_state['retrievalProfile']=='text'


def test_grouping_by_project_does_not_itself_force_text_only_search():
    assert select_profile(SearchIntent(searchText='河道'),'查找河道图片再按项目分组')=='balanced'


def test_brightness_is_still_a_hard_feature_filter():
    parser=Mock()
    parser.parse.return_value=SearchIntent(searchText='河道',brightness='dark')
    pictures=[PictureCandidate(pictureId=str(i),spaceId=None,features=PictureFeatures(brightnessScore=b))
              for i,b in [(1,10),(2,150)]]
    result=KeywordSearchExecutor(parser).execute(context('查找偏暗的河道图'),lambda *args:pictures,
        lambda ids:[p for p in pictures if p.pictureId in ids],lambda:None)
    assert [c['pictureId'] for c in result.citations]==['1']
