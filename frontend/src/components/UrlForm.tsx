import { useState } from "react";
import {
  createJob,
  downloadVideo,
  processJob,
} from "../api/client";

import { useJob } from "../context/JobContext";

function UrlForm() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);

  const {
  setJobId,
  setStatus,
  setStep,
  setProgress,
  } = useJob();

  async function handleGenerate() {
    if (!url.trim()) {
      alert("Please enter a YouTube URL.");
      return;
    }

    try {
      setLoading(true);

      // Reset previous state
      setStatus("creating");
      setStep("Creating Job");
      setProgress(0);

      // Create Job
      const job = await createJob();

      setJobId(job.job_id);

      // Download
      setStatus("downloading");
      setStep("Downloading Video");
      setProgress(10);

      await downloadVideo(job.job_id, url);

      // Start pipeline
      await processJob(job.job_id);

      setStatus("processing");
      setStep("Pipeline Started");
      setProgress(15);

    } catch (error) {
      console.error(error);

      setStatus("failed");
      setStep("Error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ marginTop: 30, marginBottom: 30 }}>
      <h2>YouTube URL</h2>

      <input
        type="text"
        placeholder="Paste YouTube URL..."
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        style={{
          width: "100%",
          padding: "12px",
          fontSize: "16px",
        }}
      />

      <button
        onClick={handleGenerate}
        disabled={loading}
        style={{
          marginTop: 15,
          padding: "12px 20px",
        }}
      >
        {loading ? "Starting..." : "Generate"}
      </button>
    </div>
  );
}

export default UrlForm;