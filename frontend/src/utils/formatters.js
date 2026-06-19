import { MAX_PAYLOAD_CHARS } from "../constants";

export function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString();
}

export function formatPercent(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${Math.round(value * 100)}%`;
}

export function formatScore(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${Math.round(value * 100)} / 100`;
}

export function formatPayload(payload) {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const text = JSON.stringify(payload, null, 2);
  if (!text) {
    return null;
  }

  if (text.length <= MAX_PAYLOAD_CHARS) {
    return text;
  }

  return `${text.slice(0, MAX_PAYLOAD_CHARS)}\n...<truncated>`;
}

export function formatFileSize(bytes) {
  const value = Number(bytes);
  if (!Number.isFinite(value) || value < 0) {
    return "-";
  }
  if (value === 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  const unitIndex = Math.min(
    Math.floor(Math.log(value) / Math.log(1024)),
    units.length - 1
  );
  const sized = value / 1024 ** unitIndex;
  const precision = unitIndex === 0 ? 0 : 2;
  return `${sized.toFixed(precision)} ${units[unitIndex]}`;
}
