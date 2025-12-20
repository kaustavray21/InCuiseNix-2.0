import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Video

class Command(BaseCommand):
    help = 'Syncs video status. Resets FAILED, processing, or stuck tasks if no data exists.'

    def handle(self, *args, **options):
        videos = Video.objects.all()
        self.stdout.write(f"Scanning {videos.count()} videos...")
        
        updated_count = 0
        reset_count = 0

        for video in videos:
            changed = False
            
            # 1. Sync Audio Transcript Status
            if video.transcripts.exists():
                if video.transcript_status != 'complete':
                    video.transcript_status = 'complete'
                    changed = True
            
            # 2. Sync OCR Transcript Status
            if video.ocr_transcripts.exists():
                if video.ocr_transcript_status != 'complete':
                    video.ocr_transcript_status = 'complete'
                    changed = True
            else:
                # FIX: Added 'failed' to the list. 
                # If it failed before (and has no data), we reset it to pending to retry.
                if video.ocr_transcript_status in ['processing', 'complete', 'failed']:
                    self.stdout.write(self.style.WARNING(f"  Resetting OCR for '{video.title}': Status was '{video.ocr_transcript_status}' -> 'pending'"))
                    video.ocr_transcript_status = 'pending'
                    changed = True
                    reset_count += 1

            # 3. Sync FAISS Index Status
            platform_id = video.youtube_id or video.vimeo_id
            index_exists_on_disk = False

            if platform_id:
                index_path = os.path.join(settings.FAISS_INDEX_ROOT, 'transcripts', platform_id)
                if os.path.exists(index_path) and os.path.exists(os.path.join(index_path, 'index.faiss')):
                    index_exists_on_disk = True

            if index_exists_on_disk:
                if video.index_status != 'complete':
                    video.index_status = 'complete'
                    changed = True
            else:
                if video.index_status in ['indexing', 'complete', 'failed']:
                    self.stdout.write(self.style.WARNING(f"  Resetting Index for '{video.title}': Status was '{video.index_status}' -> 'none'"))
                    video.index_status = 'none'
                    changed = True
                    reset_count += 1

            if changed:
                video.save(update_fields=['transcript_status', 'index_status', 'ocr_transcript_status'])
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"\n-----------------------------------"))
        self.stdout.write(self.style.SUCCESS(f"Sync Finished."))
        self.stdout.write(self.style.SUCCESS(f"Updated/Synced: {updated_count} videos"))
        self.stdout.write(self.style.WARNING(f"Reset (Ready to Retry): {reset_count} videos"))
        self.stdout.write(self.style.SUCCESS(f"-----------------------------------"))