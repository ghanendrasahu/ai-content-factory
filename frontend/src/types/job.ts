export interface Job {
  job_id: string;
  status: string;
  step: string;
  progress: number;
  video_path?: string;
}