import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from 'typescript'

const source = readFileSync(new URL('../src/utils/agentEventStream.ts', import.meta.url), 'utf8')
  .replace("import { API_BASE_URL } from '@/request'", "const API_BASE_URL = ''")
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2022 } }).outputText
const { connectAgentTaskEvents } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)

test('SSE disconnects are recoverable and business errors retain their payload', () => {
  const previous = globalThis.EventSource
  let instance
  class FakeEventSource extends EventTarget {
    constructor() { super(); instance = this }
    close() { this.closed = true }
  }
  globalThis.EventSource = FakeEventSource
  try {
    const received = []; let errors = 0
    const close = connectAgentTaskEvents('task', '0', event => received.push(event), () => errors++)
    instance.dispatchEvent(new Event('error')); instance.onerror()
    assert.equal(received.length, 0)
    assert.equal(errors, 1)
    instance.dispatchEvent(new MessageEvent('answer_delta', { data: '{"text":"第一段"}', lastEventId: '1' }))
    instance.dispatchEvent(new MessageEvent('answer_delta', { data: '{"text":"第二段"}', lastEventId: '2' }))
    assert.equal(received.map(event => event.payload.text).join(''), '第一段第二段')
    instance.dispatchEvent(new MessageEvent('answer_delta', { data: 'invalid' }))
    assert.equal(errors, 2)
    assert.equal(received.length, 2)
    instance.dispatchEvent(new MessageEvent('error', { data: '{"message":"图片不可用"}', lastEventId: '3' }))
    assert.equal(received[2].payload.message, '图片不可用')
    close(); assert.equal(instance.closed, true)
  } finally { globalThis.EventSource = previous }
})
