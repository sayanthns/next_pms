/**
 * Frappe API utilities for Vue 3 SPA.
 * Wraps fetch calls to the Frappe backend.
 * Includes request deduplication and short-lived TTL cache.
 */

import { isNative, apiBase, getToken } from './native'

function BASE() { return apiBase() }  // "" on web (same-origin), absolute https in native

// --- Request deduplication & TTL cache ---
const _inflightRequests = new Map(); // key -> Promise (dedup concurrent identical calls)
const _responseCache = new Map();    // key -> { data, expiry }
const DEFAULT_CACHE_TTL = 5000;      // 5 seconds

function _cacheKey(method, args) {
  return method + '::' + JSON.stringify(args);
}

function _getCached(key) {
  const entry = _responseCache.get(key);
  if (entry && Date.now() < entry.expiry) return entry.data;
  if (entry) _responseCache.delete(key);
  return undefined;
}

function _setCache(key, data, ttl = DEFAULT_CACHE_TTL) {
  _responseCache.set(key, { data, expiry: Date.now() + ttl });
}

/** Clear all cached responses (call after mutations) */
export function clearCache() {
  _responseCache.clear();
}

/** Clear cache entries matching a method prefix */
export function clearCacheFor(methodPrefix) {
  for (const key of _responseCache.keys()) {
    if (key.startsWith(methodPrefix)) _responseCache.delete(key);
  }
}

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
  if (isNative()) {
    const t = getToken()
    if (t) headers["Authorization"] = "token " + t
  }
  return headers;
}

/**
 * Pull the clean user-facing message out of a Frappe error response.
 * Prefers `_server_messages` (what frappe.throw sets — clean text + title), and
 * only falls back to the raw traceback tail in `exc` so users never see a full
 * Python traceback in an alert.
 */
export function extractServerMessage(data) {
  if (data && data._server_messages) {
    try {
      const arr = JSON.parse(data._server_messages);
      const parts = arr.map((m) => {
        try {
          const o = JSON.parse(m);
          return (o.message || o).toString();
        } catch {
          return String(m);
        }
      });
      const msg = parts.join(" ").replace(/<[^>]+>/g, "").trim();
      if (msg) return msg;
    } catch {
      /* fall through */
    }
  }
  if (data && data.exc) {
    try {
      const exc = JSON.parse(data.exc);
      const last = String(exc[exc.length - 1] || "").trim().split("\n").pop().trim();
      // Strip "frappe.exceptions.SomeError: " prefix if present.
      return last.replace(/^[\w.]*(?:Error|Exception):\s*/, "") || "Server error";
    } catch {
      /* fall through */
    }
  }
  return "Server error";
}

/**
 * Call a Frappe whitelisted method.
 * @param {string} method - Dotted method path
 * @param {object} args - Method arguments
 * @param {object} opts - Options: { cache: boolean|number } to enable TTL cache (ms)
 */
export async function call(method, args = {}, opts = {}) {
  const key = _cacheKey(method, args);

  // Check TTL cache (only for GET-style reads)
  if (opts.cache) {
    const cached = _getCached(key);
    if (cached !== undefined) return cached;
  }

  // Deduplicate concurrent identical requests
  if (_inflightRequests.has(key)) {
    return _inflightRequests.get(key);
  }

  const promise = (async () => {
    const response = await fetch(`${BASE()}/api/method/${method}`, {
      method: "POST",
      headers: getHeaders(),
      credentials: "include",
      body: JSON.stringify(args),
    });
    const data = await response.json();
    if (data._server_messages || data.exc) {
      throw new Error(extractServerMessage(data));
    }
    return data.message;
  })();

  _inflightRequests.set(key, promise);

  try {
    const result = await promise;
    // Cache the result if caching requested
    if (opts.cache) {
      const ttl = typeof opts.cache === 'number' ? opts.cache : DEFAULT_CACHE_TTL;
      _setCache(key, result, ttl);
    }
    return result;
  } finally {
    _inflightRequests.delete(key);
  }
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
    `${BASE()}/api/method/frappe.client.get_list?${params}`,
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
    `${BASE()}/api/resource/${doctype}/${encodeURIComponent(name)}`,
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
  if (window.frappe && typeof window.frappe.show_alert === "function") {
    window.frappe.show_alert({ message, indicator }, indicator === "red" ? 7 : 5);
  } else if (typeof window !== "undefined") {
    // Fallback so the user always gets feedback even when frappe's desk JS isn't loaded.
    window.alert(message);
  }
}
