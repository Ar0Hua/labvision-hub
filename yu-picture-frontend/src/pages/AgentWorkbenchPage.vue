<template>
  <div class="agent-workbench">
    <aside class="conversation-panel">
      <div class="panel-title">
        <div><strong>视觉资产 Agent</strong><small>{{ scopeLabel }}</small></div>
        <a-button type="primary" size="small" @click="createConversation">新会话</a-button>
      </div>
      <div style="display: flex; gap: 12px; margin: 8px 0">
        <a href="/agent?scope=all">全部授权空间</a><a href="/agent">仅公共图库</a>
      </div>
      <a-spin :spinning="loadingConversations">
        <button v-for="item in conversations" :key="item.conversationId" class="conversation-item"
          :class="{ active: item.conversationId === activeConversationId }"
          @click="selectConversation(item.conversationId)">
          <span>{{ item.allSpaces ? '全部授权空间快照' : item.spaceId ? `空间 ${item.spaceId}` : '公共图库' }}</span>
          <small>{{ shortId(item.conversationId) }} · {{ formatTime(item.updateTime) }}</small>
        </button>
        <a-empty v-if="!loadingConversations && !conversations.length" description="暂无会话" />
      </a-spin>
    </aside>

    <main class="chat-panel">
      <header class="chat-header">
        <div><h2>LabVision Hub 检索与分析</h2><p>回答只基于当前账号有权访问的站内视觉资产，视觉观察不等同于实验结论。</p></div>
        <a-tag :color="activeTask ? statusColor(activeTask.status) : 'default'">
          {{ activeTask ? statusText(activeTask.status) : '就绪' }}
        </a-tag>
      </header>

      <section ref="messageContainer" class="messages">
        <a-spin :spinning="loadingHistory">
          <article v-for="turn in turns" :key="turn.task.taskId" class="turn">
            <div class="user-message">{{ turn.query }}</div>
            <div class="agent-message">
              <div class="stage-line"><span class="stage-dot" />{{ stageText(turn.task.stage) }}
                <span v-if="turn.tools.length"> · 已使用 {{ turn.tools.join('、') }}</span>
              </div>
              <AgentAnswer v-if="turn.answer" :text="turn.answer" />
              <a-alert v-if="turn.task.status === 'FAILED'" type="error"
                :message="turn.task.errorMessage || '任务执行失败'" show-icon />
              <div v-else-if="!turn.answer" class="waiting">正在检索和核验证据…</div>
              <div v-if="turn.citations.length" class="citations">
                <div v-for="citation in turn.citations" :key="citation.pictureId" class="citation-card">
                <router-link :to="`/picture/${citation.pictureId}`" class="citation-card">
                  <span>{{ citation.name || '未命名图片' }}</span>
                  <small>ID {{ citation.pictureId }}{{ citation.category ? ` · ${citation.category}` : '' }}</small>
                  <small v-if="citation.matchLevel">{{ citation.matchLevel }}匹配（排序信号）</small>
                </router-link>
                <details v-if="citation.scoreBreakdown"><summary>查看排序依据</summary>
                  <p style="overflow-wrap: anywhere">{{ citation.scoreBreakdown }}</p>
                </details>
                <a-select style="width: 100%; margin-top: 8px" placeholder="反馈相关性"
                  :value="feedbackValues[turn.task.taskId + ':' + citation.pictureId]"
                  :options="feedbackOptions" @change="value => saveFeedback(turn, citation.pictureId, String(value))" />
                </div>
              </div>
              <a-space v-if="turn.answer && turn.task.status === 'SUCCEEDED'" class="task-actions">
                <a-button size="small" @click="exportReport(turn, 'md')">下载 Markdown</a-button>
                <a-button size="small" @click="exportReport(turn, 'json')">下载 JSON</a-button>
              </a-space>
              <div v-if="['FAILED', 'CANCELLED'].includes(turn.task.status)" class="task-actions">
                <a-button size="small" @click="resumeTask(turn)">重新执行</a-button>
              </div>
            </div>
          </article>
          <a-empty v-if="!loadingHistory && !turns.length" description="输入需求开始检索实验室视觉资产" />
        </a-spin>
      </section>

      <footer class="composer">
        <div class="example-picker">
          <span>平台样例图</span>
          <a-select v-model:value="selectedPictureIds" mode="tags" :max-tag-count="3"
            :token-separators="[',', ' ']" placeholder="输入图片 ID，最多 20 张" />
          <small>样例图会先由后端复核当前账号权限，再用于站内相似检索。</small>
        </div>
        <a-textarea v-model:value="draft" :maxlength="8000" :auto-size="{ minRows: 2, maxRows: 5 }"
          placeholder="例如：查找最近的模型预测对比图，并说明可见差异" @press-enter="handleEnter" />
        <div class="composer-actions">
          <span>仅显示执行阶段、工具与证据，不展示模型隐藏思维链</span>
          <a-space>
            <a-button v-if="activeTask" danger @click="cancelTask">停止</a-button>
            <a-button type="primary" :loading="submitting" :disabled="!!activeTask" @click="submit">发送</a-button>
          </a-space>
        </div>
      </footer>
    </main>
  </div>
</template>

<script setup lang="ts">
import AgentAnswer from '@/components/AgentAnswer.vue'
import request from '@/request'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message as antMessage } from 'ant-design-vue'
import { cancelAgentTask, createAgentConversation, listAgentConversations, listAgentMessages,
  listAgentTaskEvents, listAgentTasks, resumeAgentTask, submitAgentMessage,
  type AgentConversation, type AgentTask, type AgentTaskEvent } from '@/api/agentController'
import { connectAgentTaskEvents, type AgentStreamEvent } from '@/utils/agentEventStream'

type Citation = { pictureId: string; name?: string; category?: string; matchLevel?: string; scoreBreakdown?: string }
type Turn = { task: AgentTask; query: string; answer: string; citations: Citation[]; tools: string[]; cursor: string }
const route = useRoute()
const conversations = ref<AgentConversation[]>([])
const activeConversationId = ref('')
const turns = ref<Turn[]>([])
const draft = ref('')
const routePictureId = typeof route.query.pictureId === 'string' ? route.query.pictureId : ''
const selectedPictureIds = ref<string[]>(routePictureId ? [routePictureId] : [])
const loadingConversations = ref(false)
const loadingHistory = ref(false)
const submitting = ref(false)
const messageContainer = ref<HTMLElement>()
let disconnect: (() => void) | undefined

const requestedSpaceId = computed(() => typeof route.query.spaceId === 'string' ? route.query.spaceId : undefined)
const allSpaces = computed(() => !requestedSpaceId.value && route.query.scope === 'all')
const scopeLabel = computed(() => allSpaces.value ? '创建时全部授权空间＋已审核公共图（最多50空间，逐次复核）' : requestedSpaceId.value ? `空间 ${requestedSpaceId.value}` : '公共图库范围')
const activeTurn = computed(() => [...turns.value].reverse().find((turn) => ['PENDING', 'RUNNING'].includes(turn.task.status)))
const activeTask = computed(() => activeTurn.value?.task)
onMounted(loadConversations)
onBeforeUnmount(() => disconnect?.())

const feedbackValues = ref<Record<string, string>>({})
const feedbackOptions = [
  { value: 'relevant', label: '相关' }, { value: 'irrelevant', label: '不相关' },
  { value: 'duplicate', label: '疑似重复' }, { value: 'permission_issue', label: '权限异常' },
]
async function saveFeedback(turn: Turn, pictureId: string, label: string) {
  try {
    const response = await request('/api/agent/tasks/' + turn.task.taskId + '/feedback',
      { method: 'POST', data: { pictureId, label } })
    if (response.data.code !== 0) throw new Error(response.data.message || '反馈保存失败')
    feedbackValues.value[turn.task.taskId + ':' + pictureId] = label
    antMessage.success('反馈已保存')
  } catch (error) { showError(error, '反馈保存失败') }
}

async function exportReport(turn: Turn, format: 'md' | 'json') {
  try {
    // Recheck current conversation ownership even for statistical reports without citations.
    const tasks = await listAgentTasks(turn.task.conversationId)
    if (tasks.data.code !== 0 || !tasks.data.data?.some(t => t.taskId === turn.task.taskId)) {
      throw new Error('报告任务当前不可访问')
    }
    const historyAccess = await listAgentTaskEvents(turn.task.taskId)
    if (historyAccess.data.code !== 0) throw new Error('报告涉及的空间当前不可访问')
    const ids = turn.citations.map(c => c.pictureId)
    if (ids.length) {
      const response = await request('/api/agent/conversations/' + turn.task.conversationId + '/pictures/details',
        { method: 'POST', data: ids })
      if (response.data.code !== 0) throw new Error('引用图片权限已变化，请重新生成报告')
      const allowed = new Set((response.data.data || []).map((p: { pictureId: string }) => p.pictureId))
      if (ids.some(id => !allowed.has(id))) throw new Error('部分图片当前不可访问')
    }
    const scrub = (value: string) => value.replace(/https?:\/\/[^\s<>]+/gi, '[外部地址已移除]')
    const report = {
      version: 'labvision-report-v1', taskId: turn.task.taskId,
      conversationId: turn.task.conversationId, exportedAt: new Date().toISOString(),
      taskCreatedAt: turn.task.createTime, scope: scopeLabel.value,
      query: scrub(turn.query), answer: scrub(turn.answer),
      citations: turn.citations.map(c => ({ pictureId: c.pictureId, name: scrub(c.name || ''),
        category: scrub(c.category || ''), matchLevel: c.matchLevel,
        scoreBreakdown: c.scoreBreakdown })),
      limitations: '基于任务生成时的证据；下载时已重新检查图片权限。视觉观察和初始阈值不代表实验结论。',
    }
    const text = format === 'json' ? JSON.stringify(report, null, 2)
      : '# LabVision Hub 分析报告\n\n'
        + '任务：' + report.taskId + '\n\n范围：' + report.scope
        + '\n\n导出时间：' + report.exportedAt + '\n\n问题：' + report.query
        + '\n\n' + report.answer + '\n\n限制：' + report.limitations
        + '\n\n引用：\n' + report.citations.map(c => '- ' + c.name + ' [图片 ID: ' + c.pictureId + ']').join('\n')
    const url = URL.createObjectURL(new Blob([text], { type: format === 'json'
      ? 'application/json;charset=utf-8' : 'text/markdown;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'labvision-' + turn.task.taskId + '.' + format
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (error) { showError(error, '导出失败') }
}

async function loadConversations() {
  loadingConversations.value = true
  try {
    const response = await listAgentConversations()
    if (response.data.code !== 0) throw new Error(response.data.message || '加载失败')
    conversations.value = (response.data.data || []).filter((item) => Boolean(item.allSpaces) === allSpaces.value && (item.spaceId || undefined) === requestedSpaceId.value)
    if (conversations.value[0]) await selectConversation(conversations.value[0].conversationId)
  } catch (error) { showError(error, '会话加载失败') }
  finally { loadingConversations.value = false }
}

async function createConversation() {
  try {
    const response = await createAgentConversation(requestedSpaceId.value, allSpaces.value)
    const id = response.data.data?.conversationId
    if (response.data.code !== 0 || !id) throw new Error(response.data.message || '创建失败')
    conversations.value.unshift({ conversationId: id, spaceId: requestedSpaceId.value, allSpaces: allSpaces.value, status: 'ACTIVE' })
    await selectConversation(id)
  } catch (error) { showError(error, '会话创建失败') }
}

async function selectConversation(id: string) {
  if (activeConversationId.value === id && turns.value.length) return
  disconnect?.(); disconnect = undefined
  activeConversationId.value = id
  loadingHistory.value = true
  try {
    const [messageResponse, taskResponse] = await Promise.all([listAgentMessages(id), listAgentTasks(id)])
    if (messageResponse.data.code !== 0 || taskResponse.data.code !== 0) throw new Error('历史记录加载失败')
    const messages = messageResponse.data.data || []
    turns.value = await Promise.all((taskResponse.data.data || []).map(async (task) => {
      const query = messages.find((item) => item.id === task.inputMessageId)?.content || '历史请求'
      const response = await listAgentTaskEvents(task.taskId)
      const feedback = await request('/api/agent/tasks/' + task.taskId + '/feedback', { method: 'GET' })
      if (feedback.data.code === 0) {
        for (const item of feedback.data.data || []) {
          feedbackValues.value[task.taskId + ':' + item.pictureId] = item.label
        }
      }
      return buildTurn(task, query, response.data.data || [])
    }))
    if (activeTurn.value) connect(activeTurn.value)
    await scrollToBottom()
  } catch (error) { showError(error, '历史记录加载失败') }
  finally { loadingHistory.value = false }
}

function buildTurn(task: AgentTask, query: string, events: AgentTaskEvent[]) {
  const turn: Turn = { task, query, answer: '', citations: [], tools: [], cursor: '0' }
  for (const event of events) applyEvent(turn, { id: event.eventId,
    type: event.eventType as AgentStreamEvent['type'], payload: parsePayload(event.payloadJson) })
  return turn
}

async function submit() {
  const ids = [...new Set(selectedPictureIds.value.map((value) => value.trim()).filter(Boolean))]
  const maxLong = '9223372036854775807'
  const invalidId = ids.some((value) => !/^[1-9]\d{0,18}$/.test(value)
    || (value.length === maxLong.length && value > maxLong))
  if (ids.length > 20 || invalidId) {
    antMessage.error('请输入 1 至 20 个有效的平台图片 ID')
    return
  }
  const content = draft.value.trim() || (ids.length ? '查找与所选图片视觉相似的资产' : '')
  if (!content || submitting.value || activeTask.value) return
  submitting.value = true
  try {
    if (!activeConversationId.value) await createConversation()
    if (!activeConversationId.value) return
    const response = await submitAgentMessage(activeConversationId.value, content, ids)
    const task = response.data.data
    if (response.data.code !== 0 || !task) throw new Error(response.data.message || '提交失败')
    const turn: Turn = { task, query: content, answer: '', citations: [], tools: [], cursor: '0' }
    turns.value.push(turn); draft.value = ''; connect(turn); await scrollToBottom()
  } catch (error) { showError(error, '任务提交失败') }
  finally { submitting.value = false }
}

function connect(turn: Turn) {
  disconnect?.()
  disconnect = connectAgentTaskEvents(turn.task.taskId, turn.cursor, async (event) => {
    applyEvent(turn, event)
    if (['done', 'error'].includes(event.type) || turn.task.status === 'CANCELLED') {
      disconnect?.(); disconnect = undefined
    }
    await scrollToBottom()
  }, () => { /* EventSource 按服务端 retry 自动续传 Last-Event-ID。 */ })
}

function applyEvent(turn: Turn, event: AgentStreamEvent) {
  if (event.id) turn.cursor = event.id
  if (event.type === 'answer_delta' && typeof event.payload.text === 'string') turn.answer += event.payload.text
  if (event.type === 'citation' && typeof event.payload.pictureId === 'string'
      && !turn.citations.some((item) => item.pictureId === event.payload.pictureId)) {
    turn.citations.push(event.payload as Citation)
  }
  if (['tool_start', 'tool_result'].includes(event.type) && typeof event.payload.tool === 'string'
      && !turn.tools.includes(event.payload.tool)) turn.tools.push(event.payload.tool)
  if (typeof event.payload.stage === 'string') turn.task.stage = event.payload.stage
  if (typeof event.payload.status === 'string') turn.task.status = event.payload.status
  if (event.type === 'done') turn.task.status = 'SUCCEEDED'
  if (event.type === 'error') {
    turn.task.status = 'FAILED'
    if (typeof event.payload.message === 'string') turn.task.errorMessage = event.payload.message
  }
}

async function cancelTask() {
  if (!activeTurn.value) return
  const response = await cancelAgentTask(activeTurn.value.task.taskId)
  if (response.data.code === 0 && response.data.data) {
    Object.assign(activeTurn.value.task, response.data.data); disconnect?.(); disconnect = undefined
  } else antMessage.error(response.data.message || '停止失败')
}

async function resumeTask(turn: Turn) {
  const response = await resumeAgentTask(turn.task.taskId)
  if (response.data.code === 0 && response.data.data) {
    const resumeCursor = turn.cursor
    Object.assign(turn.task, response.data.data)
    turn.answer = ''; turn.citations = []; turn.tools = []; turn.cursor = resumeCursor; connect(turn)
  } else antMessage.error(response.data.message || '重新执行失败')
}

function handleEnter(event: KeyboardEvent) { if (!event.shiftKey) { event.preventDefault(); submit() } }
function parsePayload(value: string): Record<string, unknown> { try { return JSON.parse(value) } catch { return {} } }
function showError(error: unknown, fallback: string) { antMessage.error(error instanceof Error ? error.message : fallback) }
function shortId(value: string) { return value.slice(0, 8) }
function formatTime(value?: string) { return value ? new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '刚刚' }
function statusText(value: string) { return ({ PENDING: '排队中', RUNNING: '执行中', SUCCEEDED: '已完成', FAILED: '失败', CANCELLED: '已停止' } as Record<string, string>)[value] || value }
function statusColor(value: string) { return ({ RUNNING: 'processing', SUCCEEDED: 'success', FAILED: 'error', CANCELLED: 'default' } as Record<string, string>)[value] || 'warning' }
function stageText(value: string) { return ({ QUEUED: '任务已排队', INITIALIZING: '正在初始化', PLANNING: '正在理解需求', RETRIEVED: '已完成候选检索', COMPLETED: '分析完成', CANCELLED: '任务已停止' } as Record<string, string>)[value] || value }
async function scrollToBottom() { await nextTick(); if (messageContainer.value) messageContainer.value.scrollTop = messageContainer.value.scrollHeight }
</script>

<style scoped>
.agent-workbench { display: grid; grid-template-columns: 260px minmax(0, 1fr); height: calc(100vh - 145px); min-height: 600px; background: #fff; border: 1px solid #edf0f4; border-radius: 16px; overflow: hidden; box-shadow: 0 12px 36px rgba(24, 39, 75, .06); }
.conversation-panel { padding: 18px 12px; border-right: 1px solid #edf0f4; background: #f8fafc; overflow-y: auto; }
.panel-title { display: flex; align-items: center; justify-content: space-between; padding: 0 6px 14px; }
.panel-title small, .conversation-item small { display: block; color: #8b95a7; margin-top: 3px; }
.conversation-item { width: 100%; padding: 11px 12px; margin-bottom: 6px; border: 0; border-radius: 10px; background: transparent; text-align: left; cursor: pointer; color: #334155; }
.conversation-item:hover, .conversation-item.active { background: #e8f2ff; color: #1677ff; }
.example-picker { display: grid; grid-template-columns: 90px minmax(0, 1fr); gap: 6px 10px; align-items: center; margin-bottom: 10px; }
.example-picker small { grid-column: 2; color: #8b95a7; }
.chat-panel { display: grid; grid-template-rows: auto minmax(0, 1fr) auto; min-width: 0; }
.chat-header { display: flex; justify-content: space-between; align-items: flex-start; padding: 20px 24px; border-bottom: 1px solid #edf0f4; }
.chat-header h2 { margin: 0 0 4px; font-size: 20px; }.chat-header p { margin: 0; color: #7a8494; }
.messages { padding: 24px; overflow-y: auto; background: linear-gradient(180deg, #fbfdff 0%, #fff 100%); }
.turn { margin-bottom: 24px; }.user-message { margin-left: auto; max-width: 72%; width: fit-content; padding: 11px 15px; background: #1677ff; color: #fff; border-radius: 14px 14px 3px 14px; }
.agent-message { max-width: 86%; margin-top: 12px; padding: 16px; border: 1px solid #e8edf3; border-radius: 4px 14px 14px 14px; background: #fff; }
.stage-line { margin-bottom: 10px; color: #657187; font-size: 13px; }.stage-dot { display: inline-block; width: 7px; height: 7px; margin-right: 7px; border-radius: 50%; background: #36cfc9; }
.agent-message pre { margin: 0; white-space: pre-wrap; font: inherit; line-height: 1.75; color: #273449; }.waiting { color: #8b95a7; }
.citations { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 8px; margin-top: 14px; }.citation-card { padding: 10px 12px; border-radius: 9px; background: #f2f7ff; color: #28558a; }.citation-card span, .citation-card small { display: block; }.citation-card small { margin-top: 3px; color: #7b8da6; }
.task-actions { margin-top: 12px; }.composer { padding: 16px 20px; border-top: 1px solid #edf0f4; background: #fff; }.composer-actions { display: flex; align-items: center; justify-content: space-between; margin-top: 10px; color: #8b95a7; font-size: 12px; }
@media (max-width: 800px) { .agent-workbench { grid-template-columns: 1fr; height: auto; }.conversation-panel { max-height: 180px; border-right: 0; border-bottom: 1px solid #edf0f4; }.messages { min-height: 420px; max-height: 60vh; }.composer-actions { align-items: flex-end; gap: 8px; }.user-message, .agent-message { max-width: 94%; } }
</style>
