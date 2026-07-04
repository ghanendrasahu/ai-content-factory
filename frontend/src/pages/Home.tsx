import { useEffect } from "react";

import Header from "../components/Header";
import UrlForm from "../components/UrlForm";
import ProgressCard from "../components/ProgressCard";
import ClipList from "../components/ClipList";
import VerticalVideo from "../components/VerticalVideo";
import ClipPreview from "../components/ClipPreview";
import ContentPack from "../components/ContentPack";

import { getJob } from "../api/client";
import { useJob } from "../context/JobContext";

function Home() {
  const {
    jobId,
    setStatus,
    setStep,
    setProgress,
    setVideoPath,
    setClips,
    setContentPack,
  } = useJob();

  useEffect(() => {
    if (!jobId) return;

    const timer = setInterval(async () => {
      try {
        const job = await getJob(jobId);

        setStatus(job.status);
        setStep(job.step);
        setProgress(job.progress);

        // video
        if (job.video_path) {
          setVideoPath(job.video_path);
        }

        // clips (IMPORTANT FIX)
        if (Array.isArray(job.clips) && job.clips.length > 0) {
          setClips(job.clips);
        }

        // content pack
        if (job.content_pack) {
          setContentPack(job.content_pack);
        }

        // stop polling
        if (
          job.status === "completed" ||
          job.status.startsWith("failed")
        ) {
          clearInterval(timer);
        }
      } catch (err) {
        console.error(err);
        clearInterval(timer);
      }
    }, 2000);

    return () => clearInterval(timer);
  }, [
    jobId,
    setStatus,
    setStep,
    setProgress,
    setVideoPath,
    setClips,
    setContentPack,
  ]);

  return (
    <div
      style={{
        maxWidth: "1000px",
        margin: "40px auto",
        padding: "20px",
        fontFamily: "Arial",
      }}
    >
      <Header />
      <UrlForm />
      <ProgressCard />
      <ClipList />
      <ClipPreview />
      <ContentPack />
      <VerticalVideo />
    </div>
  );
}

export default Home;