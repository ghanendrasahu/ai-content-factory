import {
  createContext,
  useContext,
  useState,
  ReactNode,
} from "react";

/**
 * Single clip structure from backend AI
 */
interface Clip {
  start: number;
  end: number;
  score: number;
  title?: string;
  reason?: string;
}

/**
 * Full content pack from backend (future use)
 */
interface ContentPack {
  title?: string;
  description?: string;
  hashtags?: string[];
  caption?: string;
  top_clips?: any[];
}

interface JobContextType {
  jobId: string;
  setJobId: (id: string) => void;

  status: string;
  setStatus: (status: string) => void;

  step: string;
  setStep: (step: string) => void;

  progress: number;
  setProgress: (progress: number) => void;

  videoPath: string;
  setVideoPath: (path: string) => void;

  clips: Clip[];
  setClips: (clips: Clip[]) => void;

  selectedClip: Clip | null;
  setSelectedClip: (clip: Clip | null) => void;

  contentPack: ContentPack | null;
  setContentPack: (data: ContentPack | null) => void;
}

const JobContext = createContext<JobContextType | null>(null);

export function JobProvider({ children }: { children: ReactNode }) {
  const [jobId, setJobId] = useState("");
  const [status, setStatus] = useState("");
  const [step, setStep] = useState("");
  const [progress, setProgress] = useState(0);
  const [videoPath, setVideoPath] = useState("");

  const [clips, setClips] = useState<Clip[]>([]);
  const [selectedClip, setSelectedClip] = useState<Clip | null>(null);

  const [contentPack, setContentPack] = useState<ContentPack | null>(null);

  return (
    <JobContext.Provider
      value={{
        jobId,
        setJobId,

        status,
        setStatus,

        step,
        setStep,

        progress,
        setProgress,

        videoPath,
        setVideoPath,

        clips,
        setClips,

        selectedClip,
        setSelectedClip,

        contentPack,
        setContentPack,
      }}
    >
      {children}
    </JobContext.Provider>
  );
}

export function useJob() {
  const context = useContext(JobContext);

  if (!context) {
    throw new Error("useJob must be used inside JobProvider");
  }

  return context;
}