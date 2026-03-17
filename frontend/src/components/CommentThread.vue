<template>
  <div class="comment-thread">
    <div class="comment-thread-header">
      <h4 class="comment-thread-title">Comments</h4>
      <span v-if="comments.length" class="comment-count">{{ comments.length }}</span>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="comment-loading">
      <span class="comment-loading-spinner"></span>
      <span>Loading comments...</span>
    </div>

    <!-- Comments list -->
    <div v-else-if="comments.length" class="comment-list">
      <div
        v-for="comment in comments"
        :key="comment.name"
        class="comment-item"
      >
        <div class="comment-avatar">
          {{ getInitials(comment.user) }}
        </div>
        <div class="comment-body">
          <div class="comment-meta">
            <span class="comment-user">{{ formatUserName(comment.user) }}</span>
            <span class="comment-time">{{ formatTimestamp(comment.timestamp) }}</span>
          </div>
          <div class="comment-content" v-html="renderCommentWithMentions(comment.comment)"></div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="comment-empty">
      No comments yet. Be the first to add one.
    </div>

    <!-- New comment input -->
    <div class="comment-input-area">
      <div class="comment-input-wrapper">
        <textarea
          ref="textareaRef"
          v-model="newComment"
          class="comment-textarea"
          placeholder="Write a comment... Use @ to mention"
          rows="2"
          @keydown.enter.meta="postComment"
          @keydown.enter.ctrl="postComment"
          @input="onTextInput"
          @keydown="onTextKeydown"
        ></textarea>

        <!-- @Mention dropdown -->
        <div
          v-if="showMentionDropdown && filteredMembers.length"
          class="mention-dropdown"
          :style="mentionDropdownStyle"
        >
          <div
            v-for="(member, idx) in filteredMembers"
            :key="member.user"
            class="mention-option"
            :class="{ 'mention-option-active': idx === mentionActiveIndex }"
            @mousedown.prevent="selectMention(member)"
          >
            <div class="mention-avatar">{{ getInitials(member.user) }}</div>
            <div class="mention-info">
              <span class="mention-name">{{ member.full_name }}</span>
              <span class="mention-email">{{ member.user }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Selected mentions tags -->
      <div v-if="selectedMentions.length" class="mention-tags">
        <span v-for="m in selectedMentions" :key="m.user" class="mention-tag">
          @{{ m.full_name }}
          <button class="mention-tag-remove" @click="removeMention(m)">×</button>
        </span>
      </div>

      <div class="comment-input-footer">
        <span class="comment-input-hint">@ to mention · Ctrl+Enter to send</span>
        <button
          class="comment-submit-btn"
          :disabled="!newComment.trim() || posting"
          @click="postComment"
        >
          {{ posting ? 'Posting...' : 'Post' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { call, getList } from '@/utils/frappe'

const props = defineProps({
  taskName: {
    type: String,
    required: true,
  },
  projectName: {
    type: String,
    default: '',
  },
})

const comments = ref([])
const loading = ref(false)
const newComment = ref('')
const posting = ref(false)
const textareaRef = ref(null)

// Mention state
const projectMembers = ref([])
const showMentionDropdown = ref(false)
const mentionQuery = ref('')
const mentionStartPos = ref(-1)
const mentionActiveIndex = ref(0)
const selectedMentions = ref([])
const mentionDropdownStyle = ref({})

// Fetch project members for @mention
async function fetchProjectMembers() {
  if (!props.projectName) return
  try {
    const result = await call('next_pms.api.crud.get_project_members', {
      project: props.projectName,
    })
    projectMembers.value = result || []
  } catch (e) {
    console.error('Failed to fetch project members:', e)
  }
}

const filteredMembers = computed(() => {
  const q = mentionQuery.value.toLowerCase()
  const currentUser = (window.pms_boot || window['pms_boot'])?.user || ''
  return projectMembers.value.filter(m => {
    if (m.user === currentUser) return false
    if (selectedMentions.value.some(s => s.user === m.user)) return false
    if (!q) return true
    return m.full_name.toLowerCase().includes(q) || m.user.toLowerCase().includes(q)
  }).slice(0, 6)
})

function onTextInput() {
  const textarea = textareaRef.value
  if (!textarea) return

  const text = textarea.value
  const cursorPos = textarea.selectionStart

  // Find the last '@' before cursor that isn't preceded by a word char
  let atPos = -1
  for (let i = cursorPos - 1; i >= 0; i--) {
    if (text[i] === '@') {
      if (i === 0 || /[\s\n]/.test(text[i - 1])) {
        atPos = i
      }
      break
    }
    if (text[i] === ' ' || text[i] === '\n') break
  }

  if (atPos >= 0) {
    const query = text.substring(atPos + 1, cursorPos)
    if (query.length <= 20) {
      mentionQuery.value = query
      mentionStartPos.value = atPos
      mentionActiveIndex.value = 0
      showMentionDropdown.value = true
      return
    }
  }

  showMentionDropdown.value = false
}

function onTextKeydown(event) {
  if (!showMentionDropdown.value || !filteredMembers.value.length) return

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    mentionActiveIndex.value = (mentionActiveIndex.value + 1) % filteredMembers.value.length
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    mentionActiveIndex.value = (mentionActiveIndex.value - 1 + filteredMembers.value.length) % filteredMembers.value.length
  } else if (event.key === 'Enter' && !event.metaKey && !event.ctrlKey) {
    event.preventDefault()
    selectMention(filteredMembers.value[mentionActiveIndex.value])
  } else if (event.key === 'Escape') {
    event.preventDefault()
    showMentionDropdown.value = false
  }
}

function selectMention(member) {
  const textarea = textareaRef.value
  if (!textarea) return

  const text = newComment.value
  const before = text.substring(0, mentionStartPos.value)
  const after = text.substring(textarea.selectionStart)
  const mentionText = `@${member.full_name} `

  newComment.value = before + mentionText + after
  showMentionDropdown.value = false

  if (!selectedMentions.value.some(m => m.user === member.user)) {
    selectedMentions.value.push({ user: member.user, full_name: member.full_name })
  }

  nextTick(() => {
    const newPos = before.length + mentionText.length
    textarea.focus()
    textarea.setSelectionRange(newPos, newPos)
  })
}

function removeMention(member) {
  selectedMentions.value = selectedMentions.value.filter(m => m.user !== member.user)
}

function renderCommentWithMentions(text) {
  if (!text) return ''
  // Escape HTML first
  const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  // Highlight @mentions
  return escaped.replace(/@([\w\s]+?)(?=\s@|\s*$|[.,!?;\n])/g, '<span class="mention-highlight">@$1</span>')
}

async function fetchComments() {
  loading.value = true
  try {
    const result = await getList('PMS Comment', {
      filters: { task: props.taskName },
      fields: ['name', 'user', 'comment', 'timestamp', 'mentions'],
      orderBy: 'timestamp asc',
      limit: 100,
    })
    comments.value = result || []
  } catch (error) {
    console.error('Failed to fetch comments:', error)
    comments.value = []
  } finally {
    loading.value = false
  }
}

async function postComment() {
  const text = newComment.value.trim()
  if (!text || posting.value) return

  posting.value = true
  try {
    const boot = window.pms_boot || window['pms_boot']
    const currentUser = boot?.user || window.frappe?.session?.user || 'Administrator'
    const mentionEmails = selectedMentions.value.map(m => m.user).join(',')

    await call('frappe.client.insert', {
      doc: {
        doctype: 'PMS Comment',
        task: props.taskName,
        user: currentUser,
        comment: text,
        mentions: mentionEmails,
      },
    })
    newComment.value = ''
    selectedMentions.value = []
    await fetchComments()
  } catch (error) {
    console.error('Failed to post comment:', error)
    alert('Failed to post comment. Please try again.')
  } finally {
    posting.value = false
  }
}

function getInitials(user) {
  if (!user) return '?'
  const parts = user.split(/[\s@.]+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return user.substring(0, 2).toUpperCase()
}

function formatUserName(user) {
  if (!user) return 'Unknown'
  const atIndex = user.indexOf('@')
  if (atIndex > -1) {
    return user.substring(0, atIndex).replace(/[._]/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  }
  return user
}

function formatTimestamp(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  })
}

onMounted(() => {
  fetchComments()
  fetchProjectMembers()
})
</script>

<style scoped>
.comment-thread {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  overflow: visible;
}

.comment-thread-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-light);
}

.comment-thread-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.comment-count {
  font-size: 11px;
  font-weight: 600;
  background: var(--bg-surface-hover);
  color: var(--text-secondary);
  padding: 2px 7px;
  border-radius: 10px;
}

/* Loading */
.comment-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 24px 18px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.comment-loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Comment list */
.comment-list {
  max-height: 400px;
  overflow-y: auto;
  padding: 8px 0;
}

.comment-item {
  display: flex;
  gap: 10px;
  padding: 10px 18px;
  transition: background 0.1s;
}

.comment-item:hover {
  background: #fafbfc;
}

.comment-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #2563EB;
  color: white;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.comment-body {
  flex: 1;
  min-width: 0;
}

.comment-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 3px;
}

.comment-user {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.comment-time {
  font-size: 11px;
  color: var(--text-tertiary);
}

.comment-content {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.comment-content :deep(.mention-highlight) {
  color: #2563EB;
  font-weight: 600;
  background: rgba(37, 99, 235, 0.08);
  padding: 1px 4px;
  border-radius: 4px;
}

/* Empty state */
.comment-empty {
  padding: 32px 18px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
}

/* Input area */
.comment-input-area {
  padding: 12px 18px 14px;
  border-top: 1px solid var(--border-light);
}

.comment-input-wrapper {
  position: relative;
}

.comment-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 13px;
  font-family: inherit;
  color: var(--text-primary);
  resize: vertical;
  min-height: 44px;
  line-height: 1.5;
  transition: border-color 0.15s;
}

.comment-textarea::placeholder {
  color: var(--text-tertiary);
}

.comment-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

/* Mention dropdown */
.mention-dropdown {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid var(--border-default);
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  max-height: 220px;
  overflow-y: auto;
  z-index: 100;
  margin-bottom: 4px;
}

.mention-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background 0.1s;
}

.mention-option:first-child {
  border-radius: 10px 10px 0 0;
}

.mention-option:last-child {
  border-radius: 0 0 10px 10px;
}

.mention-option:hover,
.mention-option-active {
  background: #f0f4ff;
}

.mention-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #2563EB;
  color: white;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.mention-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.mention-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.mention-email {
  font-size: 11px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Mention tags */
.mention-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.mention-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: rgba(37, 99, 235, 0.1);
  color: #2563EB;
  font-size: 12px;
  font-weight: 500;
  border-radius: 12px;
}

.mention-tag-remove {
  background: none;
  border: none;
  color: #2563EB;
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  opacity: 0.7;
}

.mention-tag-remove:hover {
  opacity: 1;
}

.comment-input-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.comment-input-hint {
  font-size: 11px;
  color: var(--text-tertiary);
}

.comment-submit-btn {
  padding: 6px 16px;
  background: #2563EB;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.comment-submit-btn:hover:not(:disabled) {
  background: #1D4ED8;
}

.comment-submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
