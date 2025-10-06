import os
import csv
from django.conf import settings
from django.core.management.base import BaseCommand
from core.models import Video
from transcripts.models import Transcript, TranscriptLine

class Command(BaseCommand):
    help = 'Populates the database with detailed transcript lines (start and end times).'

    def handle(self, *args, **options):
        # Clear all old transcript data to ensure a fresh start
        Transcript.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Cleared all previously populated transcripts.'))

        videos_to_process = Video.objects.all()
        self.stdout.write(f'Found {videos_to_process.count()} total videos. Populating transcripts...')
        
        for video in videos_to_process:
            file_path = os.path.join(settings.MEDIA_ROOT, 'transcripts', video.course.title, f'{video.video_id}.csv')
            
            if not os.path.exists(file_path):
                self.stdout.write(self.style.WARNING(f'CSV file not found for "{video.title}". Skipping.'))
                continue

            try:
                # Create a single Transcript container for the video
                transcript_container = Transcript.objects.create(video=video)
                
                lines_to_create = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader) # Skip header
                    for row in reader:
                        if len(row) < 2:
                            continue
                        
                        # Parse start and end times
                        timestamps = row[0].split('-')
                        start_time = float(timestamps[0].strip())
                        end_time = float(timestamps[1].strip()) if len(timestamps) > 1 else None

                        # Clean the text
                        raw_text = ",".join(row[1:])
                        clean_text = raw_text.split(']', 1)[-1].strip() if ']' in raw_text else raw_text
                        
                        lines_to_create.append(
                            TranscriptLine(
                                transcript=transcript_container,
                                start_time=start_time,
                                end_time=end_time,
                                text=clean_text
                            )
                        )
                
                # Create all lines for this video in one efficient database query
                if lines_to_create:
                    TranscriptLine.objects.bulk_create(lines_to_create)
                    self.stdout.write(self.style.SUCCESS(f'Successfully populated transcript for "{video.title}".'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to process transcript for "{video.title}": {e}'))

        self.stdout.write(self.style.SUCCESS('Finished populating all transcripts.'))