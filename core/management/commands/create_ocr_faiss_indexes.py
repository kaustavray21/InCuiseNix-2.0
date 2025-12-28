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
        if options['wipe']:
            self.stdout.write(self.style.WARNING('Wiping OCR indexes...'))
            index_dir = os.path.join(settings.FAISS_INDEX_ROOT, 'ocr_indexes')
            if os.path.exists(index_dir):
                shutil.rmtree(index_dir)
            Video.objects.all().update(ocr_index_status='none')

        # Find videos that have OCR content generated but not yet indexed
        videos_to_queue = Video.objects.filter(
            Q(ocr_index_status='none') | Q(ocr_index_status='failed'),
            ocr_transcript_status='complete' 
        )

        self.stdout.write(f'Found {videos_to_queue.count()} videos for OCR indexing.')

        for video in videos_to_queue:
            # Call the task created in engine/tasks.py
            async_task('engine.tasks.task_generate_ocr_index', video.id)
            self.stdout.write(f'Queued OCR index for: {video.title}')