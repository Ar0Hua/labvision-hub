<template>
  <div>
    <small v-if="metadata">{{ metadata.spaceId ? `空间 ${metadata.spaceId}` : '公共图库' }} · {{ metadata.width || '?' }} × {{ metadata.height || '?' }}</small>
    <small v-if="metadata">标签：{{ metadata.tags || '无' }} · 上传时间：{{ formatUploadDate(metadata.createdAt) }}</small>
    <small v-if="metadata">上传人：{{ uploaderName }} · {{ metadata.format || '未知格式' }}</small>
    <button type="button" :disabled="loading" @click="loadPreview">{{ loading ? '加载中…' : '查看 / 刷新缩略图' }}</button>
    <img v-if="preview" :src="preview" alt="已授权图片的短期缩略图" referrerpolicy="no-referrer" @error="preview = ''" />
    <small v-if="error">{{ error }}</small>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import request from '@/request'
const props = defineProps<{ conversationId: string; pictureId: string }>()
const metadata = ref<{ spaceId?: string; width?: number; height?: number; tags?: string; createdAt?: string; uploaderId?: string; format?: string }>()
const preview = ref('')
const error = ref('')
const loading = ref(false)
const uploaderName = ref('加载中…')
function formatUploadDate(value?: string) {
  if (!value) return '未知'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未知'
  return date.toLocaleDateString('zh-CN', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
  }).replaceAll('/', '-')
}
let expiration: ReturnType<typeof setTimeout> | undefined
let alive = true
onBeforeUnmount(() => { alive = false; clearTimeout(expiration) })
onMounted(async () => {
  try {
    const response = await request(`/api/agent/conversations/${props.conversationId}/pictures/details`,
      { method: 'POST', data: [props.pictureId] })
    if (response.data.code !== 0) throw new Error('图片已不可访问')
    if (!alive) return
    metadata.value = response.data.data?.[0]
    uploaderName.value = '未知用户'
    const uploaderId = metadata.value?.uploaderId
    if (uploaderId) {
      try {
        // 保持 bigint ID 为字符串，避免 JavaScript 数值精度丢失。
        const profile = await request('/api/user/get/vo', { params: { id: uploaderId } })
        if (alive && profile.data.code === 0) {
          uploaderName.value = profile.data.data?.userName?.trim() || '未命名用户'
        }
      } catch { /* 用户资料不可用时保留图片元数据，不回退展示用户 ID。 */ }
    }
  } catch { if (alive) error.value = '当前无法读取图片元数据' }
})
async function loadPreview() {
  loading.value = true; error.value = ''; preview.value = ''; clearTimeout(expiration)
  try {
    const response = await request(`/api/agent/conversations/${props.conversationId}/pictures/previews`,
      { method: 'POST', data: [props.pictureId] })
    if (response.data.code !== 0) throw new Error('图片不可访问')
    const item = response.data.data?.[0]
    const url = new URL(item?.temporaryUrl)
    if (url.protocol !== 'https:' || url.username || url.password) throw new Error('无效预览地址')
    if (!alive) return
    preview.value = url.href
    expiration = setTimeout(() => { preview.value = '' }, Math.min(120, item.expiresInSeconds || 120) * 1000)
  } catch { if (alive) error.value = '预览不可用或权限已变化，请刷新后重试' }
  finally { if (alive) loading.value = false }
}
</script>

<style scoped>
small { display: block; overflow-wrap: anywhere; margin: 4px 0; }
img { display: block; max-width: 100%; max-height: 160px; object-fit: contain; margin: 8px 0; }
button { background: none; border: 0; color: #1677ff; cursor: pointer; padding: 4px 0; }
</style>
