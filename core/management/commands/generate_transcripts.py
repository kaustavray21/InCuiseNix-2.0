import os
import re
import csv
import whisper
import yt_dlp
from django.conf import settings
from django.core.management.base import BaseCommand
from core.models import Video, Transcript

def sanitize_filename(title):
    """Sanitizes a string to be used as a valid filename or directory name."""
    return re.sub(r'[\\/*?:"<>|]', "", title)

class Command(BaseCommand):
    help = 'Downloads new YouTube videos, transcribes them using Whisper, and saves them to the core_transcript table.'

    def handle(self, *args, **options):
        self.stdout.write('Starting transcript generation process...')

        videos_to_process = Video.objects.filter(transcripts__isnull=True).distinct()
        
        if not videos_to_process:
            self.stdout.write(self.style.SUCCESS('All videos already have transcripts. No new transcripts to generate.'))
            return

        self.stdout.write(f'Found {videos_to_process.count()} videos without transcripts.')

        # Load the Whisper model once
        try:
            whisper_model = whisper.load_model("base")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to load Whisper model: {e}"))
            return

        for video in videos_to_process:
            self.stdout.write(f'\n--- Processing video: "{video.title}" ---')

            # 1. Download Video
            video_path = self.download_video(video)
            if not video_path:
                continue

            # 2. Transcribe Video
            transcript_data = self.transcribe_with_whisper(video_path, whisper_model)
            if not transcript_data:
                continue

            # 3. Save Transcript to Database
            self.save_transcript_to_db(transcript_data, video)
            
            # 4. (Optional) Clean up downloaded video file
            try:
                os.remove(video_path)
                self.stdout.write(self.style.SUCCESS(f'  -> Cleaned up downloaded file: {os.path.basename(video_path)}'))
            except OSError as e:
                self.stdout.write(self.style.WARNING(f'  -> Could not remove video file: {e}'))

        self.stdout.write(self.style.SUCCESS('\nFinished transcript generation process.'))

    def download_video(self, video):
        """Downloads a video file for a given Video object."""
        self.stdout.write('  -> Downloading video...')
        course_dir = sanitize_filename(video.course.title)
        download_dir = os.path.join(settings.MEDIA_ROOT, 'downloads', course_dir)
        os.makedirs(download_dir, exist_ok=True)
        
        output_template = os.path.join(download_dir, f'{video.youtube_id}.%(ext)s')

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video.video_url, download=True)
                # The final path will have the .mp3 extension after post-processing
                final_filepath = os.path.join(download_dir, f'{video.youtube_id}.mp3')
                if os.path.exists(final_filepath):
                    self.stdout.write(self.style.SUCCESS(f'  -> Video downloaded successfully: {os.path.basename(final_filepath)}'))
                    return final_filepath
                else:
                    self.stdout.write(self.style.ERROR('  -> Downloaded file not found after processing.'))
                    return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  -> Error downloading video: {e}'))
            return None

    def transcribe_with_whisper(self, audio_path, model):
        """Transcribes an audio file using the pre-loaded Whisper model."""
        self.stdout.write('  -> Transcribing with Whisper...')
        try:
            result = model.transcribe(audio_path, fp16=False)
            self.stdout.write(self.style.SUCCESS('  -> Transcription successful.'))
            return result.get('segments', [])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  -> Error during transcription: {e}'))
            return None

    def save_transcript_to_db(self, transcript_data, video):
        """Saves transcript segments to the core_transcript table."""
        self.stdout.write('  -> Saving transcript to database...')
        try:
            lines_to_create = []
            for segment in transcript_data:
                lines_to_create.append(
                    Transcript(
                        video=video,
                        course=video.course,
                        start=segment['start'],
                        content=segment['text'].strip()
                    )
                )
            
            if lines_to_create:
                Transcript.objects.bulk_create(lines_to_create)
                self.stdout.write(self.style.SUCCESS(f'  -> Saved {len(lines_to_create)} transcript lines.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  -> Error saving to database: {e}'))