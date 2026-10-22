from pathlib import Path
from time import perf_counter

from app.ai.clip_detector import ClipDetector
from app.ai.content_packager import ContentPackager
from app.ai.transcriber import Transcriber
from app.core.paths import OUTPUT_DIR, cleanup_job_temp_files, ensure_directories
from app.core.cancellation import JobCancelled, check_cancelled
from app.logger import logger
from app.config import settings
from app.services.self_healing import RecoveryStrategies, RetryManager
from app.services.clip_renderer import ClipRenderer
from app.services.download_service import DownloadService
from app.services.platform_export import PlatformExportPresets
from app.services.progress import ProgressTracker
from app.services.subtitles import SubtitleService
from app.services.thumbnail import ThumbnailGenerator
from app.services.video_optimizer import VideoOptimizer
from app.services.youtube_publisher import YouTubePublisher


class Pipeline:
    @staticmethod
    def _set_state(job, status: str, progress: int):
        job.set_state(status, progress)

    @staticmethod
    def run(job):
        ensure_directories()
        pipeline_started_at = perf_counter()
        tracker = ProgressTracker()
        retry = RetryManager()

        logger.info(f"Pipeline started for job: {job.job_id}")

        try:
            job.apply_progress(tracker.snapshot("queued", 0))
            job.error = None

            logger.info("Step 1/5 downloading")
            job.apply_progress(tracker.snapshot("downloading", 10))
            check_cancelled(job)

            if not job.video_url and not job.video_path:
                raise ValueError("No video URL provided")

            if not job.video_path:
                logger.info("Downloading video...")
                _, video_path = retry.run(
                    lambda: DownloadService.download(job.video_url),
                    "download",
                )
                job.video_path = video_path
            else:
                logger.info("Video already downloaded. Skipping download.")

            video_path = Pipeline._require_file(job.video_path, "Downloaded video")
            logger.info("Download completed: %s", video_path)

            logger.info("Step 2/5 transcribing")
            job.apply_progress(tracker.snapshot("transcribing", 30))
            check_cancelled(job)

            result = retry.run(lambda: Transcriber.transcribe(video_path), "whisper")
            job.transcript = result["transcript"]

            if not job.transcript:
                raise ValueError("Transcription produced no segments")

            logger.info("Transcription completed: %s segments", len(job.transcript))

            logger.info("Step 3/5 detecting")
            job.apply_progress(tracker.snapshot("detecting", 45))
            check_cancelled(job)

            clips = retry.run(lambda: ClipDetector.detect(job.transcript), "detect")
            if not clips:
                raise ValueError("No clips detected")

            job.clips = clips
            logger.info("Clip detection completed: %s clips", len(clips))

            logger.info("Step 4/6 content_generation")
            job.apply_progress(tracker.snapshot("content_generation", 55))
            check_cancelled(job)
            job.content_pack = retry.run(
                lambda: ContentPackager.generate(job.transcript, clips),
                "content_generation",
            )

            logger.info("Step 4/5 rendering")
            job.apply_progress(tracker.snapshot("rendering", 70))
            check_cancelled(job)

            clip_outputs = retry.run(
                lambda: ClipRenderer.render(
                    video_path,
                    job.clips,
                    job.job_id,
                ),
                "render",
            )

            if not clip_outputs:
                raise ValueError("No clips were rendered")

            for clip_output in clip_outputs:
                Pipeline._require_file(clip_output, "Rendered clip")

            job.clip_outputs = clip_outputs
            logger.info("Rendering completed: %s clips", len(clip_outputs))

            logger.info("Step 5/5 finalizing")
            job.apply_progress(tracker.snapshot("optimizing", 90))
            check_cancelled(job)

            vertical_output = OUTPUT_DIR / f"{job.job_id}_vertical.mp4"
            source_clip = Pipeline._require_file(clip_outputs[0], "Rendered clip")

            final_video = retry.run(
                lambda: VideoOptimizer.make_vertical(
                    source_clip,
                    str(vertical_output),
                    job.transcript,
                ),
                "optimize",
            )

            job.final_video = Pipeline._require_file(final_video, "Vertical video")

            if settings.ENABLE_SUBTITLES and job.transcript:
                subtitle_path = OUTPUT_DIR / f"{job.job_id}.srt"
                job.subtitle_path = SubtitleService.generate(
                    job.transcript,
                    subtitle_path,
                )
                subtitled_output = OUTPUT_DIR / f"{job.job_id}_vertical_subtitled.mp4"
                job.final_video = retry.run(
                    lambda: SubtitleService.burn(
                        job.final_video,
                        job.subtitle_path,
                        str(subtitled_output),
                    ),
                    "subtitles",
                )

            if settings.ENABLE_THUMBNAILS:
                title = (job.content_pack or {}).get("title", "AI Content Factory")
                job.thumbnail_path = ThumbnailGenerator.generate(
                    job.final_video,
                    title,
                    job.job_id,
                )

            if settings.ENABLE_PLATFORM_EXPORTS:
                job.platform_exports = {
                    key: preset.__dict__
                    for key, preset in PlatformExportPresets.all().items()
                }

            if settings.YOUTUBE_PUBLISH_ENABLED and job.publish_requested:
                logger.info("Step 6/6 publishing to YouTube")
                job.apply_progress(tracker.snapshot("publishing", 95))

                metadata = YouTubePublisher.build_metadata(content_pack=job.content_pack)
                published = retry.run(
                    lambda: YouTubePublisher.publish(job.final_video, metadata),
                    "publish",
                )
                job.published_video = published.to_dict()
                logger.info(
                    "Published to YouTube: id=%s url=%s",
                    job.published_video.get("video_id"),
                    job.published_video.get("url"),
                )

            job.apply_progress(tracker.snapshot("completed", 100))
            cleanup_job_temp_files(job.job_id)

            logger.info(
                "Pipeline completed successfully for job=%s elapsed=%.2fs",
                job.job_id,
                perf_counter() - pipeline_started_at,
            )

            return job

        except JobCancelled:
            job.set_state("cancelled", job.progress)
            job.error = "cancelled by user"
            cleanup_job_temp_files(job.job_id)
            logger.info("Pipeline cancelled for job: %s", job.job_id)
            raise
        except Exception as e:
            job.set_state("failed", job.progress)
            job.error = str(e)
            job.failure_report = RecoveryStrategies.diagnose(e).__dict__
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
