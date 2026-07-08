# KT / Handoff — Meeting AI ⇄ Next PMS "Invite Bot" bridge

**For:** the agent maintaining the `meeting_ai` app.
**From:** the Next PMS (`next_pms`) agent.
**Date:** 2026-07-08.
**Goal:** let a user invite the transcription bot to a **PMS Meeting** from the Next PMS Calendar, without duplicating any Vexa/bot logic. All bot + transcription + MoM generation stays in `meeting_ai` (single source). `next_pms` only *triggers* it and *receives the MoM back*.

Both apps live in the same bench (`/home/v15/frappe-bench` on office; `mysite.local` locally), so calls are in-process — no HTTP/webhook needed between them.

---

## What Next PMS has already built (done, deployed)

On the **PMS Meeting** DocType (`next_pms`), three new fields:

| Field | Type | Who writes it |
|---|---|---|
| `meeting_url` | Small Text | user (the call link) |
| `ai_meeting` | Data (read-only) | set by next_pms from your return value |
| `bot_status` | Data (read-only) | set by next_pms initially; **you update it** as the job progresses |
| `mom_pdf` | Attach (existing) | **you write** the final PDF here when the MoM is ready |

`next_pms/api/calendar.py → invite_bot(name)` (whitelisted) does, when the user clicks **Invite bot**:

```python
bridge = frappe.get_attr("meeting_ai.api.bridge.create_and_invite")
res = bridge(
    source_pms_meeting = doc.name,        # str, PMS Meeting id
    title              = doc.subject,     # str
    meeting_url        = doc.meeting_url,  # str (http/https link)
    project            = doc.project,      # str | None, PMS Project id (e.g. "PROJ-1677")
    project_name       = project_name,     # str | None, human name (e.g. "ATA")
    meeting_date       = str(doc.meeting_date or ""),  # "YYYY-MM-DD" or ""
    attendees          = [{"user": "<email>", "full_name": "<name>"}, ...],  # list[dict]
)
doc.db_set("ai_meeting", res.get("ai_meeting"))
doc.db_set("bot_status", res.get("status") or "Bot Scheduled")
```

It is guarded: if `meeting_ai` is not installed, or `meeting_ai.api.bridge.create_and_invite` does not resolve, the user gets a clean error ("bot bridge not deployed yet"). So **nothing breaks before you ship your half** — the button just errors gracefully.

---

## What you need to build in `meeting_ai`

### 1. `meeting_ai/api/bridge.py` → `create_and_invite(...)`

```python
@frappe.whitelist()
def create_and_invite(source_pms_meeting, title, meeting_url, project=None,
                      project_name=None, meeting_date=None, attendees=None, language=None):
    # attendees arrives as a Python list[dict] (in-process call) — but also accept a
    # JSON string in case it is ever called over HTTP:
    if isinstance(attendees, str):
        attendees = json.loads(attendees or "[]")

    # idempotency: if an AI Meeting already exists for this PMS meeting, reuse it
    existing = frappe.db.get_value("AI Meeting", {"source_pms_meeting": source_pms_meeting}, "name")
    doc = frappe.get_doc("AI Meeting", existing) if existing else frappe.new_doc("AI Meeting")

    doc.title = title
    doc.client_name = project_name          # or resolve the real customer if you prefer
    doc.project = project_name or project
    doc.meeting_url = meeting_url
    doc.source = "Vexa Bot"
    doc.language = language or "en-IN"       # your call on default
    if meeting_date:
        doc.meeting_date = meeting_date
    doc.source_pms_meeting = source_pms_meeting   # NEW field — see step 2
    # map attendees -> your AI Meeting Attendee child table
    doc.set("attendees", [])
    for a in (attendees or []):
        doc.append("attendees", {"email": a.get("user"), "full_name": a.get("full_name")})
    doc.save(ignore_permissions=True)

    # dispatch the bot (reuse the existing logic you already have in vexa.invite_bot)
    from meeting_ai.api.vexa import invite_bot
    invite_bot(doc.name)

    return {"ai_meeting": doc.name, "status": doc.status or "Bot Scheduled"}
```

Adjust field mapping to your actual AI Meeting schema. The **only hard requirements** from the next_pms side are the return shape `{"ai_meeting": <name>, "status": <str>}` and honoring `source_pms_meeting`.

### 2. New link field on **AI Meeting**: `source_pms_meeting`

- Type `Data` (read-only). *Do not* use a `Link` to "PMS Meeting" — that would make `meeting_ai` hard-depend on `next_pms` being installed. Keep it `Data` for loose coupling.
- Purpose: lets you (a) dedupe re-invites, (b) know which PMS Meeting to write the MoM back to.

### 3. Write the MoM back to the PMS Meeting when your pipeline finishes

Wherever your pipeline sets the AI Meeting to "MoM ready" / attaches `mom_pdf` (your poll/webhook completion in `vexa.py`, or the MoM generator), add:

```python
pms = frappe.db.get_value("AI Meeting", ai_meeting_name, "source_pms_meeting")
if pms and frappe.db.exists("PMS Meeting", pms):
    updates = {"bot_status": doc.status}          # keep the calendar's status mirror fresh
    if doc.mom_pdf:
        updates["mom_pdf"] = doc.mom_pdf           # <-- fills the field the calendar needs to mark Held
    frappe.db.set_value("PMS Meeting", pms, updates)
```

- Guard with `frappe.db.exists("PMS Meeting", pms)` so `meeting_ai` still works on sites without `next_pms`.
- Push `bot_status` at each stage transition too (Bot Scheduled → Recording → Transcribing → MoM Draft → Done) so the calendar card shows live progress. The value is free-text on the next_pms side — just send your AI Meeting `status` string.
- Setting `mom_pdf` closes the loop: the calendar already requires a PDF to mark a meeting **Held**, so an auto-generated MoM makes the meeting completable with one click.

---

## Field/contract summary (the whole coupling surface)

| Direction | Mechanism |
|---|---|
| next_pms → meeting_ai | in-process call `meeting_ai.api.bridge.create_and_invite(...)` (signature above) |
| meeting_ai → next_pms | `frappe.db.set_value("PMS Meeting", <source_pms_meeting>, {"mom_pdf": ..., "bot_status": ...})` on completion |

No other coupling. AI Meeting and PMS Meeting stay **separate records** (transcription job vs schedule), linked 1:1 via `source_pms_meeting` only when a bot is invited.

## Notes
- `mom_pdf` on PMS Meeting is an `Attach` field storing a file URL string. If your generated PDF is a private File, link it to the PMS Meeting (`attached_to_doctype="PMS Meeting"`, `attached_to_name=<pms>`) so meeting viewers can open it — mirror what `next_pms/api/calendar.py save_meeting` does.
- Deploy on office is via `git pull` as user `v15`; **`bench migrate` is currently blocked** by a pre-existing HRMS `job-application` Web Form duplicate, so sync new/changed DocTypes with `bench --site <site> execute frappe.reload_doc --kwargs "{'module':'meeting_ai','dt':'doctype','dn':'ai_meeting'}"` then `clear-cache` + root `supervisorctl restart all`.
- Test target sites: `office` (= office.enfono.com, primary) and `enfono-office-new` (= office.enfonoerp.com).

## Definition of done
1. `meeting_ai.api.bridge.create_and_invite` exists, returns `{ai_meeting, status}`, dispatches the bot.
2. AI Meeting has `source_pms_meeting` (Data).
3. Pipeline completion writes `mom_pdf` + `bot_status` back to the PMS Meeting (guarded).
4. End-to-end: from Next PMS Calendar → Edit a meeting → paste link → **Invite bot** → bot joins → after the call, the MoM PDF appears on the meeting and it can be marked Held.
