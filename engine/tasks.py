import logging
from .transcript_service.orchestrator import generate_transcript_for_video
from .transcript_service.ocr_service.video_ocr_service import VideoOCRService  # <--- NEW IMPORT
from .rag.vector_store.indexer import perform_course_index_generation, create_index_for_single_video
from .rag.index_notes import update_video_notes_index
from core.models import Note, Video
from django.contrib.auth.models import User
from django.db.models import Q

logger = logging.getLogger(__name__)

def task_process_new_video(vimeo_id: str):
    """
    Orchestrates the pipeline for a newly uploaded video using its Vimeo ID.
    Pipeline: Audio Transcript -> OCR Transcript -> FAISS Index
    """
    logger.info(f"Django-Q: Starting NEW VIDEO pipeline for Vimeo ID {vimeo_id}")
    
    video = None
    try:
        # 1. Retrieve the video using the Vimeo ID
        video = Video.objects.get(vimeo_id=vimeo_id)
        
        # --- Step 1: Audio Transcript ---
        logger.info(f"Pipeline: 1. Generating AUDIO transcript for video {video.id}")
        status, log = generate_transcript_for_video(video.id)
        
        if status == "Error":
            raise Exception(f"Audio Transcript generation failed. Log: {log}")

        # --- Step 2: OCR Transcript (NEW) ---
        logger.info(f"Pipeline: 2. Generating OCR transcript for video {video.id}")
        
        # Initialize service and process
        ocr_service = VideoOCRService(sample_rate=2)
        ocr_success = ocr_service.process_video(video.id)
        
        if not ocr_success:
            # We log a warning but DO NOT stop the pipeline, as indexing might still be possible with just audio
            logger.warning(f"Pipeline: OCR generation failed for video {video.id}. Proceeding to indexing...")
            # Ensure the status is set to failed in DB (service usually does this, but double check)
            if video.ocr_transcript_status != 'failed':
                video.ocr_transcript_status = 'failed'
                video.save(update_fields=['ocr_transcript_status'])
        else:
             logger.info(f"Pipeline: OCR generation SUCCESS for video {video.id}")

        # --- Step 3: Indexing ---
        logger.info(f"Pipeline: 3. Creating FAISS index for video {video.id}")
        create_index_for_single_video(video)
        
        logger.info(f"Django-Q: NEW VIDEO pipeline SUCCESS for video {video.id}.")
        
    except Video.DoesNotExist:
        logger.error(f"CRITICAL: Could not find video with Vimeo ID {vimeo_id} in the database.")

    except Exception as e:
        logger.error(f"Django-Q: NEW VIDEO pipeline FAILED for Vimeo ID {vimeo_id}. Error: {e}", exc_info=True)
        if video:
            # Mark critical statuses as failed
            video.transcript_status = 'failed'
            video.index_status = 'failed'
            # Note: We don't necessarily overwrite OCR status here if it was the one that failed earlier
            video.save(update_fields=['transcript_status', 'index_status'])


def task_process_video_ocr(video_id: int):
    """
    Standalone task to run OCR on a specific video.
    Used by signals.py when ocr_transcript_status is pending.
    """
    logger.info(f"Django-Q: Starting OCR task for video {video_id}")
    try:
        service = VideoOCRService(sample_rate=2)
        success = service.process_video(video_id)
        
        if success:
            logger.info(f"Django-Q: OCR task SUCCESS for video {video_id}")
        else:
            logger.error(f"Django-Q: OCR task FAILED for video {video_id}")
            # Explicitly ensure DB state reflects failure if service didn't save it
            try:
                v = Video.objects.get(id=video_id)
                if v.ocr_transcript_status != 'complete':
                    v.ocr_transcript_status = 'failed'
                    v.save(update_fields=['ocr_transcript_status'])
            except:
                pass

    except Exception as e:
        logger.exception(f"Django-Q: Unexpected error in OCR task for video {video_id}")
        try:
            v = Video.objects.get(id=video_id)
            v.ocr_transcript_status = 'failed'
            v.save(update_fields=['ocr_transcript_status'])
        except:
            pass


def task_generate_transcript(video_id: int):
    logger.info(f"Django-Q: Starting transcript task for video {video_id}")
    status, log = generate_transcript_for_video(video_id)
    if status == "Error":
        logger.error(f"Django-Q: Transcript task FAILED for video {video_id}. Log: {log}")
        try:
            v = Video.objects.get(id=video_id)
            v.transcript_status = 'failed'
            v.save(update_fields=['transcript_status'])
        except Exception:
            pass
    else:
        logger.info(f"Django-Q: Transcript task SUCCESS for video {video_id}.")


def task_generate_index(course_id: int):
    logger.info(f"Django-Q: Starting index task for course {course_id}")
    status, log = perform_course_index_generation(course_id)
    if status == "Error":
        logger.error(f"Django-Q: Index task FAILED for course {course_id}. Log: {log}")
    else:
        logger.info(f"Django-Q: Index task SUCCESS for course {course_id}.")


def task_update_note_index(user_id: int, video_id: str):
    try:
        logger.info(f"Django-Q : Starting note index update for user {user_id}, video {video_id}")
        user = User.objects.get(id=user_id)
        video = Video.objects.get(Q(youtube_id=video_id) | Q(vimeo_id=video_id))

        notes_to_process = Note.objects.filter(user=user, video=video)
        notes_to_process.update(index_status='processing')

        update_video_notes_index(video, user)

        notes_to_process.update(index_status='complete')

    except Video.DoesNotExist:
        logger.error(f"Django-Q: Failed note index task for platform_id {video_id} for user {user_id}")
    except User.DoesNotExist:
        logger.error(f"Django-Q: Failed note index. User not found with id {user_id} for video {video_id}")
    except Exception as e:
        logger.error(f"Django-Q: FAILED note index task for user {user_id}, video {video_id}: {e}", exc_info=True)

        try:
            if 'video' in locals() and 'user' in locals():
                Note.objects.filter(user=user, video=video, index_status='processing').update(index_status='failed')
        except Exception as e_update:
            logger.error(f"Django-Q: Could not even set status to 'failed' for user {user_id}, video {video_id}: {e_update}")