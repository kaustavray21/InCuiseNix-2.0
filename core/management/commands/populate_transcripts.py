# transcripts/management/commands/populate_transcripts.py

from django.core.management.base import BaseCommand
from core.models import Video
from transcripts.services import get_transcript

class Command(BaseCommand):
    help = 'Fetches and saves transcripts for all videos that do not have one.'

    def handle(self, *args, **options):
        videos_without_transcripts = Video.objects.filter(transcript__isnull=True)
        
        if not videos_without_transcripts:
            self.stdout.write(self.style.SUCCESS('All videos already have transcripts.'))
            return

        self.stdout.write(f'Found {videos_without_transcripts.count()} videos without transcripts. Fetching...')

        for video in videos_without_transcripts:
            self.stdout.write(f'Fetching transcript for "{video.title}"...')
            try:
                # The get_transcript service will automatically save the new transcript
                get_transcript(video)
                self.stdout.write(self.style.SUCCESS(f'Successfully saved transcript for "{video.title}".'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to get transcript for "{video.title}": {e}'))

        self.stdout.write(self.style.SUCCESS('Finished populating transcripts.'))