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
          <div class="comment-content">{{ comment.comment }}</div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="comment-empty">
      No comments yet. Be the first to add one.
    </div>

    <!-- New comment input -->
    <div class="comment-input-area">
      <textarea
        v-model="newComment"
        class="comment-textarea"
        placeholder="Write a comment..."
        rows="2"
        @keydown.enter.meta="postComment"
        @keydown.enter.ctrl="postComment"
      ></textarea>
      <div class="comment-input-footer">
        <span class="comment-input-hint">Ctrl+Enter to send</span>
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
import { ref, onMounted } from 'vue'
import { call, getList } from '@/utils/frappe'

const props = defineProps({
  taskName: {
    type: String,
    required: true,
  },
})

const comments = ref([])
const loading = ref(false)
const newComment = ref('')
const posting = ref(false)

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
    await call('frappe.client.insert', {
      doc: {
        doctype: 'PMS Comment',
        task: props.taskName,
        user: currentUser,
        comment: text,
      },
    })
    newComment.value = ''
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
  // Extract name part from email-like strings
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
})
</script>

<style scoped>
.comment-thread {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
}

.comment-thread-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 18px;
  border-bottom: 1px solid #f3f4f6;
}

.comment-thread-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e1e2e;
}

.comment-count {
  font-size: 11px;
  font-weight: 600;
  background: #f3f4f6;
  color: #6b7280;
  padding: 2px 7px;
  border-radius: 10px;
}

/* Loading */
.comment-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 24px 18px;
  color: #9ca3af;
  font-size: 13px;
}

.comment-loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #e5e7eb;
  border-top-color: #6366f1;
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
  background: #6366f1;
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
  color: #1e1e2e;
}

.comment-time {
  font-size: 11px;
  color: #9ca3af;
}

.comment-content {
  font-size: 13px;
  color: #374151;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Empty state */
.comment-empty {
  padding: 32px 18px;
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
}

/* Input area */
.comment-input-area {
  padding: 12px 18px 14px;
  border-top: 1px solid #f3f4f6;
}

.comment-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
  font-family: inherit;
  color: #1e1e2e;
  resize: vertical;
  min-height: 44px;
  line-height: 1.5;
  transition: border-color 0.15s;
}

.comment-textarea::placeholder {
  color: #9ca3af;
}

.comment-textarea:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.comment-input-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.comment-input-hint {
  font-size: 11px;
  color: #9ca3af;
}

.comment-submit-btn {
  padding: 6px 16px;
  background: #6366f1;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.comment-submit-btn:hover:not(:disabled) {
  background: #4f46e5;
}

.comment-submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
