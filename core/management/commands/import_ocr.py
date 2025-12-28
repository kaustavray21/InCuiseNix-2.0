import os
import csv
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from core.models import Video, OCRTranscript 

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Imports local OCR CSV files into the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--wipe',
            action='store_true',
            help='Wipe all existing OCR transcripts before importing.',
        )

    def handle(self, *args, **options):
        # --- WIPE LOGIC ---
        if options['wipe']:
            self.stdout.write(self.style.WARNING('!!! WIPE DETECTED !!!'))
            self.stdout.write('Cleaning Database records...')
            with transaction.atomic():
                count, _ = OCRTranscript.objects.all().delete()
                # Reset only the transcript status. We do not touch index status.
                Video.objects.update(ocr_transcript_status='pending')
            self.stdout.write(self.style.SUCCESS(f'  - Deleted {count} OCR transcript rows from DB.'))
        # ------------------

        base_dir = os.path.join(settings.MEDIA_ROOT, 'ocr_transcripts')
        
        if not os.path.exists(base_dir):
            self.stdout.write(self.style.ERROR(f"Directory not found: {base_dir}"))
            return

        self.stdout.write(f"Scanning directory: {base_dir}")
        
        processed_count = 0
        skipped_count = 0
        error_count = 0

        for root, dirs, files in os.walk(base_dir):
            for filename in files:
                if not filename.endswith('.csv'):
                    continue

                file_path = os.path.join(root, filename)
                file_id = os.path.splitext(filename)[0]
                
                try:
                    self.process_file(file_path, file_id)
                    processed_count += 1
                except Video.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Skipped {filename}: Video not found in DB."))
                    skipped_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing {filename}: {e}"))
                    error_count += 1

        self.stdout.write(self.style.SUCCESS(f"\nImport Finished."))
        self.stdout.write(f"Processed: {processed_count}")
        self.stdout.write(f"Skipped (No DB Match): {skipped_count}")
        self.stdout.write(f"Errors: {error_count}")

    def process_file(self, file_path, file_id):
        video = None
        
        # Try finding video by ID (e.g. video_123.csv)
        if file_id.startswith('video_'):
            try:
                db_id = int(file_id.split('_')[1])
                video = Video.objects.get(id=db_id)
            except (IndexError, ValueError):
                pass
        
        # Try finding video by Vimeo ID
        if not video:
            try:
                video = Video.objects.get(vimeo_id=file_id)
            except Video.DoesNotExist:
                pass
        
        # Try finding video by YouTube ID
        if not video:
            try:
                video = Video.objects.get(youtube_id=file_id)
            except Video.DoesNotExist:
                raise Video.DoesNotExist

        # If we didn't wipe, we might need to overwrite specific records
        if video.ocr_transcripts.exists():
            self.stdout.write(f"  Updating existing records for: {video.title}")
            video.ocr_transcripts.all().delete()
        else:
            self.stdout.write(f"  Importing new data for: {video.title}")

        transcript_objects = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None) # Skip header
            
            for row in reader:
                if len(row) < 2:
                    continue
                
                try:
                    start_time = float(row[0])
                    text_content = row[1].strip()

                    if text_content:
                        transcript_objects.append(
                            OCRTranscript(
                                video=video,
                                start=start_time,
                                course=video.course,
                                content=text_content
                            )
                        )
                except ValueError:
                    logger.warning(f"Skipping malformed row in {file_path}: {row}")
                    continue

        if transcript_objects:
            with transaction.atomic():
                OCRTranscript.objects.bulk_create(transcript_objects)
                
                video.ocr_transcript_status = 'complete'
                # We strictly update ONLY the transcript status, as requested.
                video.save(update_fields=['ocr_transcript_status'])