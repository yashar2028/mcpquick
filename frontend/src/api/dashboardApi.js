import { apiClient, authConfig } from "./client";

export async function getDashboardSummary(token) {
  const response = await apiClient.get("/v1/dashboard/summary", authConfig(token));
  return response.data;
}
