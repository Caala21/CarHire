const configuredApiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
const apiOrigin = configuredApiUrl.replace(/\/+$/, "");

export function apiUrl(path) {
  if (/^https?:\/\//i.test(path)) return path;
  return `${apiOrigin}${path.startsWith("/") ? path : `/${path}`}`;
}

export class ApiError extends Error {
  constructor(message, status = 0, code = "") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export async function readResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const error = payload?.error;
    const detail = payload?.detail;
    const validationDetails = Array.isArray(error?.details)
      ? error.details.map(({ field, message: detailMessage }) => `${field}: ${detailMessage}`).join("; ")
      : "";
    const message =
      (error?.message && validationDetails ? `${error.message}: ${validationDetails}` : error?.message) ||
      (typeof detail === "string" ? detail : null) ||
      payload?.message ||
      `The request failed (${response.status}). Please try again.`;
    throw new ApiError(message, response.status, error?.code || "");
  }
  return payload;
}

export function jsonBody(value) {
  return JSON.stringify(value);
}
