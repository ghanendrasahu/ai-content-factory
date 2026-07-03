from app.services.download_service import DownloadService
from app.ai.transcriber import Transcriber
from app.ai.clip_detector import ClipDetector
from app.services.clip_renderer import ClipRenderer
from app.services.video_optimizer import VideoOptimizer


class Pipeline:

    @staticmethod
    def run(job):

        print("=" * 50)
        print(f"Pipeline started for Job: {job.job_id}")

        # -------------------
        # INIT
        # -------------------
        job.status = "processing"
        job.step = "starting"
        job.progress = 0

        # -------------------
        # 1. Download
        # -------------------
        print("Step 1: Download")

        job.step = "downloading"
        job.progress = 10

        if not job.video_path:
            print("Downloading video...")
            _, video_path = DownloadService.download(job.video_url)
            job.video_path = video_path
        else:
            print("Video already downloaded. Skipping download.")

        job.status = "downloaded"
        print("✓ Download completed")

        # -------------------
        # 2. Transcribe
        # -------------------
        print("Step 2: Transcribe")

        job.step = "transcribing"
        job.progress = 30

        result = Transcriber.transcribe(job.video_path)

        job.transcript = result["transcript"]
        job.status = "transcribed"

        print("✓ Transcription completed")

        # -------------------
        # 3. Detect Clips
        # -------------------
        print("Step 3: Detect Clips")

        job.step = "detecting_clips"
        job.progress = 50

        clips = ClipDetector.detect(job.transcript)

        job.clips = clips
        job.status = "clips_detected"

        print(f"✓ {len(clips)} clips detected")

        # -------------------
        # 4. Render Clips
        # -------------------
        print("Step 4: Render Clips")

        job.step = "rendering_clips"
        job.progress = 70

        clip_outputs = ClipRenderer.render(job.video_path, job.clips)

        job.clip_outputs = clip_outputs
        job.status = "clips_rendered"

        print("✓ Clips rendered")

        # -------------------
        # 5. Vertical Video
        # -------------------
        print("Step 5: Make Vertical")

        job.step = "making_vertical"
        job.progress = 90

        vertical_output = f"outputs/{job.job_id}_vertical.mp4"

        final_video = VideoOptimizer.make_vertical(
            job.video_path,
            vertical_output,
            job.transcript
        )

        job.final_video = final_video

        print("✓ Vertical video created")

        # -------------------
        # DONE
        # -------------------
        job.step = "completed"
        job.progress = 100
        job.status = "completed"

        print("✓ Pipeline completed successfully")
        print("=" * 50)

        return job