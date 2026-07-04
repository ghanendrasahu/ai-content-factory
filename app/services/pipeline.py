from pathlib import Path
from time import perf_counter

from app.ai.clip_detector import ClipDetector
from app.ai.content_packager import ContentPackager
from app.ai.transcriber import Transcriber
from app.core.paths import OUTPUT_DIR, cleanup_job_temp_files, ensure_directories
from app.logger import logger
from app.services.clip_renderer import ClipRenderer
from app.services.download_service import DownloadService
from app.services.video_optimizer import VideoOptimizer


class Pipeline:
    @staticmethod
    def _set_state(job, status: str, progress: int):
        job.set_state(status, progress)

    @staticmethod
    def run(job):
        ensure_directories()
        pipeline_started_at = perf_counter()

        logger.info(f"Pipeline started for job: {job.job_id}")

        try:
            Pipeline._set_state(job, "queued", 0)
            job.error = None

            logger.info("Step 1/5 downloading")
            Pipeline._set_state(job, "downloading", 10)

            if not job.video_url and not job.video_path:
                raise ValueError("No video URL provided")

            if not job.video_path:
                logger.info("Downloading video...")
                _, video_path = DownloadService.download(job.video_url)
                job.video_path = video_path
            else:
                logger.info("Video already downloaded. Skipping download.")

            video_path = Pipeline._require_file(job.video_path, "Downloaded video")
            logger.info("Download completed: %s", video_path)

            logger.info("Step 2/5 transcribing")
            Pipeline._set_state(job, "transcribing", 30)

            result = Transcriber.transcribe(video_path)
            job.transcript = result["transcript"]

            if not job.transcript:
                raise ValueError("Transcription produced no segments")

            logger.info("Transcription completed: %s segments", len(job.transcript))

            logger.info("Step 3/5 detecting")
            Pipeline._set_state(job, "detecting", 50)

            clips = ClipDetector.detect(job.transcript)
            if not clips:
                raise ValueError("No clips detected")

            job.clips = clips
            job.content_pack = ContentPackager.generate(job.transcript, clips)
            logger.info("Clip detection completed: %s clips", len(clips))

            logger.info("Step 4/5 rendering")
            Pipeline._set_state(job, "rendering", 70)

            clip_outputs = ClipRenderer.render(
                video_path,
                job.clips,
                job.job_id,
            )

            if not clip_outputs:
                raise ValueError("No clips were rendered")

            for clip_output in clip_outputs:
                Pipeline._require_file(clip_output, "Rendered clip")

            job.clip_outputs = clip_outputs
            logger.info("Rendering completed: %s clips", len(clip_outputs))

            logger.info("Step 5/5 finalizing")
            Pipeline._set_state(job, "optimizing", 90)

            vertical_output = OUTPUT_DIR / f"{job.job_id}_vertical.mp4"
            source_clip = Pipeline._require_file(clip_outputs[0], "Rendered clip")

            final_video = VideoOptimizer.make_vertical(
                source_clip,
                str(vertical_output),
                job.transcript,
            )

            job.final_video = Pipeline._require_file(final_video, "Vertical video")

            Pipeline._set_state(job, "completed", 100)
            cleanup_job_temp_files(job.job_id)

            logger.info(
                "Pipeline completed successfully for job=%s elapsed=%.2fs",
                job.job_id,
                perf_counter() - pipeline_started_at,
            )

            return job

        except Exception as e:
            job.set_state("failed", job.progress)
            job.error = str(e)
            cleanup_job_temp_files(job.job_id)
            logger.exception(f"Pipeline failed for job: {job.job_id}")
            raise

    @staticmethod
    def _require_file(path: str, label: str):
        if not path:
            raise FileNotFoundError(f"{label} path is missing")

        file_path = Path(path)
        if not file_path.is_file() or file_path.stat().st_size == 0:
            raise FileNotFoundError(f"{label} not found: {file_path}")

        return str(file_path)
