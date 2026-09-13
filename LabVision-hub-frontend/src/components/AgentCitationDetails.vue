<template>
  <div class="picture-details">
    <div v-if="metadata" class="badges"><span>{{ spaceName }}</span><span>{{ metadata.format || '未知格式' }}</span></div>
    <dl v-if="metadata">
      <div><dt>尺寸</dt><dd>{{ metadata.width || '?' }} × {{ metadata.height || '?' }}</dd></div>
      <div><dt>上传日期</dt><dd>{{ formatUploadDate(metadata.createdAt) }}</dd></div>
      <div><dt>上传人</dt><dd>{{ uploaderName }}</dd></div>
      <div><dt>标签</dt><dd>{{ metadata.tags || '暂无标签' }}</dd></div>
    </dl>
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
const spaceName = ref('空间名称加载中…')
async function loadSpaceName(spaceId?: string) {
  if (!spaceId) {
    spaceName.value = '公共图库'
    return
  }
  try {
    // 仅在图片元数据通过当前会话权限校验后读取空间名称，保留 bigint 字符串。
    const response = await request('/api/space/get/vo', { params: { id: spaceId } })
    if (!alive) return
    spaceName.value = response.data.code === 0
      ? response.data.data?.spaceName?.trim() || '未命名空间'
      : '空间名称暂不可用'
  } catch {
    if (alive) spaceName.value = '空间名称暂不可用'
  }
}
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
    void loadSpaceName(metadata.value?.spaceId)
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
.badges { display: flex; flex-wrap: wrap; gap: 6px; }
.badges span { background: #eaf2ff; color: #426a9d; padding: 3px 8px; border-radius: 6px; font-size: 11px; max-width: 100%; overflow-wrap: anywhere; }
dl { margin: 12px 0; font-size: 12px; line-height: 1.7; }
dl div { display: grid; grid-template-columns: 62px minmax(0, 1fr); gap: 8px; margin: 6px 0; }
dt { color: #8190a3; } dd { margin: 0; color: #43536a; overflow-wrap: anywhere; }
small { display: block; color: #b45309; margin: 8px 0; }
img { display: block; width: 100%; max-height: 220px; object-fit: contain; margin: 12px 0; border-radius: 10px; background: #f1f5f9; }
button { width: 100%; border: 1px solid #cfe0f7; border-radius: 8px; background: #f5f9ff; color: #2467bf; cursor: pointer; padding: 8px; }
button:hover { background: #eaf2ff; } button:disabled { opacity: .6; cursor: wait; }
</style>
