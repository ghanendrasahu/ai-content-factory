import axios from "axios";

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

  return data;
}

export default api;