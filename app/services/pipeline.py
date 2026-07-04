from app.services.download_service import DownloadService
from app.ai.transcriber import Transcriber
from app.ai.clip_detector import ClipDetector
from app.services.clip_renderer import ClipRenderer
from app.services.video_optimizer import VideoOptimizer
from app.logger import logger


class Pipeline:

    @staticmethod
    def run(job):

        logger.info(f"Pipeline started for job: {job.job_id}")

        # -------------------
        # INIT
        # -------------------
        job.status = "processing"
        job.step = "starting"
        job.progress = 0

        # -------------------
        # 1. Download
        # -------------------
        logger.info("Step 1: Download")

        job.step = "downloading"
        job.progress = 10

        if not job.video_path:
            logger.info("Downloading video...")
            _, video_path = DownloadService.download(job.video_url)
            job.video_path = video_path
        else:
            logger.info("Video already downloaded. Skipping download.")

        job.status = "downloaded"
        logger.info("✓ Download completed")

        # -------------------
        # 2. Transcribe
        # -------------------
        logger.info("Step 2: Transcribe")

        job.step = "transcribing"
        job.progress = 30

        result = Transcriber.transcribe(job.video_path)

        job.transcript = result["transcript"]
        job.status = "transcribed"

        logger.info("✓ Transcription completed")

        # -------------------
        # 3. Detect Clips
        # -------------------
        logger.info("Step 3: Detect Clips")

        job.step = "detecting_clips"
        job.progress = 50

        clips = ClipDetector.detect(job.transcript)

        job.clips = clips
        job.status = "clips_detected"

        logger.info(f"✓ {len(clips)} clips detected")

        # -------------------
        # 4. Render Clips
        # -------------------
        logger.info("Step 4: Render Clips")

        job.step = "rendering_clips"
        job.progress = 70

        clip_outputs = ClipRenderer.render(job.video_path, job.clips)

        job.clip_outputs = clip_outputs
        job.status = "clips_rendered"

        logger.info("✓ Clips rendered")

        # -------------------
        # 5. Vertical Video
        # -------------------
        logger.info("Step 5: Make Vertical")

        job.step = "making_vertical"
        job.progress = 90

        vertical_output = f"outputs/{job.job_id}_vertical.mp4"

        final_video = VideoOptimizer.make_vertical(
            job.video_path,
            vertical_output,
            job.transcript
        )

        job.final_video = final_video

        logger.info("✓ Vertical video created")

        # -------------------
        # DONE
        # -------------------
        job.step = "completed"
        job.progress = 100
        job.status = "completed"

        logger.info(f"✓ Pipeline completed successfully for job: {job.job_id}")

        return job