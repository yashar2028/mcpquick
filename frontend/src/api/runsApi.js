import { apiClient, authConfig } from "./client";

export async function listRuns(token, params) {
  const response = await apiClient.get("/v1/runs", {
    ...authConfig(token),
    params,
  });
  return response.data;
}

export async function createRun(token, payload) {
  const response = await apiClient.post("/v1/runs", payload, authConfig(token));
  return response.data;
}

export async function getRun(token, runId) {
  const response = await apiClient.get(`/v1/runs/${runId}`, authConfig(token));
  return response.data;
}

export async function getRunEvents(token, runId, limit = 250) {
  const response = await apiClient.get(`/v1/runs/${runId}/events`, {
    ...authConfig(token),
    params: { limit },
  });
  return response.data;
}

export async function getRunReport(token, runId) {
  const response = await apiClient.get(`/v1/runs/${runId}/report`, authConfig(token));
  return response.data;
}

export async function getRunLogs(token, runId) {
  const response = await apiClient.get(`/v1/runs/${runId}/logs`, authConfig(token));
  return response.data;
}

export async function deleteRun(token, runId) {
  await apiClient.delete(`/v1/runs/${runId}`, authConfig(token));
}

export async function retryRun(token, runId, apiKey) {
  const response = await apiClient.post(
    `/v1/runs/${runId}/retry`,
    { api_key: apiKey },
    authConfig(token)
  );
  return response.data;
}
