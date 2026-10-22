export interface Clip {
  start: number;
  end: number;
  score: number;
  title?: string;
  reason?: string;
}

export interface Job {
  job_id: string;
  status: string;
  step: string;
  progress: number;
  video_path?: string;
  final_video?: string;
  clip_outputs?: string[];
  clips?: Clip[];
  content_pack?: {
    title?: string;
    description?: string;
    hashtags?: string[];
  } | null;
  thumbnail_path?: string | null;
  subtitle_path?: string | null;
  published_video?: {
    video_id: string;
    url: string;
    privacy_status: string;
  } | null;
  error?: string | null;
  failure_report?: Record<string, unknown> | null;
}

export interface AppSettings {
  app: {
    name: string;
    version: string;
    debug: boolean;
  };
  pipeline: {
    engine: string;
    clip_selection_count: number;
    min_clip_duration_seconds: number;
    max_clip_duration_seconds: number;
    target: { width: number; height: number };
  };
  features: {
    subtitles: boolean;
    thumbnails: boolean;
    platform_exports: boolean;
    youtube_publish: boolean;
    gpu: boolean;
  };
  media: {
    subtitle_format: string;
    thumbnail_template: string;
    thumbnail_size: { width: number; height: number };
  };
  integrations: {
    llm_configured: boolean;
    youtube_configured: boolean;
    api_key_required: boolean;
  };
}

export type Theme = "light" | "dark";
