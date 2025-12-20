from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from core.models import Note, Video
from django_q.tasks import async_task
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Video)
def on_video_save(sender, instance, created, **kwargs):
    # 1. Existing Logic: Handle New Video Processing (Transcoding/Fetching)
    if created and instance.vimeo_id:
        logger.info(f"Signal: New video created (DB ID: {instance.pk}, Vimeo ID: {instance.vimeo_id}). Scheduling processing pipeline.")
        
        instance.transcript_status = 'processing'
        instance.index_status = 'indexing'
        # We also set OCR to processing immediately to reserve the task
        instance.ocr_transcript_status = 'processing' 
        
        instance.save(update_fields=['transcript_status', 'index_status', 'ocr_transcript_status'])
        
        transaction.on_commit(lambda: async_task(
            'engine.tasks.task_process_new_video',
            instance.vimeo_id 
        ))

    # 2. NEW Logic: Trigger OCR specifically
    # Triggers if it's a new video OR if the status was manually set to 'pending'
    if (created or instance.ocr_transcript_status == 'pending') and instance.ocr_transcript_status != 'complete':
        
        # If we didn't already set it to processing in the block above
        if instance.ocr_transcript_status != 'processing':
            logger.info(f"Signal: Triggering OCR for Video {instance.pk}")
            instance.ocr_transcript_status = 'processing'
            instance.save(update_fields=['ocr_transcript_status'])
        
     
        transaction.on_commit(lambda: async_task(
            'engine.tasks.task_process_video_ocr',
            video_id=instance.pk
        ))

@receiver(post_save, sender=Note)
def on_note_save(sender, instance, created, **kwargs):
    if instance.video:
        platform_id = instance.video.youtube_id or instance.video.vimeo_id

        if platform_id:
            if not created and instance.index_status != 'pending':
                Note.objects.filter(pk=instance.pk).update(index_status='pending')
            
            logger.info(f"Signal: Queuing note index update for user {instance.user.id}, video {platform_id}")
            
            transaction.on_commit(lambda: async_task(
                'engine.tasks.task_update_note_index', 
                user_id=instance.user.id, 
                video_id=platform_id
            ))
        else:
            logger.warning(f"Signal: Note {instance.pk} was saved, but its video has no platform_id. Cannot queue task.")

@receiver(post_delete, sender=Note)
def on_note_delete(sender, instance, **kwargs):
    if instance.video:
        platform_id = instance.video.youtube_id or instance.video.vimeo_id

        if platform_id:
            logger.info(f"Signal: Queuing note index update (due to delete) for user {instance.user.id}, video {platform_id}")
            
            transaction.on_commit(lambda: async_task(
                'engine.tasks.task_update_note_index', 
                user_id=instance.user.id, 
                video_id=platform_id
            ))
        else:
            logger.warning(f"Signal: Note {instance.pk} was deleted, but its video has no platform_id. Cannot queue task.")