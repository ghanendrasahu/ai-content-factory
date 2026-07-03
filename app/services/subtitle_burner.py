from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip


class SubtitleBurner:

    @staticmethod
    def burn(video_path: str, transcript: list, output_path: str):

        video = VideoFileClip(video_path)

        subtitles = []

        for item in transcript:

            txt = (
                TextClip(
                    item["text"],
                    fontsize=60,
                    color="white",
                    stroke_color="black",
                    stroke_width=2
                )
                .set_position(("center", "bottom"))
                .set_start(item["start"])
                .set_end(item["end"])
            )

            subtitles.append(txt)

        final = CompositeVideoClip([video] + subtitles)

        final.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac"
        )

        return output_path