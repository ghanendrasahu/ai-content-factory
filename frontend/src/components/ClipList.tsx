import { useJob } from "../context/JobContext";
import type { Clip } from "../types/job";

function ClipList() {
  const { clips, setSelectedClip } = useJob();

  if (!clips || clips.length === 0) {
    return <div style={{ marginTop: 20 }}>No clips yet.</div>;
  }

  return (
    <div style={{ marginTop: 20 }}>
      <h3>Generated Clips</h3>

      <div style={{ display: "grid", gap: 10 }}>
        {clips
          .slice()
          .sort((a: Clip, b: Clip) => b.score - a.score)
          .map((clip: Clip, index: number) => (
            <div
              key={index}
              onClick={() => setSelectedClip(clip)}
              style={{
                padding: 12,
                border: "1px solid #ddd",
                borderRadius: 8,
                cursor: "pointer",
                background: "#fafafa",
              }}
            >
              <b>
                #{index + 1} • Score {clip.score}
              </b>

              <div style={{ fontSize: 12 }}>
                {clip.start}s → {clip.end}s
              </div>

              <div style={{ fontSize: 13, marginTop: 4 }}>
                {clip.title}
              </div>
            </div>
          ))}
      </div>
    </div>
  );
}

export default ClipList;