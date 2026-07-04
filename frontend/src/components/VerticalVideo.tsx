import { useJob } from "../context/JobContext";

function VerticalVideo() {
  const { videoPath } = useJob();

  if (!videoPath) {
    return (
      <div style={{ marginTop: 40 }}>
        <h2>Vertical Video</h2>
        <p>No video generated.</p>
      </div>
    );
  }

  return (
    <div style={{ marginTop: 40 }}>
      <h2>Vertical Video</h2>

      <video
        width="300"
        height="533"
        controls
        style={{
          borderRadius: 10,
          marginTop: 10,
        }}
      >
        <source
          src={`http://127.0.0.1:8000/${videoPath}`}
          type="video/mp4"
        />
      </video>
    </div>
  );
}

export default VerticalVideo;