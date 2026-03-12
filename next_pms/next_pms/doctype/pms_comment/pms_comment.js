// Copyright (c) 2024, Next PMS and contributors
// For license information, please see license.txt

frappe.ui.form.on("PMS Comment", {
    refresh(frm) {
        frm.set_query("task", function () {
            return {};
        });
    },
});
