import os
import logging
from django.conf import settings
from langchain_community.vectorstores import FAISS
from .config import get_embeddings

logger = logging.getLogger(__name__)


def get_transcript_vector_store(video_id: str):
    video_id = str(video_id)
    logger.debug(f"Attempting to load transcript vector store for video_id: {video_id}")
    
    index_path = os.path.join(settings.FAISS_INDEX_ROOT, 'transcripts', video_id)
    
    return _load_vector_store(index_path, "transcript", video_id)


def get_ocr_vector_store(video_id: str):
    video_id = str(video_id)
    logger.debug(f"Attempting to load OCR vector store for video_id: {video_id}")

    index_path = os.path.join(settings.FAISS_INDEX_ROOT, 'ocr', video_id)

    return _load_vector_store(index_path, "OCR", video_id)


def get_note_vector_store(video_id: str, user_id: int):
    logger.debug(f"Attempting to load notes vector store for video_id: {video_id}, user_id: {user_id}")

    index_path = os.path.join(
        settings.FAISS_INDEX_ROOT,
        'notes',
        str(user_id),
        video_id
    )
    
    return _load_vector_store(index_path, "notes", f"{video_id} (user {user_id})")


def _load_vector_store(index_path: str, store_type: str, identifier: str):
    """
    Helper function to verify paths and load the FAISS index.
    """
    if not os.path.exists(index_path):
        logger.warning(f"No {store_type} index directory found for {identifier} at {index_path}")
        return None

    faiss_file = os.path.join(index_path, "index.faiss")
    if not os.path.exists(faiss_file):
        logger.warning(f"FAISS file 'index.faiss' not found within {store_type} directory {index_path}")
        return None

    try:
        logger.debug(f"Loading {store_type} FAISS index from: {index_path}")
        return FAISS.load_local(
            index_path,
            get_embeddings(),
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        logger.exception(f"Error loading {store_type} index for {identifier}: {e}")
        return None