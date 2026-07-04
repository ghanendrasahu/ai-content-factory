import { useJob } from "../context/JobContext";

function ProgressCard() {
  const {
    status,
    step,
    progress,
  } = useJob();

  if (!status) {
    return (
      <div style={{ marginTop: 40 }}>
        <h2>Progress</h2>
        <p>No job running.</p>
        <hr />
      </div>
    );
  }

  return (
    <div
      style={{
        marginTop: 40,
        padding: 20,
        border: "1px solid #ddd",
        borderRadius: 8,
      }}
    >
      <h2>Progress</h2>

      <p>
        <strong>Status:</strong> {status}
      </p>

      <p>
        <strong>Step:</strong> {step}
      </p>

      <p>
        <strong>Progress:</strong> {progress}%
      </p>

      <div
        style={{
          width: "100%",
          height: 18,
          background: "#ddd",
          borderRadius: 10,
          overflow: "hidden",
          marginTop: 15,
        }}
      >
        <div
          style={{
            width: `${progress}%`,
            height: "100%",
            background: "#4CAF50",
            transition: "width 0.5s ease",
          }}
        />
      </div>
    </div>
  );
}

export default ProgressCard;