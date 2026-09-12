import { API_BASE_URL } from '@/request'

export const AGENT_EVENT_TYPES = ['status', 'tool_start', 'tool_result', 'citation', 'answer_delta', 'approval_required', 'done', 'error'] as const
export type AgentEventType = (typeof AGENT_EVENT_TYPES)[number]
export type AgentStreamEvent = { id: string; type: AgentEventType; payload: Record<string, unknown> }

export function connectAgentTaskEvents(taskId: string, afterEventId: string, onEvent: (event: AgentStreamEvent) => void, onConnectionError: () => void) {
  const source = new EventSource(`${API_BASE_URL}/api/agent/tasks/${encodeURIComponent(taskId)}/events?afterEventId=${encodeURIComponent(afterEventId || '0')}`, { withCredentials: true })
  for (const type of AGENT_EVENT_TYPES) {
    source.addEventListener(type, (raw) => {
      const event = raw as MessageEvent<string>
      try { onEvent({ id: event.lastEventId, type, payload: JSON.parse(event.data) as Record<string, unknown> }) }
      catch { onEvent({ id: event.lastEventId, type: 'error', payload: { message: '事件数据格式错误' } }) }
    })
  }
  source.onerror = onConnectionError
  return () => source.close()
}
