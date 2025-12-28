import logging
from langchain_community.vectorstores import FAISS
from langchain.retrievers import EnsembleRetriever
from .config import get_embeddings
# Updated import to include get_ocr_vector_store
from .loader import get_transcript_vector_store, get_note_vector_store, get_ocr_vector_store 

logger = logging.getLogger(__name__)

def get_retriever(video_id: str, user_id: int | None):
    logger.debug(f"Getting retriever for video_id: {video_id}, user_id: {user_id}")

    retrievers = []
    weights = []

    # --- 1. Audio Transcript Retriever ---
    transcript_store = get_transcript_vector_store(video_id)
    if transcript_store:
        # k=3: Get top 3 matching segments from speech
        transcript_retriever = transcript_store.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        retrievers.append(transcript_retriever)
        weights.append(0.5) # Weight: 50% Importance
        logger.info(f"Loaded transcript retriever for video {video_id}")

    # --- 2. OCR (On-Screen Text) Retriever ---
    ocr_store = get_ocr_vector_store(video_id)
    if ocr_store:
        # k=3: Get top 3 matching segments from screen text
        ocr_retriever = ocr_store.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        retrievers.append(ocr_retriever)
        weights.append(0.2) # Weight: 20% Importance (Supportive context)
        logger.info(f"Loaded OCR retriever for video {video_id}")

    # --- 3. User Notes Retriever ---
    if user_id is not None:
        note_store = get_note_vector_store(video_id, user_id)
        if note_store:
            # k=5: Get top 5 notes (higher recall for user personalization)
            note_retriever = note_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            retrievers.append(note_retriever)
            weights.append(0.3) # Weight: 30% Importance
            logger.info(f"Loaded note retriever for video {video_id} for user {user_id}")

    # --- Fallback if no data exists ---
    if not retrievers:
        logger.warning(f"Could not load any retrievers for video {video_id}. RAG will have no context.")
        return FAISS.from_texts(["No context available for this video."], get_embeddings()).as_retriever(search_kwargs={"k": 1})

    # --- Single Retriever Optimization ---
    if len(retrievers) == 1:
        logger.info(f"Using single retriever for video {video_id}")
        return retrievers[0]

    # --- Dynamic Weight Normalization ---
    # Ensure weights sum to 1.0 (e.g., if Notes are missing, redistribute 0.3 to Transcript/OCR)
    total_weight = sum(weights)
    final_weights = [w / total_weight for w in weights]

    logger.info(f"Using EnsembleRetriever with {len(retrievers)} sources. Weights: {final_weights}")
    return EnsembleRetriever(retrievers=retrievers, weights=final_weights)