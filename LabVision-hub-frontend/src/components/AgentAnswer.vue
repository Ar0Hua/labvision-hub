<template>
  <div class="agent-answer">
    <template v-for="(block, index) in blocks" :key="index">
      <div v-if="block.table" class="table-scroll">
        <table>
          <thead><tr><th v-for="(cell, c) in block.rows[0]" :key="c">{{ cell }}</th></tr></thead>
          <tbody><tr v-for="(row, r) in block.rows.slice(1)" :key="r">
            <td v-for="(cell, c) in row" :key="c">{{ cell }}</td>
          </tr></tbody>
        </table>
      </div>
      <h3 v-else-if="block.kind === 'heading'">{{ block.text }}</h3>
      <ol v-else-if="block.kind === 'ordered'" :start="block.start"><li v-for="(item, n) in block.items" :key="n"><template v-for="(part, p) in inline(item)" :key="p"><strong v-if="part.bold">{{ part.text }}</strong><span v-else>{{ part.text }}</span></template></li></ol>
      <ul v-else-if="block.kind === 'list'"><li v-for="(item, n) in block.items" :key="n"><template v-for="(part, p) in inline(item)" :key="p"><strong v-if="part.bold">{{ part.text }}</strong><span v-else>{{ part.text }}</span></template></li></ul>
      <blockquote v-else-if="block.kind === 'quote'">{{ block.text }}</blockquote>
      <p v-else><template v-for="(part, p) in inline(block.text)" :key="p"><strong v-if="part.bold">{{ part.text }}</strong><span v-else>{{ part.text }}</span></template></p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ text: string }>()
const inline = (text: string) => text.split(/(\*\*[^*]+\*\*)/g).map(part => ({
  bold: part.startsWith('**') && part.endsWith('**'),
  text: part.startsWith('**') && part.endsWith('**') ? part.slice(2, -2) : part,
}))
// Render cells as escaped Vue text. Model output is never treated as HTML.
const blocks = computed(() => {
  const lines = props.text.split('\n')
  const result: { table?: boolean; rows: string[][]; text: string; kind?: string; items?: string[]; start?: number }[] = []
  const cells = (line: string) => line.trim().replace(/^\||\|$/g, '').split('|').map(s => s.trim())
  for (let i = 0; i < lines.length;) {
    if (lines[i].trim().startsWith('|') && i + 1 < lines.length
      && cells(lines[i + 1]).every(s => /^:?-{3,}:?$/.test(s))) {
      const rows = [cells(lines[i])]
      i += 2
      while (i < lines.length && lines[i].trim().startsWith('|')) rows.push(cells(lines[i++]))
      result.push({ table: true, rows, text: '' })
    } else {
      const line = lines[i].trim()
      if (!line) { i++; continue }
      const heading = line.match(/^#{1,6}\s+(.+)$/)
      const list = line.match(/^(?:(\d+)[.)、]\s+|[-*+]\s+)(.+)$/)
      if (heading) {
        result.push({ kind: 'heading', rows: [], text: heading[1] }); i++
      } else if (list) {
        const ordered = !!list[1]
        const items: string[] = []
        const pattern = ordered ? /^\d+[.)、]\s+(.+)$/ : /^[-*+]\s+(.+)$/
        while (i < lines.length) {
          const item = lines[i].trim().match(pattern)
          if (!item) break
          items.push(item[1]); i++
        }
        result.push({ kind: ordered ? 'ordered' : 'list', rows: [], text: '', items, start: ordered ? Number(list[1]) : undefined })
      } else if (line.startsWith('> ')) {
        result.push({ kind: 'quote', rows: [], text: line.slice(2) }); i++
      } else {
        result.push({ rows: [], text: lines[i++] })
      }
    }
  }
  return result
})
</script>

<style scoped>
.agent-answer { min-width: 0; line-height: 1.9; font-size: 14px; color: #334155; overflow-wrap: anywhere; }
p { white-space: pre-wrap; margin: 0 0 14px; }
h3 { font-size: 16px; color: #1e3a5f; margin: 24px 0 12px; padding-left: 10px; border-left: 3px solid #60a5fa; line-height: 1.6; }
h3:first-child { margin-top: 0; }
strong { color: #203b60; font-weight: 600; }
ol, ul { padding-left: 24px; margin: 12px 0 20px; }
li { padding: 5px 0 5px 6px; } li::marker { color: #4280c5; font-weight: 600; }
blockquote { margin: 16px 0; padding: 12px 16px; border-left: 3px solid #93b6dd; border-radius: 0 8px 8px 0; background: #f3f7fc; color: #60748c; }
.table-scroll { overflow-x: auto; margin: 18px 0; border: 1px solid #e0e8f2; border-radius: 10px; }
table { border-collapse: collapse; font-size: 13px; width: 100%; }
th, td { padding: 11px 14px; border-bottom: 1px solid #e7edf5; text-align: left; white-space: nowrap; }
th { background: #edf4fd; color: #345579; font-weight: 600; }
tbody tr:nth-child(even) { background: #f8fafc; } tbody tr:hover { background: #f1f6fd; }
tbody tr:last-child td { border-bottom: 0; }
</style>
