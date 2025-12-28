from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from core.models import Note, Video
from django_q.tasks import async_task
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Video)
def on_video_save(sender, instance, created, **kwargs):
    # 1. Handle New Video Creation: Trigger full processing pipeline
    if created and instance.vimeo_id:
        logger.info(f"Signal: New video created (DB ID: {instance.pk}). Scheduling full processing pipeline.")
        
        # Pre-set statuses to prevent redundant signals later
        instance.transcript_status = 'processing'
        instance.ocr_transcript_status = 'processing'
        instance.index_status = 'indexing'
        instance.ocr_index_status = 'indexing'
        
        instance.save(update_fields=[
            'transcript_status', 
            'ocr_transcript_status', 
            'index_status', 
            'ocr_index_status'
        ])
        
        transaction.on_commit(lambda: async_task(
            'engine.tasks.task_process_new_video',
            instance.vimeo_id 
        ))
        return 

    # 2. Retry Logic: Trigger processing if status is manually set to 'pending'
    
    # Audio Transcript Retry
    if instance.transcript_status == 'pending':
        logger.info(f"Signal: Triggering Audio Transcript Retry for Video {instance.pk}")
        instance.transcript_status = 'processing'
        instance.save(update_fields=['transcript_status'])
        transaction.on_commit(lambda: async_task(
            'engine.tasks.task_generate_transcript',
            video_id=instance.pk
        ))

    # OCR Transcript Retry
    if instance.ocr_transcript_status == 'pending':
        logger.info(f"Signal: Triggering OCR Transcript Retry for Video {instance.pk}")
        instance.ocr_transcript_status = 'processing'
        instance.save(update_fields=['ocr_transcript_status'])
        transaction.on_commit(lambda: async_task(
            'engine.tasks.task_process_video_ocr',
            video_id=instance.pk
        ))

    # 3. Indexing Logic: Trigger indexing when transcripts complete
    
    # Standard Indexing
    if instance.transcript_status == 'complete' and instance.index_status in ['none', 'failed']:
        logger.info(f"Signal: Transcript complete. Triggering Standard Indexing for Video {instance.pk}")
        
        instance.index_status = 'indexing'
        instance.save(update_fields=['index_status'])
        
        transaction.on_commit(lambda: async_task(
            'core.rag.vector_store.indexer.create_index_for_single_video',
            instance
        ))

    # OCR Indexing
    if instance.ocr_transcript_status == 'complete' and instance.ocr_index_status in ['none', 'failed']:
        logger.info(f"Signal: OCR complete. Triggering OCR Indexing for Video {instance.pk}")
        
        instance.ocr_index_status = 'indexing'
        instance.save(update_fields=['ocr_index_status'])
        
        transaction.on_commit(lambda: async_task(
            'engine.tasks.task_generate_ocr_index',
            video_id=instance.pk
        ))

@receiver(post_save, sender=Note)
def on_note_save(sender, instance, created, **kwargs):
    if instance.video:
        platform_id = instance.video.youtube_id or instance.video.vimeo_id

        if platform_id:
            # Reset status to pending on update unless already processing
            if not created and instance.index_status != 'pending':
                Note.objects.filter(pk=instance.pk).update(index_status='pending')
            
            logger.info(f"Signal: Queuing note index update for user {instance.user.id}, video {platform_id}")
            
            transaction.on_commit(lambda: async_task(
                'engine.tasks.task_update_note_index', 
                user_id=instance.user.id, 
                video_id=platform_id
            ))
        else:
            logger.warning(f"Signal: Note {instance.pk} saved, but video has no platform_id.")

@receiver(post_delete, sender=Note)
def on_note_delete(sender, instance, **kwargs):
    if instance.video:
        platform_id = instance.video.youtube_id or instance.video.vimeo_id

        if platform_id:
            logger.info(f"Signal: Queuing note index update (delete) for user {instance.user.id}, video {platform_id}")
            
            transaction.on_commit(lambda: async_task(
                'engine.tasks.task_update_note_index', 
                user_id=instance.user.id, 
                video_id=platform_id
            ))
        else:
            logger.warning(f"Signal: Note {instance.pk} deleted, but video has no platform_id.")