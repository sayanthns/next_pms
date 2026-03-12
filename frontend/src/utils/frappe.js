/**
 * Frappe API utilities for Vue 3 SPA.
 * Wraps fetch calls to the Frappe backend.
 */

const BASE_URL = "";

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return null;
}

function getCSRFToken() {
  // Try cookie first (Desk pages set this)
  const fromCookie = getCookie("csrf_token");
  if (fromCookie) return fromCookie;
  // Fall back to boot data injected by the www page
  const boot = window.pms_boot || window["pms_boot"];
  if (boot && boot.csrf_token) return boot.csrf_token;
  // Last resort: check frappe.csrf_token (set by Frappe JS on Desk)
  if (window.frappe && window.frappe.csrf_token) return window.frappe.csrf_token;
  return null;
}

function getHeaders() {
  const headers = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  const csrf = getCSRFToken();
  if (csrf) {
    headers["X-Frappe-CSRF-Token"] = csrf;
  }
  return headers;
}

export async function call(method, args = {}) {
  const response = await fetch(`${BASE_URL}/api/method/${method}`, {
    method: "POST",
    headers: getHeaders(),
    credentials: "include",
    body: JSON.stringify(args),
  });
  const data = await response.json();
  if (data.exc) {
    const error = JSON.parse(data.exc);
    throw new Error(error[error.length - 1] || "Server error");
  }
  return data.message;
}

export async function getList(doctype, options = {}) {
  const {
    fields = ["name"],
    filters = {},
    orderBy = "modified desc",
    limit = 20,
    start = 0,
  } = options;

  const params = new URLSearchParams({
    doctype,
    fields: JSON.stringify(fields),
    filters: JSON.stringify(filters),
    order_by: orderBy,
    limit_page_length: limit,
    limit_start: start,
  });

  const response = await fetch(
    `${BASE_URL}/api/method/frappe.client.get_list?${params}`,
    {
      headers: getHeaders(),
      credentials: "include",
    }
  );
  const data = await response.json();
  return data.message || [];
}

export async function getDoc(doctype, name) {
  const response = await fetch(
    `${BASE_URL}/api/resource/${doctype}/${encodeURIComponent(name)}`,
    {
      headers: getHeaders(),
      credentials: "include",
    }
  );
  const data = await response.json();
  return data.data;
}

export async function setValue(doctype, name, fieldname, value) {
  return call("frappe.client.set_value", {
    doctype,
    name,
    fieldname,
    value,
  });
}

export async function getCount(doctype, filters = {}) {
  return call("frappe.client.get_count", { doctype, filters });
}

export function subscribeRealtime(event, callback) {
  if (window.frappe && window.frappe.realtime) {
    window.frappe.realtime.on(event, callback);
  }
}

export function unsubscribeRealtime(event, callback) {
  if (window.frappe && window.frappe.realtime) {
    window.frappe.realtime.off(event, callback);
  }
}

export function showAlert(message, indicator = "blue") {
  if (window.frappe) {
    window.frappe.show_alert({ message, indicator });
  }
}
