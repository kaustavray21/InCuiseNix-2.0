import os
import logging
from django.conf import settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

from core.models import Transcript, OCRTranscript, Video, Course
from .config import get_embeddings

logger = logging.getLogger(__name__)

# STANDARD TRANSCRIPT INDEXING

def perform_course_index_generation(course_id: int):
    logger.info(f"--- Starting FAISS index generation (Standard) for course ID: {course_id} ---")
    try:
        course = Course.objects.get(id=course_id)
        videos = Video.objects.filter(course=course)
        
        if not videos.exists():
            logger.warning(f"No videos found for course '{course.title}'. Nothing to index.")
            return "No Videos", "No videos found."

        logger.info(f"Found {videos.count()} videos to index for course '{course.title}'.")
        
        success_count = 0
        fail_count = 0

        for video in videos:
            try:
                create_index_for_single_video(video)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to index video {video.id} ('{video.title}'): {e}")
                fail_count += 1
        
        logger.info(f"--- Completed standard indexing for course {course_id}. Success: {success_count}, Failed: {fail_count} ---")
        return "Generated", f"Indexed {success_count} videos. Failed {fail_count}."

    except Exception as e:
        logger.error(f"FATAL: Course index generation crashed for course {course_id}: {e}", exc_info=True)
        return "Error", str(e)


def create_index_for_single_video(video: Video):
    logger.info(f"Creating Standard vector store for video: '{video.title}' (ID: {video.id})")

    try:
        video.index_status = 'indexing'
        video.save(update_fields=['index_status'])

        platform_id = video.youtube_id or video.vimeo_id
        if not platform_id:
            raise ValueError(f"Video {video.id} (DB) has no platform_id.")

        transcripts = Transcript.objects.filter(video=video).order_by('start')

        if not transcripts.exists():
            if video.transcript_status == 'complete':
                logger.warning(f"No transcripts found for video: {platform_id} but status is complete. Marking index complete.")
                video.index_status = 'complete'
                video.save(update_fields=['index_status'])
            else:
                logger.warning(f"No transcripts found for video: {platform_id} and status is '{video.transcript_status}'. Marking index failed.")
                video.index_status = 'failed'
                video.save(update_fields=['index_status'])
            return
            
        docs = []
        for t in transcripts:
            docs.append(Document(
                page_content=t.content,
                metadata={
                    'start_time': t.start,
                    'video_title': video.title,
                    'video_id': platform_id,
                    'course_title': video.course.title,
                    'course_id': video.course.id,
                    'type': 'transcript' # Useful for distinguishing in search results
                }
            ))

        _process_and_save_index(docs, platform_id, video, 'transcripts', 'index_status')

    except Exception as e:
        logger.error(f"Failed to create standard index for video {video.id}: {e}", exc_info=True)
        video.index_status = 'failed'
        video.save(update_fields=['index_status'])
        raise e


# OCR INDEXING

def perform_course_ocr_index_generation(course_id: int):
    """
    Iterates through all videos in a course and generates/updates the OCR vector index.
    """
    logger.info(f"--- Starting FAISS OCR index generation for course ID: {course_id} ---")
    try:
        course = Course.objects.get(id=course_id)
        videos = Video.objects.filter(course=course)
        
        if not videos.exists():
            return "No Videos", "No videos found."

        success_count = 0
        fail_count = 0

        for video in videos:
            try:
                create_ocr_index_for_single_video(video)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to OCR index video {video.id}: {e}")
                fail_count += 1
        
        logger.info(f"--- Completed OCR indexing for course {course_id}. Success: {success_count}, Failed: {fail_count} ---")
        return "Generated", f"OCR Indexed {success_count} videos. Failed {fail_count}."

    except Exception as e:
        logger.error(f"FATAL: OCR Course index generation crashed for course {course_id}: {e}", exc_info=True)
        return "Error", str(e)


def create_ocr_index_for_single_video(video: Video):
    logger.info(f"Creating OCR vector store for video: '{video.title}' (ID: {video.id})")

    try:
        # 1. Update OCR Index Status
        video.ocr_index_status = 'indexing'
        video.save(update_fields=['ocr_index_status'])

        platform_id = video.youtube_id or video.vimeo_id
        if not platform_id:
            raise ValueError(f"Video {video.id} has no platform_id.")

        # 2. Fetch OCR Transcripts
        ocr_transcripts = OCRTranscript.objects.filter(video=video).order_by('start')

        # 3. Handle Empty Results
        if not ocr_transcripts.exists():
            if video.ocr_transcript_status == 'complete':
                logger.warning(f"No OCR data found for {platform_id} but status is complete. Marking index complete.")
                video.ocr_index_status = 'complete'
                video.save(update_fields=['ocr_index_status'])
            else:
                logger.warning(f"No OCR data found for {platform_id} and status is '{video.ocr_transcript_status}'. Marking index failed.")
                video.ocr_index_status = 'failed'
                video.save(update_fields=['ocr_index_status'])
            return

        # 4. Create Documents
        docs = []
        for t in ocr_transcripts:
            docs.append(Document(
                page_content=t.content,
                metadata={
                    'start_time': t.start,
                    'video_title': video.title,
                    'video_id': platform_id,
                    'course_title': video.course.title,
                    'course_id': video.course.id,
                    'type': 'ocr' # Useful for distinguishing in search results
                }
            ))

        # 5. Process and Save (Reusable logic)
        # Saves to settings.FAISS_INDEX_ROOT/ocr/platform_id
        _process_and_save_index(docs, platform_id, video, 'ocr', 'ocr_index_status')

    except Exception as e:
        logger.error(f"Failed to create OCR index for video {video.id}: {e}", exc_info=True)
        video.ocr_index_status = 'failed'
        video.save(update_fields=['ocr_index_status'])
        raise e

# SHARED UTILITIES


def _process_and_save_index(docs, platform_id, video, subfolder_name, status_field):
    """
    Shared logic to split text, embed, save FAISS index, and update status.
    """
    logger.info(f"Loaded {len(docs)} documents for {subfolder_name} processing.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    split_docs = text_splitter.split_documents(docs)
    logger.info(f"Split into {len(split_docs)} chunks for embedding.")

    if not split_docs:
        logger.warning(f"Text splitting resulted in zero documents for video {platform_id}. Skipping.")
        setattr(video, status_field, 'complete')
        video.save(update_fields=[status_field])
        return

    embedding_function = get_embeddings()

    logger.info(f"Creating FAISS index from {len(split_docs)} chunks...")
    vector_store = FAISS.from_documents(split_docs, embedding_function)

    # Path e.g.: /indices/transcripts/12345 OR /indices/ocr/12345
    index_path = os.path.join(settings.FAISS_INDEX_ROOT, subfolder_name, platform_id)
    os.makedirs(index_path, exist_ok=True)

    vector_store.save_local(index_path)
    logger.info(f"Successfully saved FAISS index to {index_path}")

    setattr(video, status_field, 'complete')
    video.save(update_fields=[status_field])
    logger.info(f"Video {video.id} {status_field} updated to 'complete'.")