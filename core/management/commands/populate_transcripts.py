import os
import csv
from django.conf import settings
from django.core.management.base import BaseCommand
from core.models import Video
from transcripts.models import Transcript

class Command(BaseCommand):
    help = 'Populates the database with cleaned transcripts from local CSV files, handling CSV format errors.'

    def handle(self, *args, **options):
        # Clears previously populated transcripts to ensure a clean import.
        populated_videos = Video.objects.filter(transcript__isnull=False)
        if populated_videos.exists():
            for video in populated_videos:
                video.transcript.delete()
            self.stdout.write(self.style.SUCCESS('Cleared previously populated transcripts to ensure a clean import.'))

        videos_to_process = Video.objects.all()
        self.stdout.write(f'Found {videos_to_process.count()} total videos. Populating with cleaned data...')
        
        populated_count = 0
        for video in videos_to_process:
            file_path = os.path.join(settings.MEDIA_ROOT, 'transcripts', video.course.title, f'{video.video_id}.csv')
            
            if not os.path.exists(file_path):
                self.stdout.write(self.style.WARNING(f'CSV file not found for "{video.title}". Skipping.'))
                continue

            try:
                full_transcript_content = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader) # Skip header
                    for i, row in enumerate(reader):
                        
                        if len(row) < 2:
                            self.stdout.write(self.style.WARNING(f'Skipping malformed row {i+2} in {file_path}'))
                            continue
                        
                        # --- CORRECTED LOGIC: Extract ONLY the start time ---
                        timestamp_data = row[0]
                        start_time = timestamp_data.split('-')[0].strip()
                        
                        raw_text = ",".join(row[1:])
                        
                        clean_text = raw_text
                        if ']' in raw_text:
                            clean_text = raw_text.split(']', 1)[-1].strip()
                        
                        full_transcript_content.append(f"{start_time} - {clean_text}")
                
                transcript_content_str = "\n".join(full_transcript_content)

                Transcript.objects.create(
                    video=video,
                    content=transcript_content_str
                )
                
                self.stdout.write(self.style.SUCCESS(f'Successfully populated cleaned transcript for "{video.title}".'))
                populated_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to process transcript for "{video.title}": {e}'))

        self.stdout.write(self.style.SUCCESS(f'Finished populating transcripts. Populated {populated_count} new transcripts.'))