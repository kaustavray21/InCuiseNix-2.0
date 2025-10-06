import os
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Video
from transcripts.services import get_transcript, save_transcript_to_csv, sanitize_filename

class Command(BaseCommand):
    help = 'Generates and saves transcripts for all videos, naming files by video_id.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting transcript generation process...'))
        
        videos = Video.objects.select_related('course').all()
        total_videos = videos.count()
        new_transcripts_created = 0
        
        for index, video in enumerate(videos):
            self.stdout.write(f'Processing video {index + 1}/{total_videos}: "{video.title}" (ID: {video.video_id})')
            
            try:
                sanitized_course_title = sanitize_filename(video.course.title)
                
                # Check for existing transcript file using video_id
                transcript_path = os.path.join(
                    settings.MEDIA_ROOT, 
                    'transcripts', 
                    sanitized_course_title, 
                    f"{video.video_id}.csv"
                )

                if os.path.exists(transcript_path):
                    self.stdout.write(self.style.SUCCESS(f'Transcript for "{video.title}" already exists. Skipping.'))
                    continue

                # Pass the entire video object to the service functions
                transcript_data = get_transcript(video)
                
                if transcript_data:
                    save_transcript_to_csv(transcript_data, video)
                    self.stdout.write(self.style.SUCCESS(f'Successfully generated new transcript for "{video.title}"'))
                    new_transcripts_created += 1
                else:
                    self.stdout.write(self.style.WARNING(f'Could not generate transcript for "{video.title}"'))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'An error occurred for video "{video.title}": {e}'))

        self.stdout.write(self.style.SUCCESS(f'Finished. Created {new_transcripts_created} new transcript(s).'))