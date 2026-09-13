<template>
  <details class="ranking">
    <summary>查看排序依据</summary>
    <dl v-if="rows.length">
      <div v-for="row in rows" :key="row.label"><dt>{{ row.label }}</dt><dd>{{ row.text }}</dd></div>
    </dl>
    <p v-else>暂无可解释的排序信息。</p>
    <p class="hint">这些依据用于排列搜索结果，不代表相似度百分比或实验结论。</p>
  </details>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ value: string }>()
const rows = computed(() => {
  try {
    const data = JSON.parse(props.value)
    if (!data || typeof data !== 'object' || Array.isArray(data)) return []
    const result: { label: string; text: string }[] = []
    for (const [key, label] of [['image', '图像检索'], ['vector', '语义检索'], ['keyword', '关键词检索']]) {
      const rank = data.channelRanks?.[key]
      if (typeof rank === 'number' && Number.isSafeInteger(rank) && rank > 0) {
        result.push({ label, text: `在该检索渠道中排第 ${rank} 位` })
      }
    }
    if (typeof data.metadataScore === 'number' && Number.isFinite(data.metadataScore)) {
      result.push({ label: '图片资料', text: data.metadataScore > 0 ? '名称、标签等资料命中了部分查询条件' : '名称、标签等资料未命中查询条件' })
    }
    if ('qualityScore' in data) {
      result.push({ label: '画质参考', text: typeof data.qualityScore === 'number' && Number.isFinite(data.qualityScore) ? '清晰度、亮度等可用特征参与排序' : '暂无画质特征，按中性值参与排序' })
    }
    return result
  } catch { return [] }
})
</script>

<style scoped>
.ranking { margin: 14px 0; padding: 12px; border-radius: 10px; background: #edf3fa; font-size: 12px; }
summary { cursor: pointer; color: #35629b; font-weight: 500; }
summary:focus-visible { outline: 2px solid #1677ff; outline-offset: 4px; }
dl { margin: 12px 0; }
dl div { margin: 10px 0; }
dt { color: #334155; font-weight: 600; } dd { margin: 3px 0 0; color: #64748b; line-height: 1.7; }
p { margin: 10px 0 0; line-height: 1.7; color: #64748b; }
.hint { border-top: 1px solid #dbe5f1; padding-top: 10px; font-size: 11px; }
</style>
