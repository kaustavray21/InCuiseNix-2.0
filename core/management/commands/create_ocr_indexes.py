import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Q
from core.models import Video
from django_q.tasks import async_task

class Command(BaseCommand):
    help = 'Queues FAISS OCR index generation tasks.'

    def add_arguments(self, parser):
        parser.add_argument('--wipe', action='store_true', help='Wipe all OCR indexes and reset status.')

    def handle(self, *args, **options):
        # FIX 1: Correct Directory Name ('ocr' instead of 'ocr_indexes')
        ocr_index_root = os.path.join(settings.FAISS_INDEX_ROOT, 'ocr')

        if options['wipe']:
            self.stdout.write(self.style.WARNING(f'Wiping OCR indexes at {ocr_index_root}...'))
            
            if os.path.exists(ocr_index_root):
                shutil.rmtree(ocr_index_root)
                self.stdout.write("  - Deleted index directory.")
            else:
                self.stdout.write("  - Index directory not found (nothing to delete).")

            # Reset statuses to 'pending' so they are picked up by the loop below
            Video.objects.all().update(ocr_index_status='pending')
            self.stdout.write("  - Reset all video statuses to 'pending'.")

        # FIX 2: Include 'pending' in the filter to catch fresh imports
        videos_to_queue = Video.objects.filter(
            Q(ocr_index_status='none') | Q(ocr_index_status='failed') | Q(ocr_index_status='pending'),
            ocr_transcript_status='complete' 
        )

        self.stdout.write(f'Found {videos_to_queue.count()} videos for OCR indexing.')

        for video in videos_to_queue:
            # FIX 3: Use keyword argument matches your signals.py usage
            async_task('engine.tasks.task_generate_ocr_index', video_id=video.id)
            self.stdout.write(f'Queued OCR index for: {video.title}')