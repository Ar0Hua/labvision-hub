import request from '@/request'

export type AgentConversation = { conversationId: string; spaceId?: string; status: string; createTime?: string; updateTime?: string }
export type AgentMessage = { id: string; conversationId: string; role: string; content: string; createTime?: string }
export type AgentTask = { taskId: string; conversationId: string; inputMessageId: string; status: string; stage: string; errorCode?: string; errorMessage?: string; retryCount?: number; createTime?: string; updateTime?: string }
export type AgentTaskEvent = { eventId: string; eventType: string; payloadJson: string; createTime?: string }
type ApiResponse<T> = { code: number; data?: T; message?: string }

export const listAgentConversations = () => request<ApiResponse<AgentConversation[]>>('/api/agent/conversations', { method: 'GET' })
export const createAgentConversation = (spaceId?: string) => request<ApiResponse<{ conversationId: string }>>('/api/agent/conversations', { method: 'POST', headers: { 'Content-Type': 'application/json' }, data: spaceId ? { spaceId } : {} })
export const listAgentMessages = (id: string) => request<ApiResponse<AgentMessage[]>>(`/api/agent/conversations/${id}/messages`, { method: 'GET' })
export const listAgentTasks = (id: string) => request<ApiResponse<AgentTask[]>>(`/api/agent/conversations/${id}/tasks`, { method: 'GET' })
export const submitAgentMessage = (id: string, content: string) => request<ApiResponse<AgentTask>>(`/api/agent/conversations/${id}/messages`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, data: { content } })
export const listAgentTaskEvents = (id: string, afterEventId = '0') => request<ApiResponse<AgentTaskEvent[]>>(`/api/agent/tasks/${id}/events/history`, { method: 'GET', params: { afterEventId, limit: 200 } })
export const cancelAgentTask = (id: string) => request<ApiResponse<AgentTask>>(`/api/agent/tasks/${id}/cancel`, { method: 'POST' })
export const resumeAgentTask = (id: string) => request<ApiResponse<AgentTask>>(`/api/agent/tasks/${id}/resume`, { method: 'POST' })
