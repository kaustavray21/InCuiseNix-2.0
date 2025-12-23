import logging
import os
import csv
from typing import List, Dict
from django.conf import settings
from core.models import Video, OCRTranscript
from .frame_extractor import FrameExtractor
from .ocr_extractor import OCRExtractor
from .text_processor import TextProcessor
from .ocr_downloader import VideoDownloader
from engine.transcript_service.utils import sanitize_filename

logger = logging.getLogger(__name__)

class VideoOCRService:
    def __init__(self, sample_rate: int = 2):
        self.frame_extractor = FrameExtractor(sample_rate=sample_rate)
        self.ocr_extractor = OCRExtractor(lang='en', use_gpu=False) 
        self.text_processor = TextProcessor(min_similarity=0.85)
        self.downloader = VideoDownloader()
        
        # Base directory
        self.ocr_root_dir = os.path.join(settings.MEDIA_ROOT, 'ocr_transcripts')
        if not os.path.exists(self.ocr_root_dir):
            os.makedirs(self.ocr_root_dir)

    def _save_to_csv(self, video, unique_entries: List[Dict]):
        """
        Saves OCR results to a CSV.
        Organizes files into subfolders by Course Name.
        """
        # 1. Determine Filename (ID preferred)
        platform_id = video.vimeo_id or video.youtube_id
        if platform_id:
            filename = f"{platform_id}.csv"
        else:
            filename = f"video_{video.id}.csv"
            
        # 2. Determine Folder (Course Name)
        if video.course:
            course_dir_name = sanitize_filename(video.course.title)
        else:
            course_dir_name = "Uncategorized"
            
        final_dir = os.path.join(self.ocr_root_dir, course_dir_name)
        os.makedirs(final_dir, exist_ok=True)
        
        file_path = os.path.join(final_dir, filename)
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['start', 'content'])
                for entry in unique_entries:
                    writer.writerow([entry['start'], entry['content']])
            logger.info(f"OCR CSV saved: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to write CSV {filename}: {e}")
            return None

    def process_video(self, video_id: int) -> bool:
        temp_video_path = None
        try:
            video = Video.objects.get(id=video_id)
            video_path = None
            
            # --- FIX: Robust URL Construction ---
            # If video_url is missing, build it from the IDs
            target_url = video.video_url
            if not target_url:
                if video.vimeo_id:
                    target_url = f"https://vimeo.com/{video.vimeo_id}"
                elif video.youtube_id:
                    target_url = f"https://www.youtube.com/watch?v={video.youtube_id}"
            
            logger.info(f"Video {video.id}: processing target '{target_url}'")

            # --- Logic to handle local vs URL ---
            # 1. Check if it is a local file path that actually exists
            if target_url and os.path.exists(target_url):
                 logger.info(f"Found local file: {target_url}")
                 video_path = target_url
                 
            # 2. If it looks like a URL, download it
            elif target_url and ("http" in target_url or "vimeo" in target_url or "youtube" in target_url):
                 logger.info(f"Downloading from URL: {target_url}")
                 video_path = self.downloader.download_video(target_url)
                 temp_video_path = video_path 
            
            # 3. If we still don't have a path, we can't proceed
            if not video_path or not os.path.exists(video_path):
                 logger.error(f"Video {video.id}: Could not resolve video file. Target URL was: {target_url}")
                 return False

            # --- Start OCR Extraction ---
            logger.info(f"Starting OCR extraction for: {video.title}")

            raw_segments = []
            for timestamp, frame in self.frame_extractor.extract_frames(video_path):
                text = self.ocr_extractor.extract_text(frame, preprocess=False)
                if text.strip():
                    cleaned_text = self.text_processor.clean_text(text)
                    if cleaned_text:
                        raw_segments.append({'start': timestamp, 'content': cleaned_text})

            unique_entries = self._consolidate_segments(raw_segments)

            # 1. Database Update
            OCRTranscript.objects.filter(video=video).delete()
            for entry in unique_entries:
                OCRTranscript.objects.create(
                    video=video,
                    course=video.course,
                    start=entry['start'],
                    content=entry['content'],
                    youtube_id=video.youtube_id,
                    vimeo_id=video.vimeo_id
                )

            # 2. File System Update
            self._save_to_csv(video, unique_entries)

            return True

        except Exception as e:
            logger.error(f"OCR Error Video {video_id}: {str(e)}")
            return False
            
        finally:
            if temp_video_path:
                self.downloader.cleanup(temp_video_path)

    def _consolidate_segments(self, raw_segments: List[Dict]) -> List[Dict]:
        if not raw_segments: return []
        consolidated = []
        current = raw_segments[0]
        from difflib import SequenceMatcher
        for i in range(1, len(raw_segments)):
            nxt = raw_segments[i]
            sim = SequenceMatcher(None, current['content'], nxt['content']).ratio()
            if sim < 0.85:
                consolidated.append(current)
                current = nxt
        consolidated.append(current)
        return consolidated