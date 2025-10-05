import os
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Video
from transcripts.services import get_transcript, save_transcript_to_csv, sanitize_filename

class Command(BaseCommand):
    help = 'Generates and saves transcripts for all videos in the database.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting transcript generation process...'))
        
        videos = Video.objects.all()
        total_videos = videos.count()
        new_transcripts_created = 0
        
        for index, video in enumerate(videos):
            self.stdout.write(f'Processing video {index + 1}/{total_videos}: "{video.title}"')
            
            try:
                # Sanitize the title to check for the transcript file
                sanitized_title = sanitize_filename(video.title)
                transcript_path = os.path.join(settings.MEDIA_ROOT, 'transcripts', f"{sanitized_title}.csv")

                if os.path.exists(transcript_path):
                    self.stdout.write(self.style.SUCCESS(f'Transcript for "{video.title}" already exists. Skipping.'))
                    continue

                # Pass both the URL and the title to the main get_transcript function
                transcript_data = get_transcript(video.video_url, video.title)
                
                if transcript_data:
                    # Pass the original title to the save function
                    save_transcript_to_csv(transcript_data, video.title)
                    self.stdout.write(self.style.SUCCESS(f'Successfully generated new transcript for "{video.title}"'))
                    new_transcripts_created += 1
                else:
                    self.stdout.write(self.style.WARNING(f'Could not generate transcript for "{video.title}"'))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'An error occurred for video "{video.title}": {e}'))

        self.stdout.write(self.style.SUCCESS(f'Finished. Created {new_transcripts_created} new transcript(s).'))