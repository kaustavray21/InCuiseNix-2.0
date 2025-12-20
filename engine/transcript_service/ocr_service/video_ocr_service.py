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

logger = logging.getLogger(__name__)

class VideoOCRService:
    def __init__(self, sample_rate: int = 2):
        self.frame_extractor = FrameExtractor(sample_rate=sample_rate)
        self.ocr_extractor = OCRExtractor(lang='en', use_gpu=False) 
        self.text_processor = TextProcessor(min_similarity=0.85)
        self.downloader = VideoDownloader()
        
        self.csv_dir = os.path.join(settings.MEDIA_ROOT, 'ocr_transcripts')
        if not os.path.exists(self.csv_dir):
            os.makedirs(self.csv_dir)

    def _save_to_csv(self, video, unique_entries: List[Dict]):
        """
        Saves OCR results to a CSV named after the Vimeo or YouTube ID.
        """
        # Determine filename based on Platform ID
        platform_id = video.vimeo_id or video.youtube_id
        
        if platform_id:
            filename = f"{platform_id}.csv"
        else:
            filename = f"video_{video.id}.csv"
            
        file_path = os.path.join(self.csv_dir, filename)
        
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
            
            if video.video_url and os.path.exists(video.video_url):
                 video_path = video.video_url
            elif video.video_url and ("http" in video.video_url):
                 video_path = self.downloader.download_video(video.video_url)
                 temp_video_path = video_path 
            
            if not video_path or not os.path.exists(video_path):
                 logger.error(f"Video {video.id}: File not found.")
                 return False

            logger.info(f"Processing OCR for: {video.title}")

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

            # 2. File System Update (CSV)
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