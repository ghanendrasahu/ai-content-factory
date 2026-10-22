import axios from "axios";

import type { AppSettings, Job } from "../types/job";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

export async function createJob() {
  const { data } = await api.post("/jobs");
  return data;
}

export async function downloadVideo(jobId: string, url: string) {
  const { data } = await api.post(`/jobs/${jobId}/download`, {
    url,
  });

  return data;
}

export async function processJob(jobId: string) {
  const { data } = await api.post(`/jobs/${jobId}/process`);

  return data;
}

export async function getJob(jobId: string) {
  const { data } = await api.get(`/jobs/${jobId}`);

  return data as Job;
}

/** Re-run a failed or cancelled job with the same inputs. */
export async function retryJob(jobId: string) {
  const { data } = await api.post(`/jobs/${jobId}/retry`);

  return data;
}

/** Request cancellation - honoured at the next stage boundary. */
export async function cancelJob(jobId: string) {
  const { data } = await api.post(`/jobs/${jobId}/cancel`);

  return data;
}

/** Remove a job from the store. */
export async function deleteJob(jobId: string) {
  const { data } = await api.delete(`/jobs/${jobId}`);

  return data;
}

/** Runtime feature flags and limits (never secrets). */
export async function getSettings(): Promise<AppSettings> {
  const { data } = await api.get("/settings");

  return data as AppSettings;
}

export default api;
