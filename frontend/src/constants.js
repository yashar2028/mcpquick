const runtimeApiUrl = (() => {
  if (typeof window === "undefined") return null;
  const { hostname, protocol } = window.location;
  // Codespaces: swap -5173 for -8000 in the hostname
  if (hostname.includes("-5173.")) {
    return `${protocol}//${hostname.replace("-5173.", "-8000.")}`;
  }
  // Localhost dev
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://localhost:8000";
  }
  return `${protocol}//${hostname}:8000`;
})();

export const API_BASE_URL = runtimeApiUrl

export const AUTH_STORAGE_KEY = "mcpquick_auth_token";
export const HISTORY_PAGE_SIZE = 12;
export const MAX_PAYLOAD_CHARS = 1400;

export const PROVIDER_OPTIONS = [
  { value: "anthropic", label: "Anthropic" },
  { value: "openai", label: "OpenAI" },
  { value: "gemini", label: "Google Gemini" },
];

export const MODEL_OPTIONS = {
  anthropic: [
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
    "claude-opus-4-7",
  ],
  openai: [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4o-2024-08-06",
    "gpt-4o-mini-2024-07-18",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
  ],
  gemini: [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-1.0-pro",
  ],
};
