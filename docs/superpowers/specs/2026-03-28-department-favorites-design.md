# Department & Favorites — Design Spec

**Date:** 2026-03-28
**Status:** Approved

## Problem

PMS Managers currently see all projects. Need department-scoped visibility so PMs only see their department's projects. Users also want quick access to frequently used projects via favorites.

## Design

### 1. Department Field on PMS Project

- Add `department` field (Link to Department) on PMS Project doctype
- Shown in project create/edit dialog
- Optional — projects without a department are visible to all roles

### 2. Department-Scoped PM Access

- **PMS Manager**: sees only projects where `department` matches their User's `department` field, OR `department` is empty
- **System Manager / Administrator**: sees all projects (no filter)
- **PMS Developer / PMS Viewer**: unchanged (see assigned projects only)
- Implementation: modify `project_query_conditions()` in `permissions.py` to add department filter for managers

### 3. Project Favorites

- **New doctype: `PMS Favorite Project`** — fields: `user` (Link to User), `project` (Link to PMS Project). Unique together constraint.
- **Toggle API**: `toggle_favorite_project(project)` — adds or removes favorite for current user
- **UI**: Star icon on project cards in ProjectList.vue. Filled star = favorited, outline = not.
- **Filter tab**: "Favorites" tab alongside existing filters in ProjectList.vue. Shows only favorited projects.
- **Get API**: `get_favorite_projects()` returns list of favorited project names for current user

## Files to Modify

| File | Change |
|------|--------|
| `next_pms/next_pms/doctype/pms_project/pms_project.json` | Add `department` field |
| `next_pms/next_pms/doctype/pms_favorite_project/` | New doctype (4 files) |
| `next_pms/api/permissions.py` | Add department filter in `project_query_conditions()` |
| `next_pms/api/crud.py` | Include `department` in create/update project APIs |
| `next_pms/api/projects.py` or new `favorites.py` | `toggle_favorite_project()`, `get_favorite_projects()` |
| `frontend/src/views/ProjectList.vue` | Star icon, favorites filter tab |
| `frontend/src/components/EditProjectModal.vue` | Department dropdown field |

## Not in Scope

- Department CRUD (uses Frappe's built-in Department doctype)
- Department hierarchy/nesting (flat filter only)
- Favorite tasks (only projects for now)
