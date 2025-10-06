from django.core.management.base import BaseCommand
from core.models import Video
from transcripts.models import TranscriptLine

class Command(BaseCommand):
    help = 'Diagnoses the transcript data for a specific video.'

    def add_arguments(self, parser):
        parser.add_argument('video_id', type=str, help='The video_id of the video to diagnose.')

    def handle(self, *args, **options):
        video_id = options['video_id']
        self.stdout.write(self.style.SUCCESS(f"--- Running diagnostics for video_id: {video_id} ---"))

        try:
            video = Video.objects.get(video_id=video_id)
            self.stdout.write(f"Found video: '{video.title}'")
        except Video.DoesNotExist:
            self.stdout.write(self.style.ERROR("Video not found in the database."))
            return

        lines = TranscriptLine.objects.filter(transcript__video=video)

        if not lines.exists():
            self.stdout.write(self.style.ERROR("No transcript lines found for this video in the database."))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {lines.count()} transcript lines. Displaying the first 5:"))
        for line in lines[:5]:
            self.stdout.write(f"  - Start: {line.start_time}, End: {line.end_time}, Text: '{line.text[:50]}...'")