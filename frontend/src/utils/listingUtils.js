export const RESORT_CODE_RE = /^[A-Z0-9]{2,10}$/i;

export const validateResortCodes = (value) =>
  value.trim() === "" ||
  value
    .split(",")
    .map((c) => c.trim())
    .filter(Boolean)
    .every((c) => RESORT_CODE_RE.test(c));

export const extractErrorMessage = (err, fallback) => {
  const detail = err?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((d) => d.msg || d.message || JSON.stringify(d)).join(", ");
  return fallback;
};
