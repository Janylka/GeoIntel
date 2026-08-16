// Shared API client for the GeoIntel frontend.
// Talks to the FastAPI backend, which is served from the same origin
// (see deploy notes in README.md) so API_BASE is left empty by default.
const API_BASE = window.GEOINTEL_API_BASE || "";

// FastAPI's error bodies come in three shapes: a plain string (HTTPException),
// a Pydantic validation array (422, one entry per bad field), or our own
// error objects (e.g. ScopeTooFineError has "message"). Handle all three so
// the UI never shows a raw stringified object.
function extractErrorMessage(detail, status) {
  if (typeof detail.detail === "string") return detail.detail;
  if (Array.isArray(detail.detail)) {
    return detail.detail
      .map((e) => `${(e.loc || []).slice(1).join(".") || "field"}: ${e.msg}`)
      .join("; ");
  }
  if (detail.message) return detail.message;
  if (detail.error) return detail.error;
  return `Request failed: ${status}`;
}

async function apiRequest(path, { method = "GET", body, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = await window.geointelAuth?.getIdToken?.();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail;
    try {
      detail = await res.json();
    } catch {
      detail = { detail: res.statusText };
    }
    const err = new Error(extractErrorMessage(detail, res.status));
    err.status = res.status;
    err.body = detail;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

const GeoIntelAPI = {
  health: () => apiRequest("/health"),
  getUnits: () => apiRequest("/api/units/"),
  getUnitSeries: (unitId, metric, startDate, endDate) => {
    const params = new URLSearchParams({ metric });
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    return apiRequest(`/api/units/${unitId}/series?${params.toString()}`);
  },
  getUnitsGeoJSON: () => apiRequest("/api/geo/units.geojson"),
  getAlerts: () => apiRequest("/api/alerts/"),
  dismissAlert: (alertId) =>
    apiRequest(`/api/alerts/${alertId}/dismiss`, { method: "PUT", auth: true }),
  getOpsEvents: () => apiRequest("/api/ops/events"),
  explain: (payload) => apiRequest("/api/explain", { method: "POST", body: payload }),
  generateReport: (payload) =>
    apiRequest("/api/reports/generate", { method: "POST", body: payload, auth: true }),
  registerField: (payload) =>
    apiRequest("/api/fields/register", { method: "POST", body: payload, auth: true }),
  requestInvoice: (plan) =>
    apiRequest("/api/billing/invoices", { method: "POST", body: { plan }, auth: true }),
  getInvoices: () => apiRequest("/api/billing/invoices", { auth: true }),
  confirmInvoice: (invoiceId) =>
    apiRequest(`/api/admin/invoices/${invoiceId}/confirm`, { method: "POST", auth: true }),
};

window.GeoIntelAPI = GeoIntelAPI;
