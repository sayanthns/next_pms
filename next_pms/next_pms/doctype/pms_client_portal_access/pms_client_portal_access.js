// Copyright (c) 2024, Next PMS and contributors
// For license information, please see license.txt

frappe.ui.form.on("PMS Client Portal Access", {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("Regenerate Token"), function () {
                frappe.call({
                    method: "regenerate_token",
                    doc: frm.doc,
                    callback(r) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __("Token regenerated"),
                            indicator: "green",
                        });
                    },
                });
            });

            if (frm.doc.access_token) {
                frm.add_custom_button(__("Copy Portal URL"), function () {
                    var url =
                        window.location.origin +
                        "/pms-portal?token=" +
                        frm.doc.access_token;
                    frappe.utils.copy_to_clipboard(url);
                    frappe.show_alert({
                        message: __("Portal URL copied to clipboard"),
                        indicator: "green",
                    });
                });
            }
        }
    },
});
