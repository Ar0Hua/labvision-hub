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
      <pre v-else>{{ block.text }}</pre>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ text: string }>()
// Render cells as escaped Vue text. Model output is never treated as HTML.
const blocks = computed(() => {
  const lines = props.text.split('\n')
  const result: { table: boolean; rows: string[][]; text: string }[] = []
  const cells = (line: string) => line.trim().replace(/^\||\|$/g, '').split('|').map(s => s.trim())
  for (let i = 0; i < lines.length;) {
    if (lines[i].trim().startsWith('|') && i + 1 < lines.length
      && cells(lines[i + 1]).every(s => /^:?-{3,}:?$/.test(s))) {
      const rows = [cells(lines[i])]
      i += 2
      while (i < lines.length && lines[i].trim().startsWith('|')) rows.push(cells(lines[i++]))
      result.push({ table: true, rows, text: '' })
    } else {
      result.push({ table: false, rows: [], text: lines[i++] })
    }
  }
  return result
})
</script>

<style scoped>
pre { white-space: pre-wrap; overflow-wrap: anywhere; margin: 0; font: inherit; min-height: 1em; }
.table-scroll { overflow-x: auto; margin: 12px 0; }
table { border-collapse: collapse; font-size: 13px; }
th, td { padding: 6px 10px; border: 1px solid #dce3ed; text-align: right; white-space: nowrap; }
th { background: #f2f7ff; }
</style>
