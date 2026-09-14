"""Versioned initial policy weights; not learned weights or relevance probabilities."""
import re

VERSION = 'intent-weight-policy-v1'
POLICIES = {
    'balanced': {'image':.45,'vector':.25,'keyword':.15,'metadata':.10,'quality':.05},
    'text': {'image':0.,'vector':.25,'keyword':.50,'metadata':.20,'quality':.05},
    'visual': {'image':.75,'vector':.10,'keyword':.05,'metadata':.05,'quality':.05},
    'mixed': {'image':.50,'vector':.15,'keyword':.20,'metadata':.10,'quality':.05},
}
REASONS = {'text':'地点、项目或编号以文本元数据为依据，不使用视觉相似推断地点',
           'visual':'构图、视角或示例相似主要依据图像向量，明暗仍使用亮度特征过滤',
           'mixed':'保留文本条件，同时提高视觉相似的排序权重',
           'balanced':'通用主题查询，综合文本与视觉证据'}


def infer_profile(query, has_image=False):
    visual = has_image or any(w in query for w in ('构图','视角','明暗','偏暗','偏亮','过曝','逆光','俯拍','光照','图搜图','相似图片','相似图','画面布局'))
    textual = any(w in query for w in ('地区','地点','拍摄于','拍摄地','项目名称','项目名','项目中','项目下','项目的','文件名','编号','实验号','名称包含','简介包含'))
    textual = textual or bool(re.search(r'[\u4e00-\u9fff]{2,}(?:省|市|县|区)|[A-Za-z]+[-_]\d+',query))
    if textual and visual:return 'mixed'
    if textual:return 'text'
    if visual:return 'visual'
    return None


def select_profile(intent, query='', has_image=False):
    explicit = infer_profile(query, has_image)
    if explicit:
        # Metadata-constrained queries with an example retain both signals.
        if explicit == 'visual' and (intent.metadataTerms or intent.retrievalProfile in ('text','mixed')):
            return 'mixed'
        return explicit
    if intent.retrievalProfile != 'auto':return intent.retrievalProfile
    return infer_profile(intent.searchText, has_image) or 'balanced'


def weights_for(intent):
    return dict(POLICIES[select_profile(intent)])


def matches_metadata(picture, intent):
    # Human-authored business fields only; never caption/OCR/model-inferred location.
    text = ' '.join(value or '' for value in (picture.name,picture.introduction,picture.category,picture.tags)).casefold()
    return all(term.casefold() in text for term in intent.metadataTerms)
