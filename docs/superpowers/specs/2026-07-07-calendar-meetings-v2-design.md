# Calendar Meetings v2 — PDF MoM, Client-meeting rules, auto-tasks

**Date:** 2026-07-07
**Status:** Approved (design), building
**Builds on:** 2026-07-07 Calendar feature (PMS Meeting + PMS Meeting Attendee + `next_pms/api/calendar.py` + CalendarView.vue)

## Goal
Extend the Calendar/scheduled-meetings feature with three behaviours the team asked for:
1. Minutes of Meeting delivered as a **PDF attachment** (not just rich text); the PDF is what makes a meeting completable.
2. **Client Weekly** meetings default and must carry a project.
3. On meeting creation, seed a **follow-up Task per participant** on the meeting's project.

## Requirements & decisions

### 1. PDF MoM (req 1 & 2)
- New field `mom_pdf` (Attach) on **PMS Meeting**. Keep `minutes` (Text Editor) as **optional Notes**.
- Flow: first save creates the meeting in **Planned** ("pending"). To mark it **Held** ("done"), a PDF MoM must be attached.
- Controller gate (replaces the old rich-text check): if `status == "Held"` and `mom_pdf` is empty → `frappe.throw`. Also validate the attachment is a `.pdf` (throw otherwise).
- `has_mom` (list/cards) now = `bool(mom_pdf)`.
- Frontend: modal adds a PDF upload (reuse the existing `/api/method/upload_file` + CSRF pattern from CreateTaskModal, `is_private=1`); stores the returned `file_url` in `mom_pdf`; shows attached file link + replace/remove. "Mark held" blocks client-side if no PDF.

### 2. Client Weekly rules (req 3)
- Default `meeting_type` = **Client Weekly** (frontend blank form + backend `save_meeting` default; doctype default already Client Weekly).
- Controller: if `meeting_type == "Client Weekly"` and no `project` → `frappe.throw`. This blocks **scheduling** (save), not just Held. Modal marks Project required for that type and blocks save with a message.

### 3. Auto-create tasks (req 4)
- In **`PMSMeeting.after_insert`** (fires once → create-once, no re-sync on edit): if the meeting has a `project` and ≥1 participant, create one **PMS Task per participant**:
  - `task_title` = `"Follow-up: {subject}"`
  - `project` = meeting project, `assigned_to` = participant user
  - `task_type` = `"Meeting"`, `status` = `"To Do"`, `due_date` = `meeting_date`
  - `description` back-references the meeting (name + date)
  - created with `ignore_permissions=True`
- Project-less (Internal/Ad-hoc) meetings create **no** tasks (PMS Task requires a project).
- Coordinator gets a task only if they are also in the participants list.
- No recurring meeting generation exists, so weekly volume is created manually and acceptable.

## Files touched
- `next_pms/next_pms/doctype/pms_meeting/pms_meeting.json` — `+mom_pdf` (Attach), field_order.
- `next_pms/next_pms/doctype/pms_meeting/pms_meeting.py` — Held gate → mom_pdf + `.pdf` check; Client Weekly project rule; `after_insert` task creation.
- `next_pms/api/calendar.py` — `mom_pdf` in save/get/list; `has_mom` from mom_pdf; default type Client Weekly.
- `frontend/src/views/CalendarView.vue` — PDF upload control; default type Client Weekly; project-required-for-CW; Held gate on PDF.
- `next_pms/api/test_calendar.py` — update Held gate test (PDF now); add Client-Weekly-project test; add after_insert task-creation tests (per-participant, skip no-project, create-once).

## Edge cases
- Existing meetings: can only be marked Held after attaching a PDF going forward; existing Held rows are untouched (validated only on save).
- `.pdf` enforcement on `mom_pdf`.
- Participant dedup already handled in `save_meeting`.
- `after_insert` runs exactly once → no duplicate tasks; editing never adds/removes tasks.

## Deploy
- `frappe.reload_doc("next_pms","doctype","pms_meeting")` on both sites (office full migrate still blocked by the pre-existing HRMS `job-application` Web Form dup — see task_75a8a64a).
- Frontend rebuild (`yarn build`), commit dist.
- clear-cache + root `supervisorctl restart all`. Verify via console smoke (rolls back).
