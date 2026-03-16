<template>
  <div class="rte-wrapper">
    <div class="rte-toolbar">
      <button type="button" class="rte-btn" @click="exec('bold')" title="Bold">
        <strong>B</strong>
      </button>
      <button type="button" class="rte-btn" @click="exec('italic')" title="Italic">
        <em>I</em>
      </button>
      <button type="button" class="rte-btn" @click="exec('underline')" title="Underline">
        <u>U</u>
      </button>
      <span class="rte-sep"></span>
      <button type="button" class="rte-btn" @click="exec('insertUnorderedList')" title="Bullet List">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="3" cy="6" r="1.5" fill="currentColor" stroke="none"/><circle cx="3" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="3" cy="18" r="1.5" fill="currentColor" stroke="none"/></svg>
      </button>
      <button type="button" class="rte-btn" @click="exec('insertOrderedList')" title="Numbered List">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="10" y1="6" x2="21" y2="6"/><line x1="10" y1="12" x2="21" y2="12"/><line x1="10" y1="18" x2="21" y2="18"/><text x="1" y="8" font-size="8" fill="currentColor" stroke="none" font-family="sans-serif">1</text><text x="1" y="14" font-size="8" fill="currentColor" stroke="none" font-family="sans-serif">2</text><text x="1" y="20" font-size="8" fill="currentColor" stroke="none" font-family="sans-serif">3</text></svg>
      </button>
      <span class="rte-sep"></span>
      <select class="rte-select" @change="onHeadingChange">
        <option value="">Normal</option>
        <option value="h2">Heading</option>
        <option value="h3">Subheading</option>
      </select>
      <span class="rte-sep"></span>
      <button type="button" class="rte-btn" @click="exec('removeFormat')" title="Clear Formatting">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="4" y1="4" x2="20" y2="20"/><path d="M6 12h8"/></svg>
      </button>
    </div>
    <div
      ref="editorRef"
      class="rte-content"
      contenteditable="true"
      @input="onInput"
      @paste="onPaste"
    ></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const editorRef = ref(null)

function exec(command, value = null) {
  document.execCommand(command, false, value)
  editorRef.value?.focus()
  emitContent()
}

function onHeadingChange(e) {
  const tag = e.target.value
  if (tag) {
    document.execCommand('formatBlock', false, tag)
  } else {
    document.execCommand('formatBlock', false, 'p')
  }
  e.target.value = ''
  editorRef.value?.focus()
  emitContent()
}

function onInput() {
  emitContent()
}

function onPaste(e) {
  e.preventDefault()
  const text = e.clipboardData?.getData('text/plain') || ''
  document.execCommand('insertText', false, text)
}

function emitContent() {
  if (editorRef.value) {
    emit('update:modelValue', editorRef.value.innerHTML)
  }
}

onMounted(() => {
  if (editorRef.value && props.modelValue) {
    editorRef.value.innerHTML = props.modelValue
  }
})

watch(() => props.modelValue, (val) => {
  if (editorRef.value && editorRef.value.innerHTML !== val) {
    editorRef.value.innerHTML = val || ''
  }
})
</script>

<style scoped>
.rte-wrapper {
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-card, #fff);
}
.rte-toolbar {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-color, #e2e8f0);
  background: var(--bg-subtle, #f8fafc);
  flex-wrap: wrap;
}
.rte-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-primary, #334155);
  transition: background 0.15s;
}
.rte-btn:hover {
  background: var(--border-color, #e2e8f0);
}
.rte-sep {
  width: 1px;
  height: 18px;
  background: var(--border-color, #e2e8f0);
  margin: 0 4px;
}
.rte-select {
  height: 28px;
  padding: 0 6px;
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: 4px;
  font-size: 12px;
  background: var(--bg-card, #fff);
  color: var(--text-primary, #334155);
  cursor: pointer;
}
.rte-content {
  min-height: 120px;
  max-height: 300px;
  overflow-y: auto;
  padding: 12px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary, #334155);
  outline: none;
}
.rte-content:empty::before {
  content: 'Type description here...';
  color: var(--text-tertiary, #94a3b8);
}
.rte-content :deep(h2) {
  font-size: 18px;
  font-weight: 600;
  margin: 8px 0 4px;
}
.rte-content :deep(h3) {
  font-size: 15px;
  font-weight: 600;
  margin: 6px 0 4px;
}
.rte-content :deep(p) {
  margin: 4px 0;
}
.rte-content :deep(ul),
.rte-content :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}
</style>
