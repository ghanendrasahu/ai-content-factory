import { useState } from "react";
import {
  createJob,
  downloadVideo,
  processJob,
} from "../api/client";

function UrlForm() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleGenerate() {
    if (!url) {
      alert("Please enter a YouTube URL.");
      return;
    }

    try {
      setLoading(true);

      // 1. Create Job
      const job = await createJob();

      // 2. Download
      await downloadVideo(job.job_id, url);

      // 3. Start Background Pipeline
      await processJob(job.job_id);

      alert(`Pipeline started!\nJob ID: ${job.job_id}`);
    } catch (error) {
      console.error(error);
      alert("Something went wrong.");
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
          marginTop: "15px",
          padding: "12px 20px",
        }}
      >
        {loading ? "Starting..." : "Generate"}
      </button>
    </div>
  );
}

export default UrlForm;