import { useEffect, useRef } from "react";
import { useJob } from "../context/JobContext";

function ClipPreview() {
  const { selectedClip, videoPath } = useJob();
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const video = videoRef.current;

    if (!video || !selectedClip) return;

    const handleTimeUpdate = () => {
      if (video.currentTime >= selectedClip.end) {
        video.pause();
      }
    };

    video.addEventListener("timeupdate", handleTimeUpdate);

    return () => {
      video.removeEventListener("timeupdate", handleTimeUpdate);
    };
  }, [selectedClip]);

  if (!selectedClip || !videoPath) {
    return (
      <div style={{ marginTop: 30 }}>
        <h3>Clip Preview</h3>
        <p>Select a clip to preview</p>
      </div>
    );
  }

  const src = `http://127.0.0.1:8000/${videoPath}`;

  return (
    <div style={{ marginTop: 30 }}>
      <h3>Clip Preview</h3>

      <div style={{ fontSize: 13, marginBottom: 8 }}>
        {selectedClip.start}s → {selectedClip.end}s
      </div>

      <video
        ref={videoRef}
        controls
        autoPlay
        onLoadedMetadata={() => {
          if (videoRef.current) {
            videoRef.current.currentTime = selectedClip.start;
            videoRef.current.play();
          }
        }}
        style={{
          width: "320px",
          borderRadius: 10,
        }}
      >
        <source src={src} type="video/mp4" />
      </video>
    </div>
  );
}

export default ClipPreview;