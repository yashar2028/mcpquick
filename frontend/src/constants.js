export const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

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
    "claude-3-5-sonnet-latest",
    "claude-3-5-haiku-latest",
    "claude-3-opus-latest",
    "claude-3-5-sonnet-20240620",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
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
