<template>
  <div class="project-detail">
    <!-- Loading -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p class="loading-text">Loading project...</p>
    </div>

    <template v-else-if="dashboard">
      <!-- Project Header -->
      <div class="project-header">
        <div class="header-top">
          <div class="header-left">
            <div class="project-title-row">
              <span class="project-color-bar" :style="{ background: statusBarColor }"></span>
              <h1 class="project-name">{{ dashboard.project_name }}</h1>
            </div>
            <p v-if="project?.description" class="project-desc">{{ stripHtml(project.description) }}</p>
            <div class="header-badges">
              <span class="badge-status" :class="'badge-' + statusKey(dashboard.status)">{{ dashboard.status }}</span>
            </div>
          </div>
          <div class="header-meta-right">
            <div v-if="project?.end_date" class="meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
              <span>Deadline: {{ formatDate(project.end_date) }}</span>
            </div>
            <div v-if="project?.start_date" class="meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              <span>Started: {{ formatDate(project.start_date) }}</span>
            </div>
            <div v-if="canModifyProject" class="header-action-btns">
              <button class="hdr-btn hdr-btn-edit" @click="showEditProject = true" title="Edit Project">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                Edit
              </button>
              <button class="hdr-btn hdr-btn-delete" @click="handleDeleteProject" title="Delete Project">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                Delete
              </button>
            </div>
          </div>
        </div>

        <!-- 4 KPI Summary Boxes -->
        <div class="kpi-row">
          <div class="kpi-box">
            <span class="kpi-title">Progress</span>
            <span class="kpi-value">{{ progressPct }}%</span>
            <span class="kpi-sub">{{ dashboard.task_counts?.Done || 0 }} of {{ dashboard.total_tasks }} tasks completed</span>
            <div class="kpi-bar"><div class="kpi-bar-fill" :style="{ width: progressPct + '%' }"></div></div>
          </div>
          <div v-if="settingsStore.canViewFinance" class="kpi-box">
            <span class="kpi-title">Budget</span>
            <span class="kpi-value">{{ formatCurrency(dashboard.total_budget) }}</span>
            <span class="kpi-sub">Client: {{ project?.client || '—' }}</span>
          </div>
          <div class="kpi-box">
            <span class="kpi-title">Team</span>
            <div class="kpi-avatars">
              <span
                v-for="(m, i) in dashboard.team_members?.slice(0, 3)"
                :key="m.user"
                class="kpi-avatar"
                :style="{ 'z-index': 10 - i }"
                :title="m.user"
              >{{ getInitials(m.user) }}</span>
            </div>
            <span class="kpi-sub">{{ dashboard.team_members?.length || 0 }} team members</span>
          </div>
          <div class="kpi-box">
            <span class="kpi-title">Hours</span>
            <span class="kpi-value">{{ Math.round((dashboard.total_actual_hours || 0) * 10) / 10 }}h</span>
            <span class="kpi-sub">of {{ dashboard.total_estimated_hours || 0 }}h estimated</span>
          </div>
        </div>
      </div>

      <!-- Tab Navigation -->
      <div class="tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="setTab(tab.key)"
        >
          <svg v-if="tab.icon === 'overview'" class="tab-icon-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          <svg v-else-if="tab.icon === 'tasks'" class="tab-icon-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
          <svg v-else-if="tab.icon === 'backlog'" class="tab-icon-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
          <svg v-else-if="tab.icon === 'team'" class="tab-icon-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          <svg v-else-if="tab.icon === 'files'" class="tab-icon-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          <svg v-else-if="tab.icon === 'timelogs'" class="tab-icon-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <svg v-else-if="tab.icon === 'analytics'" class="tab-icon-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
          {{ tab.label }}
        </button>
      </div>

      <!-- Tab Content -->
      <div class="tab-content">
        <ProjectDashboard v-if="activeTab === 'overview'" :id="id" :embedded="true" />

        <div v-if="activeTab === 'tasks'" class="tasks-tab">
          <div class="view-toggle-bar">
            <div class="view-toggle">
              <button :class="{ active: taskView === 'board' }" @click="taskView = 'board'">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
                Board
              </button>
              <button :class="{ active: taskView === 'list' }" @click="taskView = 'list'">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
                List
              </button>
              <button :class="{ active: taskView === 'gantt' }" @click="taskView = 'gantt'">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="6" x2="16" y2="6"/><line x1="8" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="14" y2="18"/></svg>
                Gantt
              </button>
            </div>
          </div>
          <ProjectBoard v-if="taskView === 'board'" :id="id" :embedded="true" />
          <ProjectTaskList v-if="taskView === 'list'" :id="id" :embedded="true" />
          <ProjectGantt v-if="taskView === 'gantt'" :id="id" :embedded="true" />
        </div>

        <ProjectBacklog v-if="activeTab === 'backlog'" :id="id" :embedded="true" />

        <!-- Team Tab -->
        <div v-if="activeTab === 'team'" class="team-tab">
          <div class="team-tab-header">
            <div class="team-tab-header-left">
              <h3 class="team-tab-title">Team Members</h3>
              <span class="team-count-badge">{{ dashboard.team_members?.length || 0 }} members</span>
            </div>
            <button class="btn-add-member" @click="showAddMember = !showAddMember">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Add Member
            </button>
          </div>

          <!-- Add Member Form -->
          <div v-if="showAddMember" class="add-member-form">
            <select v-model="newMemberUser" class="form-select">
              <option value="" disabled>Select user...</option>
              <option v-for="u in availableUsers" :key="u.name" :value="u.name">{{ u.full_name || u.name }}</option>
            </select>
            <select v-model="newMemberRole" class="form-select form-select-sm">
              <option value="Developer">Developer</option>
              <option value="Designer">Designer</option>
              <option value="QA">QA</option>
              <option value="Lead">Lead</option>
            </select>
            <div class="rate-input-wrap">
              <span class="rate-prefix">{{ settingsStore.currency }}</span>
              <input v-model.number="newMemberRate" type="number" class="form-input rate-input" placeholder="0" min="0" step="5" />
              <span class="rate-suffix">/hr</span>
            </div>
            <button class="btn-confirm-add" :disabled="!newMemberUser || teamSaving" @click="addMember">
              {{ teamSaving ? 'Adding...' : 'Add' }}
            </button>
            <button class="btn-cancel-add" @click="showAddMember = false">Cancel</button>
          </div>

          <div v-if="dashboard.team_members?.length" class="team-table-wrap">
            <table class="team-table">
              <thead>
                <tr>
                  <th>Member</th>
                  <th>Role</th>
                  <th v-if="settingsStore.canViewFinance" class="text-right">Hourly Rate</th>
                  <th class="text-right">Hours Logged</th>
                  <th v-if="settingsStore.canViewFinance" class="text-right">Cost</th>
                  <th class="th-actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="m in dashboard.team_members" :key="m.user">
                  <td>
                    <div class="team-member-cell">
                      <span class="team-member-avatar" :style="{ background: getAvatarColor(m.user) }">{{ getInitials(m.user) }}</span>
                      <div class="team-member-info">
                        <span class="team-member-name">{{ m.full_name || m.user }}</span>
                        <span class="team-member-email" v-if="m.full_name">{{ m.user }}</span>
                      </div>
                    </div>
                  </td>
                  <td>
                    <select
                      class="inline-select"
                      :value="m.role || 'Developer'"
                      @change="updateMember(m.user, 'role', $event.target.value)"
                    >
                      <option value="Developer">Developer</option>
                      <option value="Designer">Designer</option>
                      <option value="QA">QA</option>
                      <option value="Lead">Lead</option>
                    </select>
                  </td>
                  <td v-if="settingsStore.canViewFinance" class="text-right">
                    <div class="inline-rate-wrap">
                      <span class="rate-prefix-sm">{{ settingsStore.currency }}</span>
                      <input
                        type="number"
                        class="inline-rate-input"
                        :value="m.hourly_rate || 0"
                        min="0"
                        step="5"
                        @change="updateMember(m.user, 'hourly_rate', $event.target.value)"
                      />
                      <span class="rate-suffix-sm">/hr</span>
                    </div>
                  </td>
                  <td class="text-right font-mono">{{ m.total_hours ? m.total_hours + 'h' : '0h' }}</td>
                  <td v-if="settingsStore.canViewFinance" class="text-right font-semibold">{{ m.total_cost ? formatCurrency(m.total_cost) : '—' }}</td>
                  <td class="td-actions">
                    <button class="btn-remove-member" @click="removeMember(m.user)" title="Remove member">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    </button>
                  </td>
                </tr>
              </tbody>
              <tfoot v-if="settingsStore.canViewFinance && dashboard.team_members?.length > 1">
                <tr>
                  <td colspan="4" class="font-semibold">Total</td>
                  <td class="text-right font-semibold">{{ formatCurrency(teamTotalCost) }}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
          <div v-else class="team-empty">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            <p>No team members assigned yet.</p>
            <p class="team-empty-hint">Click "Add Member" to get started.</p>
          </div>
        </div>

        <!-- Files Tab -->
        <div v-if="activeTab === 'files'" class="files-tab">
          <div class="files-header">
            <h3 class="files-title">Project Files</h3>
            <label class="btn-upload">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              Upload File
              <input type="file" class="file-input-hidden" @change="handleFileUpload" multiple />
            </label>
          </div>
          <div v-if="filesLoading" class="files-loading">Loading files...</div>
          <div v-else-if="projectFiles.length" class="files-list">
            <div v-for="f in projectFiles" :key="f.name" class="file-item">
              <div class="file-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              </div>
              <div class="file-info">
                <a :href="f.file_url" target="_blank" class="file-name">{{ f.file_name }}</a>
                <span class="file-meta">{{ formatFileSize(f.file_size) }} &middot; {{ f.uploaded_by }} &middot; {{ formatDate(f.creation) }}</span>
              </div>
              <button class="btn-delete-file" @click="deleteFile(f.name)" title="Delete file">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            </div>
          </div>
          <div v-else class="files-empty">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <p>No files uploaded yet.</p>
          </div>
        </div>

        <!-- Time Logs Tab -->
        <div v-if="activeTab === 'timelogs'" class="timelogs-tab">
          <div class="timelogs-tab-header">
            <div class="timelogs-header-left">
              <h3 class="timelogs-tab-title">Project Time Logs</h3>
              <span class="timelogs-count-badge">{{ projectTimelogs.length }} entries</span>
            </div>
            <div class="timelogs-filters">
              <select v-if="settingsStore.featurePermissions.view_all_timelogs !== false" v-model="timelogUserFilter" class="tl-filter-select" @change="loadProjectTimelogs">
                <option value="">All Users</option>
                <option v-for="u in timelogUsers" :key="u" :value="u">{{ u }}</option>
              </select>
              <select v-model="timelogTaskFilter" class="tl-filter-select" @change="loadProjectTimelogs">
                <option value="">All Tasks</option>
                <option v-for="t in timelogTasks" :key="t.name" :value="t.name">{{ t.task_title }}</option>
              </select>
            </div>
          </div>

          <!-- Summary -->
          <div class="tl-summary-row" v-if="projectTimelogs.length">
            <div class="tl-summary-card">
              <span class="tl-summary-label">Total Hours</span>
              <span class="tl-summary-value">{{ timelogTotalHours.toFixed(1) }}h</span>
            </div>
            <div class="tl-summary-card">
              <span class="tl-summary-label">Entries</span>
              <span class="tl-summary-value">{{ projectTimelogs.length }}</span>
            </div>
            <div class="tl-summary-card">
              <span class="tl-summary-label">Active</span>
              <span class="tl-summary-value">{{ timelogRunningCount }}</span>
            </div>
          </div>

          <div v-if="timelogsLoading" class="timelogs-loading">
            <div class="spinner-sm"></div>
            <span>Loading time logs...</span>
          </div>
          <div v-else-if="projectTimelogs.length" class="tl-table-wrap">
            <table class="tl-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Task</th>
                  <th>Start</th>
                  <th>End</th>
                  <th>Duration</th>
                  <th>Notes</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="log in projectTimelogs" :key="log.name" :class="{ 'tl-row-running': log.is_running }">
                  <td>
                    <div class="tl-user-cell">
                      <span class="tl-user-avatar" :style="{ background: getAvatarColor(log.user) }">{{ getInitials(log.user_full_name || log.user) }}</span>
                      <span class="tl-user-name">{{ log.user_full_name || log.user }}</span>
                    </div>
                  </td>
                  <td>
                    <router-link :to="`/task/${log.task}`" class="tl-task-link">{{ log.task_title }}</router-link>
                  </td>
                  <td class="tl-nowrap">{{ formatDateTime(log.start_time) }}</td>
                  <td class="tl-nowrap">
                    <span v-if="log.is_running" class="tl-running-badge">
                      <span class="tl-live-dot"></span> Running
                    </span>
                    <span v-else>{{ log.end_time ? formatDateTime(log.end_time) : '-' }}</span>
                  </td>
                  <td class="tl-nowrap">
                    <span v-if="log.duration_hours || log.duration_minutes">
                      {{ log.duration_hours || 0 }}h {{ log.duration_minutes ? (log.duration_minutes % 60) : 0 }}m
                    </span>
                    <span v-else class="tl-muted">-</span>
                  </td>
                  <td><span class="tl-notes">{{ log.notes || '-' }}</span></td>
                  <td>
                    <span v-if="log.is_running" class="tl-status-tag tl-tag-running">Running</span>
                    <span v-else class="tl-status-tag tl-tag-done">Completed</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="timelogs-empty">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            <p>No time logs recorded for this project.</p>
          </div>
        </div>

        <ReportsView v-if="activeTab === 'analytics'" :projectId="id" :embedded="true" />
      </div>
    </template>

    <!-- Error / empty -->
    <div v-else-if="!loading" class="empty-state">
      <p>Project not found.</p>
      <router-link to="/projects" class="back-link">← Back to Projects</router-link>
    </div>

    <!-- Edit Project Modal -->
    <EditProjectModal
      :show="showEditProject"
      :project="project"
      @close="showEditProject = false"
      @updated="onProjectUpdated"
    />

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :show="showDeleteConfirm"
      title="Delete Project"
      :message="deleteMessage"
      :details="deleteDetails"
      confirmLabel="Delete Project"
      :confirmDanger="true"
      :loading="deleting"
      @confirm="confirmDeleteProject"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '@/store/projects'
import { useSettingsStore } from '@/store/settings'
import { call } from '@/utils/frappe'
import ProjectDashboard from '@/views/ProjectDashboard.vue'
import ProjectBoard from '@/views/ProjectBoard.vue'
import ProjectTaskList from '@/views/ProjectTaskList.vue'
import ProjectGantt from '@/views/ProjectGantt.vue'
import ProjectBacklog from '@/views/ProjectBacklog.vue'
import ReportsView from '@/views/ReportsView.vue'
import EditProjectModal from '@/components/EditProjectModal.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const props = defineProps({
  id: { type: String, required: true },
})

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const settingsStore = useSettingsStore()
const loading = ref(true)
const dashboard = ref(null)
const project = ref(null)

const tabs = computed(() => {
  const perms = settingsStore.projectTabPermissions
  const base = [
    { key: 'overview', label: 'Overview', icon: 'overview' },
    { key: 'tasks', label: 'Tasks', icon: 'tasks' },
    { key: 'backlog', label: 'Backlog', icon: 'backlog' },
    { key: 'team', label: 'Team', icon: 'team' },
    { key: 'files', label: 'Files', icon: 'files' },
    { key: 'timelogs', label: 'Time Logs', icon: 'timelogs' },
  ].filter(t => perms[t.key] !== false)
  if (settingsStore.canViewAnalytics && perms.analytics !== false) {
    base.push({ key: 'analytics', label: 'Analytics', icon: 'analytics' })
  }
  return base
})

const activeTab = ref(route.query.tab || 'overview')
const taskView = ref(route.query.view || 'board')

// Team management state
const showAddMember = ref(false)
const newMemberUser = ref('')
const newMemberRole = ref('Developer')
const newMemberRate = ref(0)
const teamSaving = ref(false)
const allUsers = ref([])

// Edit / Delete project state
const showEditProject = ref(false)
const showDeleteConfirm = ref(false)
const deleting = ref(false)
const deleteMessage = ref('')
const deleteDetails = ref([])

const canModifyProject = computed(() => {
  if (settingsStore.featurePermissions.edit_project === false) return false
  if (settingsStore.isAdmin) return true
  if (!project.value) return false
  // Get current user from frappe session
  const currentUser = window.frappe?.session?.user || window.pms_boot?.user || ''
  if (project.value.owner === currentUser) return true
  if (project.value.project_manager === currentUser) return true
  return false
})

// Files state
const projectFiles = ref([])
const filesLoading = ref(false)

// Timelogs state
const projectTimelogs = ref([])
const timelogsLoading = ref(false)
const timelogUserFilter = ref('')
const timelogTaskFilter = ref('')
const timelogUsers = ref([])
const timelogTasks = ref([])

const availableUsers = computed(() => {
  const existing = new Set((dashboard.value?.team_members || []).map(m => m.user))
  return allUsers.value.filter(u => !existing.has(u.name))
})

function setTab(key) {
  activeTab.value = key
  router.replace({ query: { ...route.query, tab: key } })
}

watch(() => route.query.tab, (val) => {
  if (val) activeTab.value = val
})

watch(() => route.query.view, (val) => {
  if (val) taskView.value = val
})

watch(activeTab, (tab) => {
  if (tab === 'files' && !projectFiles.value.length) {
    loadProjectFiles()
  }
  if (tab === 'timelogs' && !projectTimelogs.value.length) {
    loadProjectTimelogs()
    loadTimelogFilterOptions()
  }
})

const teamTotalHours = computed(() => {
  if (!dashboard.value?.team_members) return 0
  return Math.round(dashboard.value.team_members.reduce((s, m) => s + (m.total_hours || 0), 0) * 10) / 10
})

const teamTotalCost = computed(() => {
  if (!dashboard.value?.team_members) return 0
  return dashboard.value.team_members.reduce((s, m) => s + (m.total_cost || 0), 0)
})

function getAvatarColor(email) {
  const colors = ['#6366f1', '#14b8a6', '#F59E0B', '#EF4444', '#3b82f6', '#8b5cf6', '#ec4899', '#10b981']
  let hash = 0
  for (let i = 0; i < (email || '').length; i++) hash = email.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

const progressPct = computed(() => {
  if (!dashboard.value || !dashboard.value.total_tasks) return 0
  return Math.round(((dashboard.value.task_counts?.Done || 0) / dashboard.value.total_tasks) * 100)
})

const statusBarColor = computed(() => {
  const map = { 'Active': '#10b981', 'Planning': '#3b82f6', 'Completed': '#059669', 'On Hold': '#F59E0B' }
  return map[dashboard.value?.status] || '#9ca3af'
})

function statusKey(status) {
  return (status || '').toLowerCase().replace(/\s+/g, '-')
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatCurrency(value) {
  return settingsStore.formatCurrency(value)
}

function stripHtml(html) {
  if (!html) return ''
  const tmp = document.createElement('div')
  tmp.innerHTML = html
  return tmp.textContent || tmp.innerText || ''
}

function getInitials(name) {
  if (!name) return '?'
  const parts = name.split(/[\s@.]+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.substring(0, 2).toUpperCase()
}

async function loadUsers() {
  try {
    allUsers.value = await call('next_pms.api.crud.get_all_users')
  } catch (e) {
    console.error('Failed to load users:', e)
  }
}

async function addMember() {
  if (!newMemberUser.value || teamSaving.value) return
  teamSaving.value = true
  try {
    await call('next_pms.api.crud.add_project_member', {
      project: props.id,
      user: newMemberUser.value,
      role: newMemberRole.value,
      hourly_rate: newMemberRate.value || 0,
    })
    showAddMember.value = false
    newMemberUser.value = ''
    newMemberRole.value = 'Developer'
    newMemberRate.value = 0
    await reloadDashboard()
  } catch (e) {
    alert(e.message || 'Failed to add member')
  } finally {
    teamSaving.value = false
  }
}

async function removeMember(user) {
  if (!confirm(`Remove ${user} from the project?`)) return
  try {
    await call('next_pms.api.crud.remove_project_member', {
      project: props.id,
      user,
    })
    await reloadDashboard()
  } catch (e) {
    alert(e.message || 'Failed to remove member')
  }
}

async function updateMember(user, field, value) {
  try {
    const args = { project: props.id, user }
    if (field === 'role') args.role = value
    if (field === 'hourly_rate') args.hourly_rate = parseFloat(value) || 0
    await call('next_pms.api.crud.update_project_member', args)
    await reloadDashboard()
  } catch (e) {
    alert(e.message || 'Failed to update member')
  }
}

async function loadProjectFiles() {
  filesLoading.value = true
  try {
    projectFiles.value = await call('next_pms.api.files.get_project_files', { project: props.id })
  } catch (e) {
    console.error('Failed to load files:', e)
    projectFiles.value = []
  } finally {
    filesLoading.value = false
  }
}

async function handleFileUpload(event) {
  const files = event.target.files
  if (!files || !files.length) return

  for (const file of files) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('project', props.id)

    try {
      const csrf = document.cookie.split('; ').find(c => c.startsWith('csrf_token='))?.split('=')[1]
        || (window.frappe && window.frappe.csrf_token) || ''
      const resp = await fetch('/api/method/next_pms.api.files.upload_project_file', {
        method: 'POST',
        headers: csrf ? { 'X-Frappe-CSRF-Token': csrf } : {},
        credentials: 'include',
        body: formData,
      })
      const data = await resp.json()
      if (data.exc) throw new Error('Upload failed')
    } catch (e) {
      console.error('Upload failed:', e)
      alert('Failed to upload ' + file.name)
    }
  }
  event.target.value = ''
  await loadProjectFiles()
}

async function deleteFile(fileName) {
  if (!confirm('Delete this file?')) return
  try {
    await call('next_pms.api.files.delete_project_file', { file_name: fileName })
    await loadProjectFiles()
  } catch (e) {
    alert('Failed to delete file')
  }
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++ }
  return Math.round(size * 10) / 10 + ' ' + units[i]
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleString('en-US', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

const timelogTotalHours = computed(() => {
  return projectTimelogs.value.reduce((sum, log) => sum + (log.duration_hours || 0), 0)
})

const timelogRunningCount = computed(() => {
  return projectTimelogs.value.filter(l => l.is_running).length
})

async function loadProjectTimelogs() {
  timelogsLoading.value = true
  try {
    const filters = { project: props.id }
    // If user can't view all timelogs, force filter to own user
    if (settingsStore.featurePermissions.view_all_timelogs === false) {
      filters.user = window.frappe?.session?.user || window.pms_boot?.user || ''
    } else if (timelogUserFilter.value) {
      filters.user = timelogUserFilter.value
    }
    if (timelogTaskFilter.value) filters.task = timelogTaskFilter.value

    const data = await call('next_pms.api.timer.get_all_timelogs', {
      filters: JSON.stringify(filters),
      limit: 200,
      offset: 0,
    })
    projectTimelogs.value = data.logs || []
  } catch (e) {
    console.error('Failed to load project timelogs:', e)
    projectTimelogs.value = []
  } finally {
    timelogsLoading.value = false
  }
}

async function loadTimelogFilterOptions() {
  try {
    // Get team members from dashboard as user filter options
    const members = dashboard.value?.team_members || []
    timelogUsers.value = members.map(m => m.user)

    // Get tasks for this project
    const { getList } = await import('@/utils/frappe')
    timelogTasks.value = await getList('PMS Task', {
      fields: ['name', 'task_title'],
      filters: { project: props.id },
      orderBy: 'task_title asc',
      limit: 0,
    })
  } catch (e) {
    console.error('Failed to load timelog filter options:', e)
  }
}

async function reloadDashboard() {
  try {
    dashboard.value = await projectStore.fetchDashboard(props.id)
  } catch (e) {
    console.error('Failed to reload dashboard:', e)
  }
}

// Edit / Delete project handlers
async function onProjectUpdated() {
  showEditProject.value = false
  await loadProject()
}

async function handleDeleteProject() {
  try {
    const preview = await call('next_pms.api.crud.get_delete_preview', {
      doctype: 'PMS Project',
      name: props.id,
    })
    deleteMessage.value = 'This will permanently delete this project and all associated data. This action cannot be undone.'
    deleteDetails.value = []
    if (preview.tasks) deleteDetails.value.push(`${preview.tasks} task(s)`)
    if (preview.timelogs) deleteDetails.value.push(`${preview.timelogs} time log(s)`)
    if (preview.comments) deleteDetails.value.push(`${preview.comments} comment(s)`)
    if (preview.files) deleteDetails.value.push(`${preview.files} file(s)`)
    showDeleteConfirm.value = true
  } catch (e) {
    console.error('Failed to get delete preview:', e)
    alert('Failed to check project dependencies.')
  }
}

async function confirmDeleteProject() {
  deleting.value = true
  try {
    await call('next_pms.api.crud.delete_project', { project: props.id })
    showDeleteConfirm.value = false
    router.push('/projects')
  } catch (e) {
    console.error('Failed to delete project:', e)
    alert('Failed to delete project. Please try again.')
  } finally {
    deleting.value = false
  }
}

async function loadProject() {
  loading.value = true
  try {
    const [dashData, projDoc] = await Promise.all([
      projectStore.fetchDashboard(props.id),
      projectStore.fetchProject(props.id),
    ])
    dashboard.value = dashData
    project.value = projDoc
  } catch (e) {
    console.error('Failed to load project:', e)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadProject()
  loadUsers()
  // If arriving directly on a tab that needs data, load it now
  if (activeTab.value === 'files') loadProjectFiles()
  if (activeTab.value === 'timelogs') {
    loadProjectTimelogs()
    loadTimelogFilterOptions()
  }
})

watch(() => props.id, () => {
  activeTab.value = 'overview'
  taskView.value = 'board'
  // Clear stale tab data from previous project
  projectFiles.value = []
  projectTimelogs.value = []
  timelogUsers.value = []
  timelogTasks.value = []
  timelogUserFilter.value = ''
  timelogTaskFilter.value = ''
  loadProject()
})
</script>

<style scoped>
.project-detail {
  padding: 0;
}

/* Loading */
.loading-container { display: flex; flex-direction: column; align-items: center; padding: 80px 0; }
.spinner { width: 40px; height: 40px; border: 3px solid #e5e7eb; border-top-color: #6366f1; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { margin-top: 16px; color: #6b7280; font-size: 14px; }

/* Project Header */
.project-header {
  background: #ffffff;
  padding: 20px 24px 16px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.header-left { flex: 1; }

.project-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.project-color-bar {
  width: 4px;
  height: 28px;
  border-radius: 2px;
  flex-shrink: 0;
}

.project-name {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0;
}

.project-desc {
  font-size: 13px;
  color: #6b7280;
  margin: 0 0 8px 16px;
}

.header-badges {
  display: flex;
  gap: 8px;
  margin-left: 16px;
}

.badge-status {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.badge-active, .badge-in-progress { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.badge-planning, .badge-planned { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.badge-completed { background: rgba(16, 185, 129, 0.15); color: #059669; }
.badge-on-hold { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }

.header-meta-right {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-end;
  flex-shrink: 0;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #6b7280;
}

.meta-icon-text {
  font-size: 14px;
}

.header-action-btns {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.hdr-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  background: #fff;
}

.hdr-btn-edit {
  color: #374151;
}

.hdr-btn-edit:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.hdr-btn-delete {
  color: #EF4444;
  border-color: #fecaca;
}

.hdr-btn-delete:hover {
  background: #fef2f2;
  border-color: #EF4444;
}

/* KPI Row */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.kpi-box {
  background: #f8f9fa;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px;
}

.kpi-title {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
  margin-bottom: 6px;
}

.kpi-value {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 4px;
}

.kpi-sub {
  display: block;
  font-size: 11px;
  color: #9ca3af;
  margin-bottom: 6px;
}

.kpi-bar {
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
}

.kpi-bar-fill {
  height: 100%;
  background: #10b981;
  border-radius: 2px;
  transition: width 0.4s;
}

.kpi-avatars {
  display: flex;
  margin-bottom: 4px;
}

.kpi-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #6366f1;
  color: white;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #f8f9fa;
  margin-left: -6px;
}

.kpi-avatar:first-child {
  margin-left: 0;
}

/* Tab Bar */
.tab-bar {
  display: flex;
  gap: 0;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 28px;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 12px 20px;
  border: none;
  background: none;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}

.tab-btn:hover {
  color: #1a1a2e;
}

.tab-btn.active {
  color: #1a1a2e;
  font-weight: 600;
  border-bottom-color: #6366f1;
}

.tab-icon-svg {
  flex-shrink: 0;
}

/* Tab Content */
.tab-content {
  padding: 0;
}

/* Tasks Tab - View Toggle */
.tasks-tab {
  padding: 0;
}

.view-toggle-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
}

.view-toggle {
  display: flex;
  gap: 0;
  background: #f3f4f6;
  border-radius: 8px;
  padding: 3px;
}

.view-toggle button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border: none;
  background: transparent;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s;
}

.view-toggle button.active {
  background: #ffffff;
  color: #1a1a2e;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 80px 0;
  color: #6b7280;
}

.back-link {
  display: inline-block;
  margin-top: 12px;
  color: #6366f1;
  text-decoration: none;
  font-weight: 500;
}

.back-link:hover {
  text-decoration: underline;
}

/* Team Tab */
.team-tab {
  padding: 16px 0;
}

.team-tab-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.team-tab-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.team-tab-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.team-count-badge {
  display: inline-flex;
  padding: 3px 12px;
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.btn-add-member {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  background: #6366f1;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-add-member:hover { background: #4f46e5; }

/* Add Member Form */
.add-member-form {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.form-select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  color: #374151;
  background: #fff;
  outline: none;
  min-width: 180px;
}
.form-select:focus { border-color: #6366f1; }
.form-select-sm { min-width: 120px; }

.rate-input-wrap {
  display: flex;
  align-items: center;
  gap: 0;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  overflow: hidden;
}
.rate-prefix, .rate-suffix {
  padding: 8px 8px;
  font-size: 13px;
  color: #6b7280;
  background: #f9fafb;
}
.rate-input {
  width: 70px;
  padding: 8px 4px;
  border: none;
  outline: none;
  font-size: 13px;
  color: #374151;
  text-align: center;
}
.rate-input:focus { background: #fff; }

.btn-confirm-add {
  padding: 8px 16px;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-confirm-add:hover { background: #059669; }
.btn-confirm-add:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-cancel-add {
  padding: 8px 14px;
  background: none;
  color: #6b7280;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.btn-cancel-add:hover { background: #f3f4f6; }

/* Inline editable fields in table */
.inline-select {
  padding: 4px 8px;
  border: 1px solid transparent;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
  background: #f3f4f6;
  cursor: pointer;
  outline: none;
}
.inline-select:hover { border-color: #d1d5db; }
.inline-select:focus { border-color: #6366f1; background: #fff; }

.inline-rate-wrap {
  display: inline-flex;
  align-items: center;
  gap: 0;
  border: 1px solid transparent;
  border-radius: 6px;
  overflow: hidden;
  background: #f9fafb;
}
.inline-rate-wrap:hover { border-color: #d1d5db; }
.inline-rate-wrap:focus-within { border-color: #6366f1; background: #fff; }

.rate-prefix-sm, .rate-suffix-sm {
  padding: 4px 4px;
  font-size: 12px;
  color: #9ca3af;
}

.inline-rate-input {
  width: 56px;
  padding: 4px 2px;
  border: none;
  outline: none;
  font-size: 13px;
  font-family: 'SF Mono', SFMono-Regular, Consolas, monospace;
  color: #374151;
  text-align: center;
  background: transparent;
}

.th-actions { width: 60px; text-align: center; }
.td-actions { text-align: center; }

.btn-remove-member {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  background: none;
  color: #9ca3af;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-remove-member:hover { background: rgba(239, 68, 68, 0.1); color: #ef4444; }

.team-member-email {
  font-size: 11px;
  color: #9ca3af;
}

.team-table-wrap {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
}

.team-table {
  width: 100%;
  border-collapse: collapse;
}

.team-table thead {
  background: #f9fafb;
}

.team-table th {
  padding: 12px 16px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #e5e7eb;
}

.team-table td {
  padding: 14px 16px;
  font-size: 13px;
  color: #374151;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: middle;
}

.team-table tfoot td {
  padding: 14px 16px;
  font-size: 13px;
  color: #1a1a2e;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}

.text-right { text-align: right; }
.font-mono { font-family: 'SF Mono', SFMono-Regular, Consolas, monospace; }
.font-semibold { font-weight: 600; }

.team-member-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.team-member-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.team-member-name {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a2e;
}

.role-chip {
  display: inline-flex;
  padding: 2px 10px;
  background: #f3f4f6;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
}

.team-empty {
  text-align: center;
  padding: 48px 20px;
  color: #9ca3af;
  font-size: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.team-empty p { margin: 0; }
.team-empty-hint { font-size: 12px; color: #d1d5db; }

@media (max-width: 768px) {
  .project-header { padding: 16px; }
  .header-top { flex-direction: column; gap: 12px; }
  .header-meta-right { align-items: flex-start; }
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .tab-bar { padding: 0 16px; overflow-x: auto; }
  .tab-btn { padding: 10px 14px; font-size: 13px; white-space: nowrap; }
}

.files-tab {
  padding: 16px 0;
}

.files-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.files-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.btn-upload {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #6366f1;
  color: #fff;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-upload:hover {
  background: #4f46e5;
}

.file-input-hidden {
  display: none;
}

.files-loading {
  padding: 40px 0;
  text-align: center;
  color: #9ca3af;
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  transition: box-shadow 0.15s;
}

.file-item:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.file-icon {
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #1a1a2e;
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-name:hover {
  color: #6366f1;
}

.file-meta {
  font-size: 12px;
  color: #9ca3af;
}

.btn-delete-file {
  flex-shrink: 0;
  padding: 6px;
  border: none;
  background: transparent;
  color: #9ca3af;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s;
}

.btn-delete-file:hover {
  background: #fef2f2;
  color: #ef4444;
}

.files-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 60px 0;
  color: #9ca3af;
  font-size: 14px;
}

/* Time Logs Tab */
.timelogs-tab {
  padding: 16px 0;
}

.timelogs-tab-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.timelogs-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.timelogs-tab-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.timelogs-count-badge {
  display: inline-flex;
  padding: 3px 12px;
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.timelogs-filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tl-filter-select {
  padding: 7px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  color: #374151;
  background: #fff;
  outline: none;
  min-width: 140px;
  cursor: pointer;
}
.tl-filter-select:focus { border-color: #6366f1; }

/* Summary Row */
.tl-summary-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.tl-summary-card {
  background: #f8f9fa;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tl-summary-label {
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
}

.tl-summary-value {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
}

/* Loading */
.timelogs-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 48px 0;
  color: #9ca3af;
  font-size: 14px;
}

.spinner-sm {
  width: 20px;
  height: 20px;
  border: 2px solid #e5e7eb;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

/* Time Logs Table */
.tl-table-wrap {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
}

.tl-table {
  width: 100%;
  border-collapse: collapse;
}

.tl-table thead {
  background: #f9fafb;
}

.tl-table th {
  padding: 12px 16px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #e5e7eb;
}

.tl-table td {
  padding: 12px 16px;
  font-size: 13px;
  color: #374151;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: middle;
}

.tl-table tr:last-child td {
  border-bottom: none;
}

.tl-row-running {
  background: rgba(16, 185, 129, 0.04);
}

.tl-user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tl-user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}

.tl-user-name {
  font-size: 13px;
  font-weight: 500;
  color: #1a1a2e;
}

.tl-task-link {
  color: #6366f1;
  text-decoration: none;
  font-weight: 500;
}
.tl-task-link:hover { text-decoration: underline; }

.tl-nowrap {
  white-space: nowrap;
}

.tl-running-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.tl-live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10b981;
  animation: tl-pulse 1.5s ease-in-out infinite;
}

@keyframes tl-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.tl-muted {
  color: #d1d5db;
}

.tl-notes {
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
  color: #6b7280;
  font-size: 12px;
}

.tl-status-tag {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.tl-tag-running {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.tl-tag-done {
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
}

/* Empty State */
.timelogs-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 60px 0;
  color: #9ca3af;
  font-size: 14px;
}
.timelogs-empty p { margin: 0; }

@media (max-width: 768px) {
  .timelogs-tab-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .tl-summary-row {
    grid-template-columns: 1fr;
  }
  .tl-table-wrap {
    overflow-x: auto;
  }
  .tl-table {
    min-width: 700px;
  }
}
</style>
