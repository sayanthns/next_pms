import frappe
from frappe.utils.file_manager import save_file
from next_pms.api.permissions import check_project_access


@frappe.whitelist()
def get_project_files(project):
    """Get all files attached to a project."""
    check_project_access(project)

    files = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "PMS Project",
            "attached_to_name": project,
            "is_private": ["in", [0, 1]],
        },
        fields=[
            "name", "file_name", "file_url", "file_size",
            "is_private", "owner", "creation", "modified",
        ],
        order_by="creation desc",
    )

    for f in files:
        f["uploaded_by"] = frappe.get_cached_value("User", f["owner"], "full_name") or f["owner"]

    return files


@frappe.whitelist()
def get_task_files(task):
    """Get all files attached to a task."""
    # Verify task exists
    if not frappe.db.exists("PMS Task", task):
        frappe.throw("Task not found", frappe.DoesNotExistError)

    files = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "PMS Task",
            "attached_to_name": task,
            "is_private": ["in", [0, 1]],
        },
        fields=[
            "name", "file_name", "file_url", "file_size",
            "is_private", "owner", "creation", "modified",
        ],
        order_by="creation desc",
    )

    for f in files:
        f["uploaded_by"] = frappe.get_cached_value("User", f["owner"], "full_name") or f["owner"]

    return files


@frappe.whitelist()
def delete_task_file(file_name):
    """Delete a file attached to a task."""
    file_doc = frappe.get_doc("File", file_name)

    if file_doc.attached_to_doctype != "PMS Task":
        frappe.throw("This file is not attached to a task.")

    file_doc.delete()
    return {"success": True}


@frappe.whitelist()
def upload_project_file(project):
    """Upload a file and attach it to a project."""
    check_project_access(project)

    if not frappe.request.files:
        frappe.throw("No file uploaded")

    filedata = frappe.request.files.get("file")
    if not filedata:
        frappe.throw("No file found in request")

    content = filedata.stream.read()
    filename = filedata.filename

    file_doc = save_file(
        fname=filename,
        content=content,
        dt="PMS Project",
        dn=project,
        is_private=1,
    )

    # Ensure attachment fields are set correctly
    if file_doc.attached_to_doctype != "PMS Project" or file_doc.attached_to_name != project:
        file_doc.attached_to_doctype = "PMS Project"
        file_doc.attached_to_name = project
        file_doc.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "name": file_doc.name,
        "file_name": file_doc.file_name,
        "file_url": file_doc.file_url,
        "file_size": file_doc.file_size,
        "owner": file_doc.owner,
    }


@frappe.whitelist()
def save_task_link(task, url, title=None):
    """Save a link attachment for a task."""
    if not frappe.db.exists("PMS Task", task):
        frappe.throw("Task not found", frappe.DoesNotExistError)

    doc = frappe.get_doc({
        "doctype": "PMS Link Attachment",
        "task": task,
        "url": url,
        "title": title or url,
        "added_by": frappe.session.user,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "name": doc.name,
        "url": doc.url,
        "title": doc.title,
        "added_by_name": frappe.get_cached_value("User", doc.added_by, "full_name") or doc.added_by,
        "creation": str(doc.creation),
    }


@frappe.whitelist()
def get_task_links(task):
    """Get all link attachments for a task."""
    if not frappe.db.exists("PMS Task", task):
        frappe.throw("Task not found", frappe.DoesNotExistError)

    links = frappe.get_all(
        "PMS Link Attachment",
        filters={"task": task},
        fields=["name", "url", "title", "added_by", "creation"],
        order_by="creation desc",
    )

    for link in links:
        link["added_by_name"] = frappe.get_cached_value(
            "User", link["added_by"], "full_name"
        ) or link.get("added_by", "")

    return links


@frappe.whitelist()
def delete_task_link(name):
    """Delete a link attachment."""
    doc = frappe.get_doc("PMS Link Attachment", name)
    doc.delete(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def delete_project_file(file_name):
    """Delete a file attached to a project."""
    file_doc = frappe.get_doc("File", file_name)

    if file_doc.attached_to_doctype == "PMS Project":
        check_project_access(file_doc.attached_to_name)

    file_doc.delete()
    return {"success": True}


@frappe.whitelist()
def save_project_link(project, url, title=None):
    """Save a link attachment for a project."""
    check_project_access(project)

    doc = frappe.get_doc({
        "doctype": "PMS Link Attachment",
        "project": project,
        "url": url,
        "title": title or url,
        "added_by": frappe.session.user,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "name": doc.name,
        "url": doc.url,
        "title": doc.title,
        "added_by_name": frappe.get_cached_value("User", doc.added_by, "full_name") or doc.added_by,
        "creation": str(doc.creation),
    }


@frappe.whitelist()
def get_project_links(project):
    """Get all link attachments for a project."""
    check_project_access(project)

    links = frappe.get_all(
        "PMS Link Attachment",
        filters={"project": project},
        fields=["name", "url", "title", "added_by", "creation"],
        order_by="creation desc",
    )

    for link in links:
        link["added_by_name"] = frappe.get_cached_value(
            "User", link["added_by"], "full_name"
        ) or link.get("added_by", "")

    return links


@frappe.whitelist()
def delete_project_link(name):
    """Delete a project link attachment."""
    doc = frappe.get_doc("PMS Link Attachment", name)
    if doc.project:
        check_project_access(doc.project)
    doc.delete(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}
