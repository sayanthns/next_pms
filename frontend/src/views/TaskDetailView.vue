<template>
  <div class="task-detail">
    <!-- Loading State -->
    <div v-if="taskStore.loading && !taskStore.currentTask" class="loading-container">
      <div class="spinner"></div>
      <p class="loading-text">Loading task...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="!taskStore.currentTask" class="error-container">
      <p class="error-text">Task not found.</p>
      <button class="btn btn-primary" @click="loadTask">Retry</button>
    </div>

    <!-- Task Content -->
    <template v-else>
      <div class="task-content">
        <!-- Header -->
        <div class="task-header">
          <!-- Row 1: Priority badge + Status -->
          <div class="header-meta-row">
            <span
              class="priority-badge"
              :class="priorityClass(task.priority)"
            >
              {{ task.priority }}
            </span>
            <select
              class="status-select"
              :value="task.status"
              @change="onStatusChange($event)"
              :class="statusSelectClass(task.status)"
              :disabled="!canChangeStatus"
            >
              <option value="Backlog">Backlog</option>
              <option value="To Do">To Do</option>
              <option value="In Progress">In Progress</option>
              <option value="In Review">In Review</option>
              <option value="Done">Done</option>
              <option value="Cancelled">Cancelled</option>
            </select>
          </div>

          <!-- Row 2: Task Title -->
          <h1 class="task-title">{{ task.task_title }}</h1>

          <!-- Row 3: Action Buttons -->
          <div class="header-actions">
            <button
              v-if="canChangeStatus && task.status !== 'Done'"
              class="btn btn-success"
              @click="markAsDone"
              :disabled="markingDone"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              Mark as Done
            </button>
            <button
              v-if="canEditTask"
              class="btn btn-outline"
              @click="isEditing = !isEditing"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              {{ isEditing ? 'Cancel Edit' : 'Edit Task' }}
            </button>
            <button
              v-if="canDeleteTask"
              class="btn btn-danger-outline"
              @click="handleDeleteTask"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              Delete
            </button>
          </div>

          <!-- Inline Edit Form -->
          <div v-if="isEditing" class="edit-form">
            <div class="edit-form-grid">
              <div class="edit-field">
                <label class="edit-label">Task Title</label>
                <input v-model="editForm.task_title" class="edit-input" />
              </div>
              <div class="edit-field">
                <label class="edit-label">Priority</label>
                <select v-model="editForm.priority" class="edit-input">
                  <option value="Urgent">Urgent</option>
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                </select>
              </div>
              <div class="edit-field">
                <label class="edit-label">Due Date</label>
                <input v-model="editForm.due_date" type="date" class="edit-input" />
              </div>
              <div class="edit-field">
                <label class="edit-label">Estimated Hours</label>
                <input v-model.number="editForm.estimated_hours" type="number" step="0.5" min="0" class="edit-input" />
              </div>
              <div class="edit-field">
                <label class="edit-label">Task Type</label>
                <select v-model="editForm.task_type" class="edit-input">
                  <option value="">None</option>
                  <option value="Feature">Feature</option>
                  <option value="Bug">Bug</option>
                  <option value="Improvement">Improvement</option>
                  <option value="Research">Research</option>
                  <option value="Documentation">Documentation</option>
                  <option value="Meeting">Meeting</option>
                  <option value="Bench Task">Bench Task</option>
                  <option value="R&D Task">R&amp;D Task</option>
                  <option value="Support">Support</option>
                  <option value="Support Ticket">Support Ticket</option>
                </select>
              </div>
              <div class="edit-field" v-if="editSprints.length">
                <label class="edit-label">Sprint</label>
                <select v-model="editForm.sprint" class="edit-input">
                  <option value="">No Sprint</option>
                  <option v-for="s in editSprints" :key="s.name" :value="s.name">{{ s.sprint_name }}</option>
                </select>
              </div>
              <div class="edit-field">
                <label class="edit-label">Reviewer</label>
                <select v-model="editForm.reviewer" class="edit-input">
                  <option value="">None</option>
                  <option v-for="u in editTeamMembers" :key="u.name" :value="u.name">{{ u.full_name || u.name }}</option>
                </select>
              </div>
              <div class="edit-field" v-if="settingsStore.canViewFinance">
                <label class="edit-label">Billable</label>
                <select v-model="editForm.is_billable" class="edit-input">
                  <option :value="1">Yes</option>
                  <option :value="0">No</option>
                </select>
              </div>
              <div class="edit-field edit-field-wide">
                <label class="edit-label">Description</label>
                <RichTextEditor v-model="editForm.description" />
              </div>
            </div>
            <div class="edit-actions">
              <button class="btn btn-primary" @click="saveEdit" :disabled="savingEdit">
                {{ savingEdit ? 'Saving...' : 'Save Changes' }}
              </button>
              <button class="btn btn-outline" @click="isEditing = false">Cancel</button>
            </div>
          </div>
        </div>

        <!-- Timer -->
        <div class="timer-section">
          <Timer :taskName="task.name" :taskTitle="task.task_title" @timerStopped="onTimerStopped" @timerStarted="onTimerStarted" />
        </div>

        <!-- Info Grid -->
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">Project</span>
            <router-link
              v-if="task.project"
              :to="`/project/${task.project}`"
              class="info-link"
            >
              {{ task.project }}
            </router-link>
            <span v-else class="info-value">-</span>
          </div>
          <div class="info-item">
            <span class="info-label">Sprint</span>
            <span class="info-value">{{ task.sprint || '-' }}</span>
          </div>
          <div class="info-item" v-if="task.reviewer">
            <span class="info-label">Reviewer</span>
            <span class="info-value">{{ task.reviewer }}</span>
          </div>
          <div class="info-item info-item-wide">
            <div class="info-label-row">
              <span class="info-label">Assignees</span>
              <button
                v-if="!isEditingAssignees && (settingsStore.isAdmin || settingsStore.isManager)"
                class="assignee-edit-btn"
                @click="startEditAssignees"
                title="Edit Assignees"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                Edit
              </button>
            </div>

            <!-- View Mode -->
            <template v-if="!isEditingAssignees">
              <div v-if="taskAssignees.length" class="assignee-list-detail">
                <div v-for="a in taskAssignees" :key="a.user" class="assignee-row-detail">
                  <span class="assignee-avatar-detail">{{ getInitials(a.full_name || a.user) }}</span>
                  <span class="assignee-name-detail">{{ a.full_name || a.user }}</span>
                </div>
              </div>
              <span v-else class="info-value">No assignees</span>
            </template>

            <!-- Edit Mode -->
            <div v-else class="assignee-editor">
              <!-- Selected assignees -->
              <div v-if="selectedAssignees.length" class="ae-selected">
                <div v-for="user in selectedAssignees" :key="user.user" class="ae-chip">
                  <span class="ae-chip-avatar">{{ getInitials(user.full_name || user.user) }}</span>
                  <span class="ae-chip-name">{{ user.full_name || user.user }}</span>
                  <button type="button" class="ae-chip-remove" @click="removeAssigneeFromEdit(user.user)">&times;</button>
                </div>
              </div>
              <div v-else class="ae-empty-msg">No assignees selected</div>

              <!-- Search & dropdown -->
              <div class="ae-search-wrap">
                <input
                  v-model="assigneeSearch"
                  type="text"
                  class="ae-search-input"
                  placeholder="Search team members..."
                  @focus="showAssigneeDropdown = true"
                  @input="showAssigneeDropdown = true"
                />
                <div v-if="showAssigneeDropdown && filteredAssigneeUsers.length" class="ae-dropdown">
                  <div
                    v-for="user in filteredAssigneeUsers"
                    :key="user.user"
                    class="ae-option"
                    :class="{ selected: isAssigneeSelected(user.user) }"
                    @mousedown.prevent="toggleAssigneeInEdit(user)"
                  >
                    <span class="ae-option-avatar">{{ getInitials(user.full_name || user.user) }}</span>
                    <div class="ae-option-info">
                      <span class="ae-option-name">{{ user.full_name || user.user }}</span>
                      <span class="ae-option-email">{{ user.user }}</span>
                    </div>
                    <span v-if="isAssigneeSelected(user.user)" class="ae-option-check">✓</span>
                  </div>
                </div>
                <div v-if="showAssigneeDropdown && !filteredAssigneeUsers.length && assigneeSearch" class="ae-dropdown">
                  <div class="ae-option-empty">No users found</div>
                </div>
              </div>

              <!-- Save / Cancel -->
              <div class="ae-actions">
                <button class="btn btn-primary btn-sm" @click="saveAssignees" :disabled="savingAssignees">
                  {{ savingAssignees ? 'Saving...' : 'Save' }}
                </button>
                <button class="btn btn-outline btn-sm" @click="cancelEditAssignees">Cancel</button>
              </div>
            </div>
          </div>
          <div class="info-item">
            <span class="info-label">Task Type</span>
            <span class="info-value">{{ task.task_type || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Due Date</span>
            <span class="info-value" :class="{ overdue: isOverdue }">
              {{ formatDate(task.due_date) || '-' }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">Estimated Hours</span>
            <span class="info-value">{{ task.estimated_hours || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Actual Hours</span>
            <span class="info-value">{{ task.actual_hours || '-' }}</span>
          </div>
          <div class="info-item" v-if="overtimeData && overtimeData.overtime_hours > 0">
            <span class="info-label">Overtime (After Due Date)</span>
            <span class="info-value overtime-value">{{ overtimeData.overtime_hours }}h</span>
          </div>
        </div>

        <!-- Cost Section (hidden from developers) -->
        <div class="section-card" v-if="settingsStore.canViewFinance && (task.hourly_rate || task.calculated_cost)">
          <h3 class="section-title">Cost Information</h3>
          <div class="cost-grid">
            <div class="cost-item">
              <span class="cost-label">Hourly Rate</span>
              <span class="cost-value">{{ formatCurrency(task.hourly_rate) }}</span>
            </div>
            <div class="cost-item">
              <span class="cost-label">Calculated Cost</span>
              <span class="cost-value">{{ formatCurrency(task.calculated_cost) }}</span>
            </div>
            <div class="cost-item">
              <span class="cost-label">Billable</span>
              <span class="cost-value">
                <span
                  class="billable-badge"
                  :class="task.is_billable ? 'billable-yes' : 'billable-no'"
                >
                  {{ task.is_billable ? 'Yes' : 'No' }}
                </span>
              </span>
            </div>
          </div>
        </div>

        <!-- Description -->
        <div class="section-card" v-if="task.description">
          <h3 class="section-title">Description</h3>
          <div class="description-content" v-html="task.description"></div>
        </div>

        <!-- Subtasks -->
        <div class="section-card" v-if="subtasks.length">
          <h3 class="section-title">Subtasks ({{ subtasks.length }})</h3>
          <div class="subtask-list">
            <router-link
              v-for="sub in subtasks"
              :key="sub.name"
              :to="`/task/${sub.name}`"
              class="subtask-row"
            >
              <span
                class="priority-dot"
                :class="priorityDotClass(sub.priority)"
              ></span>
              <span class="subtask-title">{{ sub.task_title }}</span>
              <span
                class="status-badge status-badge-sm"
                :class="statusBadgeClass(sub.status)"
              >
                {{ sub.status }}
              </span>
            </router-link>
          </div>
        </div>

        <!-- Time Logs -->
        <div class="section-card">
          <h3 class="section-title">Time Logs</h3>
          <div v-if="timeLogsLoading" class="section-loading">
            <div class="spinner-sm"></div>
          </div>
          <div v-else-if="sortedTimeLogs.length" class="time-log-table-wrap">
            <table class="time-log-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Start</th>
                  <th>End</th>
                  <th>Duration</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="log in sortedTimeLogs" :key="log.name" :class="{ 'time-log-running': log.is_running }">
                  <td>{{ log.user }}</td>
                  <td>{{ formatDateTime(log.start_time) }}</td>
                  <td>
                    <span v-if="log.end_time">{{ formatDateTime(log.end_time) }}</span>
                    <span v-else-if="log.is_running" class="running-badge">
                      <span class="running-dot"></span> Running
                    </span>
                    <span v-else>-</span>
                  </td>
                  <td>
                    <span v-if="log.is_running && log.elapsed_seconds != null" class="running-elapsed">
                      {{ liveElapsedSeconds(log.elapsed_seconds) }}
                    </span>
                    <span v-else-if="log.is_running" class="running-elapsed">● Running</span>
                    <span v-else-if="log.duration_hours || log.duration_minutes">
                      {{ log.duration_hours || 0 }}h {{ log.duration_minutes || 0 }}m
                    </span>
                    <span v-else>-</span>
                  </td>
                  <td>{{ log.notes || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="no-data-text">No time logs recorded.</p>
        </div>

        <!-- Attachments -->
        <div class="section-card">
          <div class="section-header-row">
            <h3 class="section-title" style="margin-bottom:0">Attachments</h3>
            <div class="attach-btn-group">
              <label class="btn btn-sm btn-outline upload-btn">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
                File
                <input type="file" multiple @change="handleAttachmentUpload" class="file-input-hidden" ref="attachInputRef" />
              </label>
              <button class="btn btn-sm btn-outline" @click="showLinkForm = !showLinkForm">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
                Link
              </button>
            </div>
          </div>

          <!-- Add link form -->
          <div v-if="showLinkForm" class="link-form">
            <input
              v-model="linkUrl"
              class="link-form-input"
              placeholder="https://..."
              type="url"
              @keydown.enter="saveLink"
            />
            <input
              v-model="linkTitle"
              class="link-form-input"
              placeholder="Title (optional)"
              @keydown.enter="saveLink"
            />
            <div class="link-form-actions">
              <button class="btn btn-sm btn-primary" :disabled="!linkUrl.trim() || savingLink" @click="saveLink">
                {{ savingLink ? 'Saving...' : 'Save' }}
              </button>
              <button class="btn btn-sm btn-outline" @click="showLinkForm = false; linkUrl = ''; linkTitle = ''">Cancel</button>
            </div>
          </div>

          <div v-if="attachmentsLoading" class="section-loading">
            <div class="spinner-sm"></div>
          </div>
          <div v-else-if="attachments.length || linkAttachments.length" class="attachment-list">
            <!-- Link attachments -->
            <div v-for="link in linkAttachments" :key="'link-' + link.name" class="attachment-item">
              <div class="attachment-icon attachment-icon-link">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
              </div>
              <div class="attachment-info">
                <a :href="link.url" target="_blank" rel="noopener" class="attachment-name">{{ link.title || link.url }}</a>
                <span class="attachment-meta">
                  {{ link.added_by_name }} &middot; {{ formatDate(link.creation) }}
                </span>
              </div>
              <div class="attachment-actions">
                <button class="attach-action-btn attach-delete" @click="deleteLinkAttachment(link.name)" title="Delete">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </div>
            </div>
            <!-- File attachments -->
            <div v-for="file in attachments" :key="file.name" class="attachment-item">
              <div class="attachment-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              </div>
              <div class="attachment-info">
                <a :href="file.file_url" target="_blank" class="attachment-name">{{ file.file_name }}</a>
                <span class="attachment-meta">
                  {{ formatFileSize(file.file_size) }} &middot; {{ file.uploaded_by }} &middot; {{ formatDate(file.creation) }}
                </span>
              </div>
              <div class="attachment-actions">
                <a :href="file.file_url" :download="file.file_name" class="attach-action-btn" title="Download">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                </a>
                <button class="attach-action-btn attach-delete" @click="deleteAttachment(file.name)" title="Delete">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </div>
            </div>
          </div>
          <div v-else class="no-data-text">No attachments yet.</div>
          <div v-if="uploadingAttachment" class="upload-progress-bar">
            <div class="upload-progress-info">
              <svg class="upload-spin-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4m-3.93 7.07l-2.83-2.83M7.76 7.76L4.93 4.93"/></svg>
              <span>Uploading... {{ uploadProgress }}%</span>
            </div>
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
            </div>
          </div>
        </div>

        <!-- Toast -->
        <Transition name="toast">
          <div v-if="toast.show" class="toast" :class="'toast-' + toast.type">
            {{ toast.message }}
          </div>
        </Transition>

        <!-- Comments -->
        <div class="section-card">
          <h3 class="section-title">Comments</h3>
          <CommentThread :taskName="task.name" :projectName="task.project" />
        </div>

        <!-- Activity Log -->
        <div class="section-card">
          <h3 class="section-title">Activity Log</h3>
          <div v-if="activityLoading" class="section-loading">
            <div class="spinner-sm"></div>
          </div>
          <div v-else-if="activityLog.length" class="activity-list">
            <div v-for="(act, idx) in activityLog" :key="idx" class="activity-item">
              <div class="activity-icon" :class="activityIconClass(act.type)">
                <svg v-if="act.type === 'created'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
                <svg v-else-if="act.type === 'status_change'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
              </div>
              <div class="activity-content">
                <span class="activity-user">{{ act.user_name }}</span>
                <span class="activity-detail">{{ act.detail }}</span>
                <span class="activity-time">{{ formatDateTime(act.timestamp) }}</span>
              </div>
            </div>
          </div>
          <p v-else class="no-data-text">No activity recorded.</p>
        </div>
      </div>
    </template>

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :show="showDeleteTaskConfirm"
      title="Delete Task"
      :message="deleteTaskMessage"
      :details="deleteTaskDetails"
      confirmLabel="Delete Task"
      :confirmDanger="true"
      :loading="deletingTask"
      @confirm="confirmDeleteTask"
      @cancel="showDeleteTaskConfirm = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/store/tasks'
import { useSettingsStore } from '@/store/settings'
import { useTimerStore } from '@/store/timer'
import { getList, call } from '@/utils/frappe'
import { useRealtime } from '@/utils/realtime'
import { eventBus, EVENTS } from '@/utils/eventBus'
import Timer from '@/components/Timer.vue'
import CommentThread from '@/components/CommentThread.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import RichTextEditor from '@/components/RichTextEditor.vue'

const props = defineProps({
  id: {
    type: String,
    required: true,
  },
})

const router = useRouter()
const taskStore = useTaskStore()
const settingsStore = useSettingsStore()
const timerStore = useTimerStore()

const timeLogs = ref([])
const timeLogsLoading = ref(false)
const nowTick = ref(Date.now())
const logsFetchedAt = ref(Date.now())
let tickInterval = null

// Sorted time logs: running first, then by start_time desc
const sortedTimeLogs = computed(() => {
  return [...timeLogs.value].sort((a, b) => {
    if (a.is_running && !b.is_running) return -1
    if (!a.is_running && b.is_running) return 1
    return 0 // keep original server order (start_time desc)
  })
})

// Timezone-safe live elapsed: uses server-provided elapsed_seconds + local tick offset
function liveElapsedSeconds(baseElapsed) {
  if (baseElapsed == null) return '00:00:00'
  const extra = Math.max(0, Math.floor((nowTick.value - logsFetchedAt.value) / 1000))
  const total = Math.max(0, baseElapsed + extra)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
const subtasks = ref([])
const markingDone = ref(false)
const activityLog = ref([])
const activityLoading = ref(false)
const overtimeData = ref(null)

// Edit mode
const isEditing = ref(false)
const savingEdit = ref(false)
const editForm = reactive({
  task_title: '',
  priority: 'Medium',
  due_date: '',
  estimated_hours: 0,
  task_type: '',
  is_billable: 0,
  description: '',
  sprint: '',
  reviewer: '',
})
const editSprints = ref([])
const editTeamMembers = ref([])

// Delete task
const showDeleteTaskConfirm = ref(false)
const deletingTask = ref(false)
const deleteTaskMessage = ref('')
const deleteTaskDetails = ref([])

const currentUser = computed(() => window.frappe?.session?.user || window.pms_boot?.user || '')

const isAssignedToTask = computed(() => {
  if (!task.value) return false
  // Check legacy assigned_to
  if (task.value.assigned_to === currentUser.value) return true
  // Check assignees table
  const assignees = task.value.assignees || []
  return assignees.some(a => a.user === currentUser.value)
})

const canChangeStatus = computed(() => {
  if (settingsStore.isAdmin || settingsStore.isManager) return true
  if (!task.value) return false
  // Developers assigned to the task can change status
  if (isAssignedToTask.value) return true
  if (task.value.owner === currentUser.value) return true
  return false
})

const canEditTask = computed(() => {
  if (settingsStore.featurePermissions.edit_task === false) return false
  if (settingsStore.isAdmin) return true
  if (!task.value) return false
  if (task.value.owner === currentUser.value) return true
  if (isAssignedToTask.value) return true
  return settingsStore.isManager
})

const canDeleteTask = computed(() => {
  if (settingsStore.isAdmin) return true
  if (!task.value) return false
  if (task.value.owner === currentUser.value) return true
  return settingsStore.isManager
})

// Assignee editing
const isEditingAssignees = ref(false)
const savingAssignees = ref(false)
const availableAssigneeUsers = ref([])
const selectedAssignees = ref([])
const assigneeSearch = ref('')
const showAssigneeDropdown = ref(false)

// Attachments
const attachments = ref([])
const attachmentsLoading = ref(false)
const uploadingAttachment = ref(false)
const uploadProgress = ref(0)
const attachInputRef = ref(null)

// Link attachments
const linkAttachments = ref([])
const showLinkForm = ref(false)
const linkUrl = ref('')
const linkTitle = ref('')
const savingLink = ref(false)

// Toast
const toast = ref({ show: false, message: '', type: 'success' })
function showToast(message, type = 'success') {
  toast.value = { show: true, message, type }
  setTimeout(() => { toast.value.show = false }, 3000)
}

const task = computed(() => taskStore.currentTask)

const isOverdue = computed(() => {
  if (!task.value || !task.value.due_date || task.value.status === 'Done') return false
  return new Date(task.value.due_date) < new Date()
})

const taskAssignees = computed(() => {
  if (!task.value) return []
  if (task.value.assignees && task.value.assignees.length) {
    return task.value.assignees
  }
  if (task.value.assigned_to) {
    return [{ user: task.value.assigned_to, full_name: task.value.assigned_to }]
  }
  return []
})

function getInitials(name) {
  if (!name) return '?'
  const parts = name.split(/[\s@.]+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}

// Assignee editor helpers
const filteredAssigneeUsers = computed(() => {
  const search = assigneeSearch.value.toLowerCase()
  return availableAssigneeUsers.value.filter(u => {
    const name = (u.full_name || '').toLowerCase()
    const email = (u.user || '').toLowerCase()
    return name.includes(search) || email.includes(search)
  })
})

function isAssigneeSelected(userId) {
  return selectedAssignees.value.some(a => a.user === userId)
}

function toggleAssigneeInEdit(user) {
  if (isAssigneeSelected(user.user)) {
    removeAssigneeFromEdit(user.user)
  } else {
    selectedAssignees.value.push(user)
  }
}

function removeAssigneeFromEdit(userId) {
  selectedAssignees.value = selectedAssignees.value.filter(a => a.user !== userId)
}

async function loadAssigneeUsers() {
  try {
    // Try project members first
    if (task.value && task.value.project) {
      const members = await call('next_pms.api.crud.get_project_members', {
        project: task.value.project,
      })
      if (members && members.length) {
        availableAssigneeUsers.value = members
        return
      }
    }
    // Fallback to all users
    const allUsers = await call('next_pms.api.crud.get_all_users')
    availableAssigneeUsers.value = (allUsers || []).map(u => ({
      user: u.name,
      full_name: u.full_name,
      user_image: u.user_image,
    }))
  } catch (e) {
    console.error('Failed to load users for assignee editor:', e)
    availableAssigneeUsers.value = []
  }
}

function startEditAssignees() {
  // Copy current assignees to selection
  selectedAssignees.value = taskAssignees.value.map(a => ({ ...a }))
  assigneeSearch.value = ''
  showAssigneeDropdown.value = false
  isEditingAssignees.value = true
  loadAssigneeUsers()
  // Close dropdown on outside click
  setTimeout(() => {
    document.addEventListener('click', handleAssigneeOutsideClick)
  }, 0)
}

function cancelEditAssignees() {
  isEditingAssignees.value = false
  assigneeSearch.value = ''
  showAssigneeDropdown.value = false
  document.removeEventListener('click', handleAssigneeOutsideClick)
}

function handleAssigneeOutsideClick(e) {
  if (!e.target.closest('.ae-search-wrap')) {
    showAssigneeDropdown.value = false
  }
}

async function saveAssignees() {
  savingAssignees.value = true
  try {
    const emails = selectedAssignees.value.map(a => a.user)
    await taskStore.updateTaskAssignees(props.id, emails)
    // Refresh task to get updated assignees
    await taskStore.fetchTask(props.id)
    isEditingAssignees.value = false
    document.removeEventListener('click', handleAssigneeOutsideClick)
  } catch (err) {
    console.error('Failed to save assignees:', err)
    alert('Failed to save assignees. Please try again.')
  } finally {
    savingAssignees.value = false
  }
}

// Delete task handlers
async function handleDeleteTask() {
  try {
    const preview = await call('next_pms.api.crud.get_delete_preview', {
      doctype: 'PMS Task',
      name: props.id,
    })
    deleteTaskMessage.value = 'This will permanently delete this task and all associated data. This action cannot be undone.'
    deleteTaskDetails.value = []
    if (preview.timelogs) deleteTaskDetails.value.push(`${preview.timelogs} time log(s)`)
    if (preview.comments) deleteTaskDetails.value.push(`${preview.comments} comment(s)`)
    if (preview.files) deleteTaskDetails.value.push(`${preview.files} file(s)`)
    showDeleteTaskConfirm.value = true
  } catch (e) {
    console.error('Failed to get delete preview:', e)
    alert('Failed to check task dependencies.')
  }
}

async function confirmDeleteTask() {
  deletingTask.value = true
  try {
    await call('next_pms.api.crud.delete_task', { task: props.id })
    showDeleteTaskConfirm.value = false
    // Navigate to project if we know it, otherwise to home
    if (task.value && task.value.project) {
      router.push(`/project/${task.value.project}`)
    } else {
      router.push('/')
    }
  } catch (e) {
    console.error('Failed to delete task:', e)
    alert('Failed to delete task. Please try again.')
  } finally {
    deletingTask.value = false
  }
}

// Real-time: refresh task when it's updated by another user (via Socket.IO)
useRealtime('task_updated', (data) => {
  if (data?.task === props.id) loadTask()
})

// Local event bus: refresh activity log when current user changes status/task
function onLocalTaskChange(data) {
  if (data?.task === props.id) {
    // Reload activity log after a short delay to let the Version record be created
    setTimeout(() => loadActivityLog(), 500)
  }
}

onMounted(() => {
  loadTask()
  // Join the project room for realtime updates once task is loaded
  eventBus.on(EVENTS.TASK_STATUS_CHANGED, onLocalTaskChange)
  eventBus.on(EVENTS.TASK_UPDATED, onLocalTaskChange)
  // Tick every second for live running timer display
  tickInterval = setInterval(() => { nowTick.value = Date.now() }, 1000)
  // Auto-reload time logs when any timer stops
  eventBus.on(EVENTS.TIMER_STOPPED, onTimerEvent)
})

onUnmounted(() => {
  document.removeEventListener('click', handleAssigneeOutsideClick)
  eventBus.off(EVENTS.TASK_STATUS_CHANGED, onLocalTaskChange)
  eventBus.off(EVENTS.TASK_UPDATED, onLocalTaskChange)
  eventBus.off(EVENTS.TIMER_STOPPED, onTimerEvent)
  if (tickInterval) clearInterval(tickInterval)
})

function onTimerEvent() {
  loadTimeLogs()
}

watch(() => props.id, () => {
  loadTask()
})

async function loadTask() {
  await taskStore.fetchTask(props.id)
  // Load time logs, subtasks, attachments, links, activity, overtime in parallel
  loadTimeLogs()
  loadSubtasks()
  loadAttachments()
  loadLinkAttachments()
  loadActivityLog()
  loadOvertimeHours()
}

async function loadActivityLog() {
  activityLoading.value = true
  try {
    activityLog.value = await call('next_pms.api.crud.get_task_activity', { task: props.id })
  } catch {
    activityLog.value = []
  } finally {
    activityLoading.value = false
  }
}

async function loadOvertimeHours() {
  try {
    overtimeData.value = await call('next_pms.api.crud.get_task_overtime_hours', { task: props.id })
  } catch {
    overtimeData.value = null
  }
}

function activityIconClass(type) {
  return {
    'activity-icon-created': type === 'created',
    'activity-icon-status': type === 'status_change',
    'activity-icon-assign': type === 'assignment',
    'activity-icon-other': !['created', 'status_change', 'assignment'].includes(type),
  }
}

async function loadTimeLogs() {
  timeLogsLoading.value = true
  try {
    timeLogs.value = await call('next_pms.api.timer.get_task_timelogs', { task: props.id })
    logsFetchedAt.value = Date.now()
  } catch {
    timeLogs.value = []
  } finally {
    timeLogsLoading.value = false
  }
}

async function loadSubtasks() {
  try {
    subtasks.value = await getList('PMS Task', {
      fields: ['name', 'task_title', 'status', 'priority', 'assigned_to'],
      filters: { parent_task: props.id },
      orderBy: 'priority desc, modified desc',
      limit: 0,
    })
  } catch {
    subtasks.value = []
  }
}

async function onStatusChange(event) {
  const newStatus = event.target.value
  const oldStatus = task.value?.status
  const success = await taskStore.updateTaskStatus(props.id, newStatus)
  if (!success) {
    // Revert select to old value if API failed
    event.target.value = oldStatus
  } else {
    // Re-fetch task to ensure full sync
    await taskStore.fetchTask(props.id)
  }
}

async function onTimerStarted() {
  // Refresh time logs to show the new running entry
  loadTimeLogs()
}

async function onTimerStopped() {
  // Refresh time logs and task data (actual_hours may have updated)
  loadTimeLogs()
  taskStore.fetchTask(props.id)
}

async function markAsDone() {
  markingDone.value = true
  try {
    await taskStore.updateTaskStatus(props.id, 'Done')
  } finally {
    markingDone.value = false
  }
}

// Edit form
watch(isEditing, async (val) => {
  if (val && task.value) {
    editForm.task_title = task.value.task_title || ''
    editForm.priority = task.value.priority || 'Medium'
    editForm.due_date = task.value.due_date || ''
    editForm.estimated_hours = task.value.estimated_hours || 0
    editForm.task_type = task.value.task_type || ''
    editForm.is_billable = task.value.is_billable ? 1 : 0
    editForm.description = task.value.description || ''
    editForm.sprint = task.value.sprint || ''
    editForm.reviewer = task.value.reviewer || ''
    // Load sprints and team members for this project
    if (task.value.project) {
      try {
        editSprints.value = await getList('PMS Sprint', {
          fields: ['name', 'sprint_name'],
          filters: { project: task.value.project },
          orderBy: 'start_date desc',
          limit: 0,
        })
      } catch { editSprints.value = [] }
      try {
        editTeamMembers.value = await call('next_pms.api.crud.get_all_users')
      } catch { editTeamMembers.value = [] }
    }
  }
})

async function saveEdit() {
  savingEdit.value = true
  try {
    const csrf = document.cookie.split('; ').find(r => r.startsWith('csrf_token='))?.split('=')[1]
      || window.pms_boot?.csrf_token || ''
    const response = await fetch(`/api/resource/PMS Task/${encodeURIComponent(props.id)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Frappe-CSRF-Token': csrf,
      },
      credentials: 'include',
      body: JSON.stringify({
        task_title: editForm.task_title,
        priority: editForm.priority,
        due_date: editForm.due_date || null,
        estimated_hours: editForm.estimated_hours || 0,
        task_type: editForm.task_type || null,
        sprint: editForm.sprint || null,
        reviewer: editForm.reviewer || null,
        is_billable: editForm.is_billable,
        description: editForm.description || '',
      }),
    })
    if (!response.ok) throw new Error('Failed to save')
    isEditing.value = false
    await taskStore.fetchTask(props.id)
  } catch (err) {
    console.error('Failed to save task:', err)
    alert('Failed to save task. Please try again.')
  } finally {
    savingEdit.value = false
  }
}

// Attachments
async function loadAttachments() {
  attachmentsLoading.value = true
  try {
    attachments.value = await call('next_pms.api.files.get_task_files', { task: props.id })
  } catch {
    attachments.value = []
  } finally {
    attachmentsLoading.value = false
  }
}

function uploadFileWithProgress(formData, csrf) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/api/method/upload_file')
    if (csrf) xhr.setRequestHeader('X-Frappe-CSRF-Token', csrf)
    xhr.withCredentials = true
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        uploadProgress.value = Math.round((e.loaded / e.total) * 100)
      }
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try { resolve(JSON.parse(xhr.responseText)) } catch { resolve(null) }
      } else {
        reject(new Error(`Upload failed: ${xhr.status}`))
      }
    }
    xhr.onerror = () => reject(new Error('Network error'))
    xhr.send(formData)
  })
}

async function handleAttachmentUpload(event) {
  const files = event.target.files
  if (!files || !files.length) return

  uploadingAttachment.value = true
  uploadProgress.value = 0
  const csrf = document.cookie.split('; ').find(r => r.startsWith('csrf_token='))?.split('=')[1]
    || window.pms_boot?.csrf_token || ''

  let uploadedCount = 0
  try {
    for (const file of files) {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('doctype', 'PMS Task')
      formData.append('docname', props.id)
      formData.append('is_private', '1')

      const result = await uploadFileWithProgress(formData, csrf)
      const fileData = result?.message
      if (fileData) {
        attachments.value.unshift({
          name: fileData.name,
          file_name: fileData.file_name,
          file_url: fileData.file_url,
          file_size: fileData.file_size,
          uploaded_by: fileData.owner || 'You',
          creation: new Date().toISOString(),
        })
        uploadedCount++
      }
    }
    if (uploadedCount) {
      showToast(`${uploadedCount} file${uploadedCount > 1 ? 's' : ''} uploaded successfully`)
    }
  } catch (err) {
    console.error('Upload failed:', err)
    showToast('Upload failed. Please try again.', 'error')
  } finally {
    uploadingAttachment.value = false
    uploadProgress.value = 0
    if (attachInputRef.value) attachInputRef.value.value = ''
  }
}

async function deleteAttachment(fileName) {
  if (!confirm('Delete this attachment?')) return
  try {
    await call('next_pms.api.files.delete_task_file', { file_name: fileName })
    await loadAttachments()
  } catch (err) {
    console.error('Delete failed:', err)
  }
}

// Link attachments
async function loadLinkAttachments() {
  try {
    linkAttachments.value = await call('next_pms.api.files.get_task_links', { task: props.id })
  } catch {
    linkAttachments.value = []
  }
}

async function saveLink() {
  const url = linkUrl.value.trim()
  if (!url || savingLink.value) return

  savingLink.value = true
  try {
    const args = { task: props.id, url: url }
    const t = linkTitle.value.trim()
    if (t) args.title = t
    const result = await call('next_pms.api.files.save_task_link', args)
    if (result) {
      linkAttachments.value.unshift(result)
    }
    linkUrl.value = ''
    linkTitle.value = ''
    showLinkForm.value = false
    showToast('Link added successfully')
  } catch (err) {
    console.error('Failed to save link:', err)
    showToast('Failed to save link', 'error')
  } finally {
    savingLink.value = false
  }
}

async function deleteLinkAttachment(name) {
  if (!confirm('Delete this link?')) return
  try {
    await call('next_pms.api.files.delete_task_link', { name })
    linkAttachments.value = linkAttachments.value.filter(l => l.name !== name)
    showToast('Link deleted')
  } catch (err) {
    console.error('Delete link failed:', err)
  }
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatCurrency(value) {
  return settingsStore.formatCurrency(value)
}

function priorityClass(priority) {
  const map = {
    'Urgent': 'priority-urgent',
    'High': 'priority-high',
    'Medium': 'priority-medium',
    'Low': 'priority-low',
  }
  return map[priority] || 'priority-low'
}

function priorityDotClass(priority) {
  const map = {
    'Urgent': 'dot-urgent',
    'High': 'dot-high',
    'Medium': 'dot-medium',
    'Low': 'dot-low',
  }
  return map[priority] || 'dot-low'
}

function statusBadgeClass(status) {
  const map = {
    'Backlog': 'badge-default',
    'To Do': 'badge-primary',
    'In Progress': 'badge-warning',
    'In Review': 'badge-info',
    'Done': 'badge-success',
    'Cancelled': 'badge-danger',
  }
  return map[status] || 'badge-default'
}

function statusSelectClass(status) {
  const map = {
    'Backlog': 'select-default',
    'To Do': 'select-primary',
    'In Progress': 'select-warning',
    'In Review': 'select-info',
    'Done': 'select-success',
    'Cancelled': 'select-danger',
  }
  return map[status] || 'select-default'
}
</script>

<style scoped>
.task-detail {
  padding: 16px 0;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner-sm {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 16px;
  color: var(--text-secondary);
  font-size: 14px;
}

.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 0;
}

.error-text {
  color: var(--color-danger);
  font-size: 14px;
  margin-bottom: 16px;
}

.task-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Header */
.task-header {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.header-meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.priority-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex-shrink: 0;
  margin-top: 4px;
}

.priority-urgent {
  background: rgba(239, 68, 68, 0.1);
  color: #EF4444;
}

.priority-high {
  background: rgba(245, 158, 11, 0.1);
  color: #F59E0B;
}

.priority-medium {
  background: rgba(251, 191, 36, 0.1);
  color: #FBBF24;
}

.priority-low {
  background: var(--bg-surface-hover);
  color: var(--text-secondary);
}

.task-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.3;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  white-space: nowrap;
}

.btn-primary {
  background: #2563EB;
  color: #fff;
}

.btn-primary:hover {
  background: #1D4ED8;
}

.btn-success {
  background: #10b981;
  color: #fff;
}

.btn-success:hover {
  background: #059669;
}

.btn-success:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-outline {
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.btn-outline:hover {
  background: var(--bg-surface-active);
  border-color: var(--text-tertiary);
}

.btn-danger-outline {
  background: var(--bg-surface);
  color: #EF4444;
  border: 1px solid #fecaca;
}

.btn-danger-outline:hover {
  background: #fef2f2;
  border-color: #EF4444;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.status-select {
  padding: 6px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  outline: none;
  transition: all 0.2s ease;
  appearance: auto;
}

.select-primary { color: #2563EB; border-color: rgba(37, 99, 235, 0.3); }
.select-success { color: #10b981; border-color: rgba(16, 185, 129, 0.3); }
.select-warning { color: #F59E0B; border-color: rgba(245, 158, 11, 0.3); }
.select-info { color: #3b82f6; border-color: rgba(59, 130, 246, 0.3); }
.select-danger { color: #EF4444; border-color: rgba(239, 68, 68, 0.3); }
.select-default { color: var(--text-secondary); border-color: var(--border-default); }

/* Timer */
.timer-section {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 16px 20px;
}

/* Info Grid */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1px;
  background: var(--border-default);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  overflow: hidden;
}

.info-item {
  background: var(--bg-surface);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.info-value.overdue {
  color: var(--color-danger);
}

.info-link {
  font-size: 14px;
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 500;
}

.info-link:hover {
  text-decoration: underline;
}

/* Section Cards */
.section-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 16px 0;
}

.section-loading {
  display: flex;
  justify-content: center;
  padding: 24px;
}

/* Cost Grid */
.cost-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.cost-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cost-label {
  font-size: 12px;
  color: var(--text-tertiary);
  font-weight: 500;
}

.cost-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.billable-badge {
  display: inline-flex;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.billable-yes {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.billable-no {
  background: var(--bg-surface-hover);
  color: var(--text-tertiary);
}

/* Description */
.description-content {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.7;
}

.description-content :deep(p) {
  margin: 0 0 12px 0;
}

.description-content :deep(ul),
.description-content :deep(ol) {
  padding-left: 20px;
  margin: 0 0 12px 0;
}

/* Subtasks */
.subtask-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.subtask-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  text-decoration: none;
  transition: background 0.15s ease;
}

.subtask-row:hover {
  background: var(--bg-surface-active);
}

.priority-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-urgent { background: #EF4444; }
.dot-high { background: #F59E0B; }
.dot-medium { background: #FBBF24; }
.dot-low { background: var(--text-tertiary); }

.subtask-title {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.status-badge-sm {
  padding: 2px 8px;
  font-size: 10px;
}

.badge-primary { background: rgba(37, 99, 235, 0.1); color: #2563EB; }
.badge-success { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.badge-warning { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
.badge-info { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.badge-danger { background: rgba(239, 68, 68, 0.1); color: #EF4444; }
.badge-default { background: var(--bg-surface-hover); color: var(--text-secondary); }

/* Time Log Table */
.time-log-table-wrap {
  overflow-x: auto;
}

.time-log-table {
  width: 100%;
  border-collapse: collapse;
}

.time-log-table thead {
  background: var(--bg-surface-active);
}

.time-log-table th {
  padding: 10px 14px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-default);
}

.time-log-table td {
  padding: 10px 14px;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-light);
}
.time-log-running {
  background: rgba(16, 185, 129, 0.06);
}
.running-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #10b981;
  font-weight: 500;
  font-size: 12px;
}
.running-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10b981;
  animation: pulse-green 2s infinite;
}
@keyframes pulse-green {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}
.running-elapsed {
  font-family: 'SF Mono', SFMono-Regular, Consolas, monospace;
  font-weight: 600;
  color: #10b981;
  font-size: 13px;
}

.no-data-text {
  color: var(--text-tertiary);
  font-size: 13px;
  text-align: center;
  padding: 16px 0;
  margin: 0;
}

/* Assignee list in detail view */
.info-item-wide {
  grid-column: 1 / -1;
}

.assignee-list-detail {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 2px;
}

.assignee-row-detail {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px 4px 4px;
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  border-radius: 20px;
}

.assignee-avatar-detail {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #2563EB;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.assignee-name-detail {
  font-size: 13px;
  font-weight: 500;
  color: #1e40af;
}

/* Inline Edit Form */
.edit-form {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-default);
}

.edit-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.edit-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.edit-field-wide {
  grid-column: 1 / -1;
}

.edit-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.edit-input {
  padding: 8px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-surface);
  transition: border-color 0.2s;
  outline: none;
}

.edit-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.edit-textarea {
  padding: 8px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-surface);
  resize: vertical;
  min-height: 80px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
}

.edit-textarea:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.edit-actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border-light);
}

/* Attachments */
.section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.btn-sm {
  padding: 5px 12px;
  font-size: 12px;
}

.attach-btn-group {
  display: flex;
  gap: 6px;
}

.upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
}

.file-input-hidden {
  display: none;
}

/* Link form */
.link-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: #f8fafc;
  border-bottom: 1px solid var(--border-light);
}

.link-form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  color: var(--text-primary);
}

.link-form-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-bg);
}

.link-form-actions {
  display: flex;
  gap: 8px;
}

.attachment-icon-link {
  background: rgba(37, 99, 235, 0.08) !important;
  color: #2563EB !important;
}

.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  transition: background 0.15s, border-color 0.15s;
}

.attachment-item:hover {
  background: var(--bg-surface-active);
  border-color: var(--border-default);
}

.attachment-icon {
  width: 36px;
  height: 36px;
  background: var(--bg-surface-hover);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.attachment-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.attachment-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.attachment-name:hover {
  color: var(--color-primary);
}

.attachment-meta {
  font-size: 11px;
  color: var(--text-tertiary);
}

.attachment-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.attach-action-btn {
  width: 28px;
  height: 28px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.15s;
}

.attach-action-btn:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.attach-delete:hover {
  background: #fef2f2;
  color: #ef4444;
  border-color: #fecaca;
}

.upload-progress-bar {
  padding: 12px 0 4px;
}
.upload-progress-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.upload-spin-icon {
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.progress-track {
  width: 100%;
  height: 6px;
  background: var(--bg-subtle, #e5e7eb);
  border-radius: 3px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--color-primary, #2563eb);
  border-radius: 3px;
  transition: width 0.2s ease;
}

/* Toast */
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  z-index: 9999;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.toast-success { background: var(--color-success, #10b981); }
.toast-error { background: var(--color-danger, #ef4444); }
.toast-enter-active { transition: all 0.3s ease; }
.toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from { opacity: 0; transform: translateY(10px); }
.toast-leave-to { opacity: 0; transform: translateY(10px); }

/* Assignee label row */
.info-label-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.assignee-edit-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  cursor: pointer;
  transition: all 0.15s;
}

.assignee-edit-btn:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
  border-color: var(--text-tertiary);
}

/* Assignee Editor */
.assignee-editor {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ae-selected {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ae-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px 4px 4px;
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  border-radius: 20px;
  font-size: 12px;
  color: #1e40af;
}

.ae-chip-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #2563EB;
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ae-chip-name {
  font-weight: 500;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ae-chip-remove {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
  padding: 0 2px;
  line-height: 1;
  display: flex;
  align-items: center;
}

.ae-chip-remove:hover {
  color: #EF4444;
}

.ae-empty-msg {
  font-size: 13px;
  color: var(--text-tertiary);
}

.ae-search-wrap {
  position: relative;
}

.ae-search-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-surface);
  outline: none;
  transition: border-color 0.2s;
}

.ae-search-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.ae-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: 200px;
  overflow-y: auto;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 50;
  margin-top: 4px;
}

.ae-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background 0.1s;
}

.ae-option:hover {
  background: var(--bg-surface-active);
}

.ae-option.selected {
  background: #EFF6FF;
}

.ae-option-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #2563EB;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ae-option-info {
  flex: 1;
  min-width: 0;
}

.ae-option-name {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.ae-option-email {
  display: block;
  font-size: 11px;
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ae-option-check {
  color: var(--color-primary);
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}

.ae-option-empty {
  padding: 14px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
}

.ae-actions {
  display: flex;
  gap: 8px;
}

@media (max-width: 640px) {
  .task-header {
    padding: 16px;
    gap: 12px;
  }
  .task-title {
    font-size: 18px;
  }
  .header-actions {
    gap: 6px;
  }
  .header-actions .btn {
    font-size: 12px;
    padding: 6px 10px;
  }
  .edit-form-grid {
    grid-template-columns: 1fr;
  }
}

/* Activity Log */
.activity-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.activity-item {
  display: flex;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #f1f3f5;
  align-items: flex-start;
}
.activity-item:last-child { border-bottom: none; }
.activity-icon {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; margin-top: 2px;
}
.activity-icon-created { background: #dcfce7; color: #16a34a; }
.activity-icon-status { background: #dbeafe; color: #2563eb; }
.activity-icon-assign { background: #fef3c7; color: #d97706; }
.activity-icon-other { background: #f1f5f9; color: #64748b; }
.activity-content { display: flex; flex-wrap: wrap; gap: 4px; align-items: baseline; }
.activity-user { font-weight: 600; font-size: 13px; color: #1e293b; }
.activity-detail { font-size: 13px; color: #475569; }
.activity-time { font-size: 11px; color: #94a3b8; margin-left: 4px; }

/* Overtime */
.overtime-value { color: var(--color-danger-hover); font-weight: 600; }
</style>
