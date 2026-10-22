import { useState } from "react";

import { cancelJob, deleteJob, retryJob } from "../api/client";
import { useJob } from "../context/JobContext";
import { useTheme } from "../context/ThemeContext";
import { palette } from "../theme";

const RUNNING_STATES = [
  "queued",
  "downloading",
  "transcribing",
  "detecting",
  "content_generation",
  "rendering",
  "optimizing",
  "publishing",
];

const FINISHED_STATES = ["completed", "failed", "cancelled"];

function JobActions() {
  const { jobId, status, setStatus, setProgress } = useJob();
  const { theme } = useTheme();
  const colors = palette(theme);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  if (!jobId) return null;

  const isRunning = RUNNING_STATES.includes(status);
  const isFinished = FINISHED_STATES.includes(status);

  const buttonStyle = {
    padding: "8px 14px",
    marginRight: 8,
    borderRadius: 6,
    border: `1px solid ${colors.border}`,
    background: colors.surface,
    color: colors.text,
    cursor: busy ? "not-allowed" : "pointer",
    opacity: busy ? 0.6 : 1,
  };

  async function handleCancel() {
    setBusy(true);
    setMessage("");
    try {
      await cancelJob(jobId);
      setStatus("cancelled");
      setMessage("Cancellation requested - the job stops at the next stage.");
    } catch (error) {
      setMessage(`Cancel failed: ${(error as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleRetry() {
    setBusy(true);
    setMessage("");
    try {
      await retryJob(jobId);
      setStatus("queued");
      setProgress(0);
      setMessage("Retry started.");
    } catch (error) {
      setMessage(`Retry failed: ${(error as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    setBusy(true);
    setMessage("");
    try {
      await deleteJob(jobId);
      setMessage("Job deleted.");
      setStatus("");
      setProgress(0);
    } catch (error) {
      setMessage(`Delete failed: ${(error as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      style={{
        marginTop: 16,
        padding: 12,
        border: `1px solid ${colors.border}`,
        borderRadius: 8,
        background: colors.surface,
      }}
    >
      <div style={{ color: colors.muted, marginBottom: 8, fontSize: 13 }}>
        Job actions
      </div>

      <button style={buttonStyle} onClick={handleCancel} disabled={busy || !isRunning}>
        Cancel
      </button>
      <button style={buttonStyle} onClick={handleRetry} disabled={busy || !isFinished}>
        Retry
      </button>
      <button style={buttonStyle} onClick={handleDelete} disabled={busy}>
        Delete
      </button>

      {message ? (
        <div style={{ marginTop: 8, fontSize: 13, color: colors.muted }}>{message}</div>
      ) : null}
    </div>
  );
}

export default JobActions;
