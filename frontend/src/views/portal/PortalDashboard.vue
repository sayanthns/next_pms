<template>
  <div class="portal-dashboard">
    <!-- Stats Cards -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon blue">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/></svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.total_projects }}</span>
          <span class="stat-label">Projects</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon amber">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.pending_approvals }}</span>
          <span class="stat-label">Pending Approvals</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon red">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.open_tickets }}</span>
          <span class="stat-label">Open Tickets</span>
        </div>
      </div>
    </div>

    <!-- Projects -->
    <div class="section-header">
      <h2>My Projects</h2>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <span>Loading projects...</span>
    </div>

    <div v-else-if="projects.length === 0" class="empty-state">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.5"><path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/></svg>
      <p>No projects assigned yet.</p>
    </div>

    <div v-else class="project-grid">
      <div
        v-for="project in projects"
        :key="project.name"
        class="project-card"
        @click="$router.push(`/portal/project/${project.name}`)"
      >
        <div class="project-card-header">
          <h3 class="project-name">{{ project.project_name }}</h3>
          <span class="project-status" :class="statusClass(project.status)">{{ project.status }}</span>
        </div>

        <p v-if="project.description" class="project-desc">{{ truncate(project.description, 100) }}</p>

        <!-- Progress -->
        <div class="project-progress">
          <div class="progress-info">
            <span>Progress</span>
            <span class="progress-pct">{{ project.progress }}%</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: project.progress + '%' }"></div>
          </div>
          <div class="progress-tasks">
            {{ project.completed_tasks }} / {{ project.total_tasks }} tasks done
          </div>
        </div>

        <!-- Badges row -->
        <div class="project-badges">
          <span v-if="project.pending_approvals > 0" class="badge badge-amber">
            {{ project.pending_approvals }} approval{{ project.pending_approvals > 1 ? 's' : '' }} pending
          </span>
          <span v-if="project.open_tickets > 0" class="badge badge-red">
            {{ project.open_tickets }} open ticket{{ project.open_tickets > 1 ? 's' : '' }}
          </span>
          <span v-if="project.next_milestone" class="badge badge-blue">
            Next: {{ project.next_milestone.sprint_name }}
          </span>
        </div>

        <!-- Team -->
        <div v-if="project.team_members && project.team_members.length" class="project-team">
          <div
            v-for="(member, idx) in project.team_members.slice(0, 5)"
            :key="idx"
            class="team-avatar"
            :title="member.full_name"
          >
            {{ initials(member.full_name) }}
          </div>
          <span v-if="project.team_members.length > 5" class="team-more">
            +{{ project.team_members.length - 5 }}
          </span>
        </div>

        <!-- Dates -->
        <div class="project-dates">
          <span v-if="project.start_date">{{ formatDate(project.start_date) }}</span>
          <span v-if="project.start_date && project.end_date"> - </span>
          <span v-if="project.end_date">{{ formatDate(project.end_date) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { call } from '@/utils/frappe'

const projects = ref([])
const stats = ref({ total_projects: 0, pending_approvals: 0, open_tickets: 0 })
const loading = ref(true)

onMounted(async () => {
  try {
    const [projectsRes, statsRes] = await Promise.all([
      call('next_pms.api.portal.get_portal_projects'),
      call('next_pms.api.portal.get_portal_stats'),
    ])
    projects.value = projectsRes || []
    stats.value = statsRes || { total_projects: 0, pending_approvals: 0, open_tickets: 0 }
  } catch (e) {
    console.error('Portal dashboard load error:', e)
  } finally {
    loading.value = false
  }
})

function statusClass(status) {
  const map = {
    'Active': 'status-active',
    'Completed': 'status-completed',
    'On Hold': 'status-hold',
    'Cancelled': 'status-cancelled',
  }
  return map[status] || 'status-default'
}

function truncate(text, len) {
  if (!text) return ''
  const stripped = text.replace(/<[^>]+>/g, '')
  return stripped.length > len ? stripped.slice(0, len) + '...' : stripped
}

function initials(name) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

function formatDate(d) {
  if (!d) return ''
  try {
    return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch {
    return d
  }
}
</script>

<style scoped>
.portal-dashboard {
  max-width: 100%;
}

/* Stats */
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  border: 1px solid #e5e7eb;
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon.blue { background: #eff6ff; color: #2563eb; }
.stat-icon.blue svg { stroke: #2563eb; }
.stat-icon.amber { background: #fffbeb; color: #d97706; }
.stat-icon.amber svg { stroke: #d97706; }
.stat-icon.red { background: #fef2f2; color: #dc2626; }
.stat-icon.red svg { stroke: #dc2626; }

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
  font-weight: 500;
}

/* Section */
.section-header {
  margin-bottom: 16px;
}

.section-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

/* Loading / Empty */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #94a3b8;
  gap: 12px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Project Grid */
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.project-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.project-card:hover {
  border-color: #2563eb;
  box-shadow: 0 4px 12px rgba(37,99,235,0.08);
  transform: translateY(-1px);
}

.project-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.project-name {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
  line-height: 1.3;
}

.project-status {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  white-space: nowrap;
  flex-shrink: 0;
}

.status-active { background: #dcfce7; color: #16a34a; }
.status-completed { background: #eff6ff; color: #2563eb; }
.status-hold { background: #fef9c3; color: #ca8a04; }
.status-cancelled { background: #fee2e2; color: #dc2626; }
.status-default { background: #f1f5f9; color: #64748b; }

.project-desc {
  font-size: 13px;
  color: #64748b;
  margin: 0;
  line-height: 1.5;
}

/* Progress */
.project-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
}

.progress-pct {
  font-weight: 600;
  color: #2563eb;
}

.progress-bar {
  height: 6px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #2563eb, #3b82f6);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.progress-tasks {
  font-size: 11px;
  color: #94a3b8;
}

/* Badges */
.project-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.badge {
  font-size: 11px;
  font-weight: 500;
  padding: 3px 8px;
  border-radius: 6px;
}

.badge-amber { background: #fffbeb; color: #d97706; }
.badge-red { background: #fef2f2; color: #dc2626; }
.badge-blue { background: #eff6ff; color: #2563eb; }

/* Team avatars */
.project-team {
  display: flex;
  align-items: center;
  gap: 0;
}

.team-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #e0e7ff;
  color: #4338ca;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: -4px;
  border: 2px solid #fff;
}

.team-avatar:first-child {
  margin-left: 0;
}

.team-more {
  font-size: 11px;
  color: #94a3b8;
  margin-left: 8px;
}

/* Dates */
.project-dates {
  font-size: 11px;
  color: #94a3b8;
}

/* Responsive */
@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: 1fr;
  }

  .project-grid {
    grid-template-columns: 1fr;
  }
}
</style>
